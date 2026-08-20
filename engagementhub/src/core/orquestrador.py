"""Orquestrador S3 — Waterfall + Capping + Consentimento.

BACK-06-A: lógica core do orquestrador em 6 etapas.
Todas as funções recebem client como parâmetro para facilitar teste com FakeSQLiteClient.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from src.core.config import (
    TABLE_CAMPANHA,
    TABLE_CAPPING,
    TABLE_CONSENTIMENTO,
    TABLE_ESTADO_CLIENTE,
    TABLE_FILA,
    TABLE_GOLDEN_RECORD,
    TABLE_JORNADA,
    TABLE_PECA,
    TABLE_PRIORIDADE,
    TABLE_SEG_RESULTADO,
    TABLE_SUPRESSAO,
    TABLE_TRACKING,
)
from src.db.databricks_client import get_client

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def gerar_id(prefixo: str) -> str:
    return f"{prefixo}_{uuid4().hex[:16]}"


def periodo_para_delta(periodo: str) -> timedelta:
    """Converte nome do período em timedelta."""
    periodo = (periodo or "dia").lower()
    if periodo == "semana":
        return timedelta(days=7)
    if periodo == "mes":
        return timedelta(days=30)
    return timedelta(days=1)


# ---------------------------------------------------------------------------
# ETAPA 1 — Elegibilidade
# ---------------------------------------------------------------------------

def listar_jornadas_ativas(client=None) -> list[dict[str, Any]]:
    """Busca jornadas ativas de campanhas ativas com prioridade."""
    client = client or get_client()
    rows = client.fetch_all(
        f"""
        SELECT
            j.campanha_id,
            j.jornada_id,
            j.seg_entrada_id,
            COALESCE(cp.prioridade, 999) AS prioridade
        FROM {TABLE_JORNADA} j
        INNER JOIN {TABLE_CAMPANHA} c ON c.campanha_id = j.campanha_id
        LEFT JOIN {TABLE_PRIORIDADE} cp ON cp.campanha_id = j.campanha_id
        WHERE j.status = 'ativa'
          AND c.status = 'ativa'
          AND j.seg_entrada_id IS NOT NULL
        ORDER BY COALESCE(cp.prioridade, 999), j.jornada_id
        """
    )
    return [
        {
            "campanha_id": r[0],
            "jornada_id": r[1],
            "seg_entrada_id": r[2],
            "prioridade": r[3],
        }
        for r in (rows or [])
    ]


def carregar_elegiveis_segmento(seg_id: str, client=None) -> set[str]:
    """Busca CPFs/CNPJs elegíveis do segmento de entrada (S1)."""
    client = client or get_client()
    rows = client.fetch_all(
        f"SELECT cpf_cnpj FROM {TABLE_SEG_RESULTADO} WHERE seg_id = ?",
        (seg_id,),
    )
    return {r[0] for r in (rows or []) if r and r[0]}


def etapa_elegibilidade(client=None) -> list[dict[str, Any]]:
    """Etapa 1: expande jornadas ativas em candidatos {cpf, campanha, jornada}."""
    client = client or get_client()
    jornadas = listar_jornadas_ativas(client)
    candidatos = []
    for j in jornadas:
        cpfs = carregar_elegiveis_segmento(j["seg_entrada_id"], client)
        for cpf in cpfs:
            candidatos.append({
                "cpf_cnpj": cpf,
                "campanha_id": j["campanha_id"],
                "jornada_id": j["jornada_id"],
                "seg_id": j["seg_entrada_id"],
                "prioridade": j["prioridade"],
            })
    return candidatos


# ---------------------------------------------------------------------------
# ETAPA 2 — Consentimento
# ---------------------------------------------------------------------------

def carregar_canais_jornada(jornada_id: str, client=None) -> set[str]:
    """Extrai canais usados na jornada via peças no grafo."""
    client = client or get_client()
    row = client.fetch_one(
        f"SELECT grafo_json FROM {TABLE_JORNADA} WHERE jornada_id = ?",
        (jornada_id,),
    )
    if not row or not row[0]:
        return set()

    try:
        grafo = json.loads(row[0])
    except (json.JSONDecodeError, TypeError):
        return set()

    peca_ids = []
    for node in grafo.get("nodes", []):
        if node.get("type") == "enviar_peca":
            peca_id = (node.get("data") or {}).get("peca_id")
            if peca_id:
                peca_ids.append(peca_id)

    if not peca_ids:
        return set()

    placeholders = ",".join(["?"] * len(peca_ids))
    rows = client.fetch_all(
        f"SELECT DISTINCT canal FROM {TABLE_PECA} WHERE peca_id IN ({placeholders})",
        tuple(peca_ids),
    )
    return {r[0] for r in (rows or []) if r and r[0]}


def cliente_tem_consentimento(cpf_cnpj: str, canal: str, client=None) -> bool:
    """Retorna True se o cliente NÃO possui opt-out ativo para o canal."""
    client = client or get_client()
    row = client.fetch_one(
        f"""
        SELECT 1
        FROM {TABLE_CONSENTIMENTO}
        WHERE cpf_cnpj = ?
          AND canal = ?
          AND ativo = true
          AND COALESCE(opt_out, false) = true
        LIMIT 1
        """,
        (cpf_cnpj, canal),
    )
    # Se encontrou registro de opt_out ativo, não tem consentimento
    return row is None


def etapa_consentimento(
    candidatos: list[dict[str, Any]], client=None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Etapa 2: filtra quem deu opt-out."""
    client = client or get_client()
    aprovados = []
    supressoes = []

    # Cache de canais por jornada para evitar N queries repetidas
    _cache_canais: dict[str, set[str]] = {}

    for item in candidatos:
        jid = item["jornada_id"]
        if jid not in _cache_canais:
            _cache_canais[jid] = carregar_canais_jornada(jid, client) or {"email"}
        canais = _cache_canais[jid]

        canais_ok = [
            canal for canal in canais
            if cliente_tem_consentimento(item["cpf_cnpj"], canal, client)
        ]

        if not canais_ok:
            supressoes.append({
                "cpf_cnpj": item["cpf_cnpj"],
                "campanha_id": item["campanha_id"],
                "canal": ",".join(sorted(canais)),
                "motivo": "opt_out",
                "detalhe": f"Sem consentimento canais da jornada {jid}",
            })
            continue

        novo = dict(item)
        novo["canais"] = canais_ok
        aprovados.append(novo)

    return aprovados, supressoes


# ---------------------------------------------------------------------------
# ETAPA 3 — Supressão (cliente já em jornada)
# ---------------------------------------------------------------------------

def etapa_supressao(
    candidatos: list[dict[str, Any]], client=None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Etapa 3: suprime clientes já ativos em outra jornada."""
    client = client or get_client()
    aprovados = []
    supressoes = []

    # Cache para evitar query por CPF duplicado
    _cache_em_jornada: dict[str, bool] = {}

    for item in candidatos:
        cpf = item["cpf_cnpj"]
        if cpf not in _cache_em_jornada:
            row = client.fetch_one(
                f"""
                SELECT 1 FROM {TABLE_ESTADO_CLIENTE}
                WHERE cpf_cnpj = ? AND status IN ('ativo', 'aguardando')
                LIMIT 1
                """,
                (cpf,),
            )
            _cache_em_jornada[cpf] = row is not None

        if _cache_em_jornada[cpf]:
            supressoes.append({
                "cpf_cnpj": cpf,
                "campanha_id": item["campanha_id"],
                "canal": ",".join(item.get("canais", [])),
                "motivo": "ja_em_jornada",
                "detalhe": "Cliente já possui jornada ativa/aguardando",
            })
        else:
            aprovados.append(item)

    return aprovados, supressoes


# ---------------------------------------------------------------------------
# ETAPA 4 — Waterfall (prioridade)
# ---------------------------------------------------------------------------

def etapa_waterfall(
    candidatos: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Etapa 4: mantém só a campanha de maior prioridade por CPF."""
    por_cliente: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in candidatos:
        por_cliente[item["cpf_cnpj"]].append(item)

    aprovados = []
    supressoes = []

    for cpf, itens in por_cliente.items():
        itens_ord = sorted(itens, key=lambda x: (x.get("prioridade", 999), x["campanha_id"]))
        vencedor = itens_ord[0]
        aprovados.append(vencedor)

        for perdedor in itens_ord[1:]:
            supressoes.append({
                "cpf_cnpj": cpf,
                "campanha_id": perdedor["campanha_id"],
                "canal": ",".join(perdedor.get("canais", [])),
                "motivo": "waterfall",
                "detalhe": f"Perdeu para {vencedor['campanha_id']} (prioridade={vencedor.get('prioridade')})",
            })

    return aprovados, supressoes


# ---------------------------------------------------------------------------
# ETAPA 5 — Capping
# ---------------------------------------------------------------------------

def carregar_regras_capping(client=None) -> list[dict[str, Any]]:
    client = client or get_client()
    rows = client.fetch_all(
        f"""
        SELECT regra_id, canal, max_mensagens, periodo, intervalo_minimo_horas,
               escopo, prioritaria_ignora_cap
        FROM {TABLE_CAPPING}
        WHERE ativo = true
        """
    )
    return [
        {
            "regra_id": r[0],
            "canal": r[1],
            "max_mensagens": r[2],
            "periodo": r[3],
            "intervalo_minimo_horas": r[4],
            "escopo": r[5],
            "prioritaria_ignora_cap": bool(r[6]) if r[6] is not None else False,
        }
        for r in (rows or [])
    ]


def contar_envios_periodo(
    cpf_cnpj: str, canal: str, inicio: datetime,
    campanha_id: str | None = None, client=None
) -> int:
    """Conta envios do cliente/canal no período."""
    client = client or get_client()
    if campanha_id:
        row = client.fetch_one(
            f"""
            SELECT COUNT(*) FROM {TABLE_TRACKING}
            WHERE cpf_cnpj = ? AND canal = ? AND campanha_id = ? AND enviado_em >= ?
            """,
            (cpf_cnpj, canal, campanha_id, inicio.isoformat()),
        )
    else:
        row = client.fetch_one(
            f"""
            SELECT COUNT(*) FROM {TABLE_TRACKING}
            WHERE cpf_cnpj = ? AND canal = ? AND enviado_em >= ?
            """,
            (cpf_cnpj, canal, inicio.isoformat()),
        )
    return int(row[0]) if row and row[0] is not None else 0


def ultimo_envio(cpf_cnpj: str, canal: str, client=None) -> datetime | None:
    """Retorna timestamp do último envio para o cliente/canal."""
    client = client or get_client()
    row = client.fetch_one(
        f"SELECT MAX(enviado_em) FROM {TABLE_TRACKING} WHERE cpf_cnpj = ? AND canal = ?",
        (cpf_cnpj, canal),
    )
    if not row or not row[0]:
        return None
    valor = row[0]
    if isinstance(valor, datetime):
        return valor
    try:
        return datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def etapa_capping(
    candidatos: list[dict[str, Any]], client=None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Etapa 5: aplica frequency capping por canal."""
    client = client or get_client()
    regras = carregar_regras_capping(client)
    if not regras:
        return candidatos, []

    aprovados = []
    supressoes = []
    agora = utc_now()

    for item in candidatos:
        canais_permitidos = []
        for canal in item.get("canais", ["email"]):
            bloqueado = None
            for regra in regras:
                # Regra só aplica se canal da regra é None/vazio (global) ou == canal atual
                if regra["canal"] and regra["canal"] != canal:
                    continue

                # Check max_mensagens
                if regra["max_mensagens"] is not None:
                    inicio = agora - periodo_para_delta(regra["periodo"])
                    campanha_ref = item["campanha_id"] if regra["escopo"] == "por_campanha" else None
                    qtd = contar_envios_periodo(item["cpf_cnpj"], canal, inicio, campanha_ref, client)
                    if qtd >= int(regra["max_mensagens"]):
                        bloqueado = f"Capping: {qtd} envios no período {regra['periodo']} (max={regra['max_mensagens']})"
                        break

                # Check intervalo mínimo
                if regra["intervalo_minimo_horas"] is not None:
                    ult = ultimo_envio(item["cpf_cnpj"], canal, client)
                    if ult:
                        diff_horas = (agora - ult).total_seconds() / 3600
                        if diff_horas < int(regra["intervalo_minimo_horas"]):
                            bloqueado = f"Capping: intervalo mínimo {regra['intervalo_minimo_horas']}h (atual={diff_horas:.1f}h)"
                            break

            if bloqueado:
                supressoes.append({
                    "cpf_cnpj": item["cpf_cnpj"],
                    "campanha_id": item["campanha_id"],
                    "canal": canal,
                    "motivo": "capping",
                    "detalhe": bloqueado,
                })
            else:
                canais_permitidos.append(canal)

        if canais_permitidos:
            novo = dict(item)
            novo["canais"] = canais_permitidos
            aprovados.append(novo)

    return aprovados, supressoes


# ---------------------------------------------------------------------------
# ETAPA 6 — Enfileirar
# ---------------------------------------------------------------------------

def resolver_destinatario(cpf_cnpj: str, canal: str, client=None) -> str | None:
    """Busca email/telefone no golden_record."""
    client = client or get_client()
    row = client.fetch_one(
        f"SELECT email, telefone FROM {TABLE_GOLDEN_RECORD} WHERE cpf_cnpj = ? LIMIT 1",
        (cpf_cnpj,),
    )
    if not row:
        return None
    if canal == "whatsapp":
        return row[1]  # telefone
    return row[0]  # email


def enfileirar(candidatos: list[dict[str, Any]], client=None) -> list[dict[str, Any]]:
    """Etapa 6: insere na fila_disparo (status=pendente).

    Convenção 06-A: no_id='entrada' como placeholder até BACK-07 (motor de jornada).
    """
    client = client or get_client()
    inseridos = []

    for item in candidatos:
        for canal in item.get("canais", ["email"]):
            destinatario = resolver_destinatario(item["cpf_cnpj"], canal, client)
            if not destinatario:
                continue

            fila_id = gerar_id("fila")
            client.execute_insert(
                f"""
                INSERT INTO {TABLE_FILA}
                (fila_id, cpf_cnpj, campanha_id, jornada_id, no_id, peca_id, canal,
                 destinatario, agendado_para, prioridade, status, tentativas,
                 criado_em, atualizado_em)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, current_timestamp(), ?, ?, 0,
                        current_timestamp(), current_timestamp())
                """,
                (
                    fila_id,
                    item["cpf_cnpj"],
                    item["campanha_id"],
                    item["jornada_id"],
                    "entrada",       # no_id placeholder
                    None,            # peca_id (resolvível pelo motor de jornada)
                    canal,
                    destinatario,
                    item.get("prioridade", 999),
                    "pendente",
                ),
            )
            inseridos.append({
                "fila_id": fila_id,
                "cpf_cnpj": item["cpf_cnpj"],
                "campanha_id": item["campanha_id"],
                "jornada_id": item["jornada_id"],
                "canal": canal,
            })

    return inseridos


# ---------------------------------------------------------------------------
# Gravação de Supressões
# ---------------------------------------------------------------------------

def gravar_supressoes(supressoes: list[dict[str, Any]], client=None) -> int:
    """Persiste supressoes na tabela de log."""
    client = client or get_client()
    for s in supressoes:
        client.execute_insert(
            f"""
            INSERT INTO {TABLE_SUPRESSAO}
            (supressao_id, cpf_cnpj, campanha_id, canal, motivo, detalhe, data_execucao)
            VALUES (?, ?, ?, ?, ?, ?, current_timestamp())
            """,
            (
                gerar_id("sup"),
                s.get("cpf_cnpj"),
                s.get("campanha_id"),
                s.get("canal"),
                s.get("motivo"),
                s.get("detalhe"),
            ),
        )
    return len(supressoes)


# ---------------------------------------------------------------------------
# MAIN — Executor principal
# ---------------------------------------------------------------------------

def executar_orquestrador(client=None) -> dict[str, Any]:
    """Executa as 6 etapas sequencialmente e retorna métricas."""
    client = client or get_client()

    # Pipeline
    etapa1 = etapa_elegibilidade(client)
    etapa2, sup2 = etapa_consentimento(etapa1, client)
    etapa3, sup3 = etapa_supressao(etapa2, client)
    etapa4, sup4 = etapa_waterfall(etapa3)
    etapa5, sup5 = etapa_capping(etapa4, client)
    fila = enfileirar(etapa5, client)

    # Consolida supressões e persiste
    todas_supressoes = sup2 + sup3 + sup4 + sup5
    qtd_sup = gravar_supressoes(todas_supressoes, client)

    resultado = {
        "elegiveis": len(etapa1),
        "pos_consentimento": len(etapa2),
        "pos_supressao": len(etapa3),
        "pos_waterfall": len(etapa4),
        "pos_capping": len(etapa5),
        "enfileirados": len(fila),
        "supressoes": qtd_sup,
        "supressoes_por_motivo": {
            "opt_out": sum(1 for s in todas_supressoes if s["motivo"] == "opt_out"),
            "ja_em_jornada": sum(1 for s in todas_supressoes if s["motivo"] == "ja_em_jornada"),
            "waterfall": sum(1 for s in todas_supressoes if s["motivo"] == "waterfall"),
            "capping": sum(1 for s in todas_supressoes if s["motivo"] == "capping"),
        },
        "itens_fila": fila[:20],  # amostra
    }

    logger.info(f"✓ Orquestrador executado: {len(etapa1)} elegíveis → {len(fila)} enfileirados, {qtd_sup} suprimidos")
    return resultado
