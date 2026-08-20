"""Motor de Jornada S3 (BACK-07).

Percorre o grafo de cada jornada ativa, avançando clientes nó a nó.
Executado como Job (~5min) ou via API admin.

Fluxo:
1. Criar estado para novos entrantes (vindos do orquestrador/fila com no_id='entrada')
2. Buscar estados prontos (status='ativo' ou 'aguardando' com proxima_acao_em <= now)
3. Para cada estado, processar o nó atual:
   - entrada    → avança para primeiro nó conectado
   - enviar_peca → insere na fila_disparo → avança
   - esperar    → seta proxima_acao_em → status='aguardando' (não avança)
   - condicao   → avalia → segue edge true/false
   - ab_split   → sorteia variante por peso → segue edge correspondente
   - acao       → executa side-effect → avança
   - saida      → status='concluido'
4. Loops respeitam max_iteracoes (definido no grafo)
5. Grava log em jornada_log
6. Atualiza jornada_estado_cliente
"""

from __future__ import annotations

import json
import logging
import random
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from src.core.config import (
    TABLE_ESTADO_CLIENTE,
    TABLE_FILA,
    TABLE_GOLDEN_RECORD,
    TABLE_JORNADA,
    TABLE_JORNADA_LOG,
    TABLE_JORNADA_PARTICIPACAO,
    TABLE_PECA,
    TABLE_POLITICA_JORNADA,
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


def parse_grafo(grafo_json: str | None) -> dict | None:
    """Parse seguro do grafo JSON."""
    if not grafo_json:
        return None
    try:
        g = json.loads(grafo_json) if isinstance(grafo_json, str) else grafo_json
        return g if isinstance(g, dict) else None
    except (json.JSONDecodeError, TypeError):
        return None


def construir_adjacencia(grafo: dict) -> tuple[dict, dict]:
    """Retorna (adjacencia_por_id, edges_por_source).

    adjacencia: {source_id: [target_id, ...]}
    edges_por_source: {source_id: [edge_dict, ...]}  (para metadata como label)
    """
    adjacencia: dict[str, list[str]] = defaultdict(list)
    edges_por_source: dict[str, list[dict]] = defaultdict(list)
    for edge in grafo.get("edges", []):
        src = edge.get("source")
        tgt = edge.get("target")
        if src and tgt:
            adjacencia[src].append(tgt)
            edges_por_source[src].append(edge)
    return dict(adjacencia), dict(edges_por_source)


def nodes_por_id(grafo: dict) -> dict[str, dict]:
    """Retorna mapa {node_id: node_dict}."""
    return {n["id"]: n for n in grafo.get("nodes", []) if "id" in n}


# ---------------------------------------------------------------------------
# Carregar dados
# ---------------------------------------------------------------------------

def carregar_jornadas_ativas(client=None) -> list[dict[str, Any]]:
    """Busca jornadas com status='ativa'."""
    client = client or get_client()
    rows = client.fetch_all(
        f"""
        SELECT jornada_id, campanha_id, grafo_json, seg_entrada_id,
               ao_sair_segmento
        FROM {TABLE_JORNADA}
        WHERE status = 'ativa'
        """
    )
    return [
        {
            "jornada_id": r[0],
            "campanha_id": r[1],
            "grafo_json": r[2],
            "seg_entrada_id": r[3],
            "ao_sair_segmento": r[4],
        }
        for r in (rows or [])
    ]


def carregar_estados_prontos(jornada_id: str, client=None) -> list[dict[str, Any]]:
    """Busca estados prontos para processar (ativo ou aguardando com tempo ok)."""
    client = client or get_client()
    agora = utc_now().isoformat()
    rows = client.fetch_all(
        f"""
        SELECT estado_id, jornada_id, campanha_id, cpf_cnpj, no_atual,
               status, proxima_acao_em, historico_nos, contexto_json
        FROM {TABLE_ESTADO_CLIENTE}
        WHERE jornada_id = ?
          AND status IN ('ativo', 'aguardando')
          AND (proxima_acao_em IS NULL OR proxima_acao_em <= ?)
        """,
        (jornada_id, agora),
    )
    return [
        {
            "estado_id": r[0],
            "jornada_id": r[1],
            "campanha_id": r[2],
            "cpf_cnpj": r[3],
            "no_atual": r[4],
            "status": r[5],
            "proxima_acao_em": r[6],
            "historico_nos": json.loads(r[7]) if r[7] else [],
            "contexto_json": json.loads(r[8]) if r[8] else {},
        }
        for r in (rows or [])
    ]


def carregar_novos_entrantes(jornada_id: str, client=None) -> list[dict[str, Any]]:
    """Busca CPFs na fila_disparo com no_id='entrada' que ainda não têm estado."""
    client = client or get_client()
    rows = client.fetch_all(
        f"""
        SELECT DISTINCT f.cpf_cnpj, f.campanha_id, f.jornada_id
        FROM {TABLE_FILA} f
        WHERE f.jornada_id = ?
          AND f.no_id = 'entrada'
          AND f.status = 'pendente'
          AND NOT EXISTS (
              SELECT 1 FROM {TABLE_ESTADO_CLIENTE} e
              WHERE e.cpf_cnpj = f.cpf_cnpj
                AND e.jornada_id = f.jornada_id
                AND e.status IN ('ativo', 'aguardando')
          )
        """,
        (jornada_id,),
    )
    return [
        {"cpf_cnpj": r[0], "campanha_id": r[1], "jornada_id": r[2]}
        for r in (rows or [])
    ]


def carregar_politica_global(client=None) -> dict[str, Any]:
    """Carrega política global de jornada (se existir)."""
    client = client or get_client()
    row = client.fetch_one(
        f"SELECT loop_max_iteracoes_teto, loop_max_dias_teto FROM {TABLE_POLITICA_JORNADA} WHERE escopo = 'global' AND ativo = true"
    )
    if not row:
        return {"loop_max_iteracoes_teto": 50, "loop_max_dias_teto": 90}
    return {
        "loop_max_iteracoes_teto": int(row[0]) if row[0] else 50,
        "loop_max_dias_teto": int(row[1]) if row[1] else 90,
    }


# ---------------------------------------------------------------------------
# Criar estados para novos entrantes
# ---------------------------------------------------------------------------

def criar_estados_novos(jornada: dict, client=None) -> int:
    """Cria registro em jornada_estado_cliente para cada novo entrante."""
    client = client or get_client()
    grafo = parse_grafo(jornada["grafo_json"])
    if not grafo:
        return 0

    # Encontra nó de entrada
    no_entrada = None
    for node in grafo.get("nodes", []):
        if node.get("type") == "entrada":
            no_entrada = node["id"]
            break
    if not no_entrada:
        return 0

    novos = carregar_novos_entrantes(jornada["jornada_id"], client)
    agora = utc_now().isoformat()
    criados = 0

    for item in novos:
        estado_id = gerar_id("est")
        client.execute_insert(
            f"""
            INSERT INTO {TABLE_ESTADO_CLIENTE}
            (estado_id, jornada_id, campanha_id, cpf_cnpj, no_atual,
             status, proxima_acao_em, entrou_em, ultimo_processamento,
             historico_nos, contexto_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                estado_id,
                jornada["jornada_id"],
                item["campanha_id"],
                item["cpf_cnpj"],
                no_entrada,
                "ativo",
                None,  # processar imediatamente
                agora,
                None,
                json.dumps([no_entrada]),
                json.dumps({}),
            ),
        )

        # Marca fila de entrada como processada
        client.execute_insert(
            f"""
            UPDATE {TABLE_FILA}
            SET status = 'processado', atualizado_em = ?
            WHERE cpf_cnpj = ? AND jornada_id = ? AND no_id = 'entrada' AND status = 'pendente'
            """,
            (agora, item["cpf_cnpj"], jornada["jornada_id"]),
        )
        criados += 1

    return criados


# ---------------------------------------------------------------------------
# Processamento de nós
# ---------------------------------------------------------------------------

def processar_no(
    estado: dict,
    node: dict,
    adjacencia: dict,
    edges_por_source: dict,
    nodes_map: dict,
    politica: dict,
    client=None,
) -> dict[str, Any]:
    """Processa um nó e retorna instrução de avanço.

    Retorna dict com:
        - 'avancar_para': node_id do próximo nó (ou None se parou)
        - 'status': novo status do estado ('ativo', 'aguardando', 'concluido')
        - 'proxima_acao_em': timestamp ou None
        - 'log_acao': ação para gravar no log
        - 'log_resultado': resultado para o log
    """
    client = client or get_client()
    tipo = node.get("type", "")
    data = node.get("data", {}) or {}
    node_id = node["id"]
    vizinhos = adjacencia.get(node_id, [])

    resultado = {
        "avancar_para": None,
        "status": "ativo",
        "proxima_acao_em": None,
        "log_acao": tipo,
        "log_resultado": "ok",
    }

    # --- ENTRADA ---
    if tipo == "entrada":
        resultado["avancar_para"] = vizinhos[0] if vizinhos else None
        resultado["log_acao"] = "avancar"
        if not vizinhos:
            resultado["status"] = "concluido"
            resultado["log_resultado"] = "sem_proximo_no"

    # --- ENVIAR_PECA ---
    elif tipo == "enviar_peca":
        peca_id = data.get("peca_id")
        if peca_id:
            _enfileirar_disparo(estado, peca_id, node_id, client)
            resultado["log_resultado"] = f"enfileirado peca={peca_id}"
        else:
            resultado["log_resultado"] = "peca_id ausente — skip"
        resultado["avancar_para"] = vizinhos[0] if vizinhos else None
        resultado["log_acao"] = "enviar_peca"

    # --- ESPERAR ---
    elif tipo == "esperar":
        dias = int(data.get("dias", 0) or 0)
        horas = int(data.get("horas", 0) or 0)
        ate_evento = data.get("ate_evento")

        if ate_evento:
            # Espera por evento externo — aguarda indefinidamente (motor_disparo marca)
            resultado["status"] = "aguardando"
            resultado["proxima_acao_em"] = None  # será desbloqueado por evento
            resultado["log_resultado"] = f"aguardando evento={ate_evento}"
        elif dias or horas:
            delta = timedelta(days=dias, hours=horas)
            resultado["status"] = "aguardando"
            resultado["proxima_acao_em"] = (utc_now() + delta).isoformat()
            resultado["log_resultado"] = f"aguardando {dias}d {horas}h"
        else:
            # Sem configuração de espera — avança direto
            resultado["avancar_para"] = vizinhos[0] if vizinhos else None
            resultado["log_resultado"] = "espera_zerada — avancar"

        # Se retornando de espera (já estava aguardando), avança
        if estado["status"] == "aguardando":
            resultado["status"] = "ativo"
            resultado["proxima_acao_em"] = None
            resultado["avancar_para"] = vizinhos[0] if vizinhos else None
            resultado["log_resultado"] = "espera_concluida"

    # --- CONDICAO ---
    elif tipo == "condicao":
        campo = data.get("campo", "")
        op = data.get("op", "=")
        valor = data.get("valor")
        avaliado = _avaliar_condicao(estado, campo, op, valor, client)

        # Edges devem ter label 'true'/'false' ou sourceHandle
        edges = edges_por_source.get(node_id, [])
        target_true = None
        target_false = None

        for edge in edges:
            label = (edge.get("label") or edge.get("sourceHandle") or "").lower()
            if label in ("true", "sim", "yes", "1"):
                target_true = edge["target"]
            elif label in ("false", "nao", "no", "0"):
                target_false = edge["target"]

        # Fallback: primeiro = true, segundo = false
        if not target_true and not target_false and len(vizinhos) >= 2:
            target_true = vizinhos[0]
            target_false = vizinhos[1]
        elif not target_true and vizinhos:
            target_true = vizinhos[0]
            target_false = vizinhos[0]  # ambos para mesmo se só 1 saída

        resultado["avancar_para"] = target_true if avaliado else target_false
        resultado["log_acao"] = "condicao"
        resultado["log_resultado"] = f"{campo} {op} {valor} → {avaliado}"

    # --- AB_SPLIT ---
    elif tipo == "ab_split":
        variantes = data.get("variantes", [])
        if isinstance(variantes, str):
            try:
                variantes = json.loads(variantes)
            except (json.JSONDecodeError, TypeError):
                variantes = []

        # Sorteia variante por peso (se disponível)
        escolhido_idx = _sortear_variante(variantes)

        # Mapeia para edge correspondente (por index ou label)
        edges = edges_por_source.get(node_id, [])
        if escolhido_idx < len(vizinhos):
            resultado["avancar_para"] = vizinhos[escolhido_idx]
        elif vizinhos:
            resultado["avancar_para"] = vizinhos[0]

        variante_label = variantes[escolhido_idx].get("rotulo", f"variante_{escolhido_idx}") if escolhido_idx < len(variantes) else "?"
        resultado["log_acao"] = "ab_split"
        resultado["log_resultado"] = f"variante={variante_label} (idx={escolhido_idx})"

    # --- ACAO ---
    elif tipo == "acao":
        tipo_acao = data.get("tipo_acao", "noop")
        _executar_acao(estado, tipo_acao, data, client)
        resultado["avancar_para"] = vizinhos[0] if vizinhos else None
        resultado["log_acao"] = f"acao:{tipo_acao}"
        resultado["log_resultado"] = "executada"

    # --- SAIDA ---
    elif tipo == "saida":
        resultado["status"] = "concluido"
        resultado["avancar_para"] = None
        resultado["log_acao"] = "saida"
        resultado["log_resultado"] = "jornada_concluida"

    return resultado


# ---------------------------------------------------------------------------
# Sub-funções de processamento de nós
# ---------------------------------------------------------------------------

def _enfileirar_disparo(estado: dict, peca_id: str, no_id: str, client=None):
    """Insere item na fila_disparo para envio pelo motor_disparo."""
    client = client or get_client()
    # Resolver destinatário
    canal = _resolver_canal_peca(peca_id, client)
    destinatario = _resolver_destinatario(estado["cpf_cnpj"], canal, client)

    if not destinatario:
        logger.warning(f"Sem destinatário para {estado['cpf_cnpj']} canal={canal}")
        return

    fila_id = gerar_id("fila")
    agora = utc_now().isoformat()
    client.execute_insert(
        f"""
        INSERT INTO {TABLE_FILA}
        (fila_id, cpf_cnpj, campanha_id, jornada_id, no_id, peca_id, canal,
         destinatario, agendado_para, prioridade, status, tentativas,
         criado_em, atualizado_em)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
        """,
        (
            fila_id,
            estado["cpf_cnpj"],
            estado["campanha_id"],
            estado["jornada_id"],
            no_id,
            peca_id,
            canal,
            destinatario,
            agora,  # agendado_para = agora (enviar ASAP)
            0,      # prioridade (motor de disparo ordena)
            "pendente",
            agora,
            agora,
        ),
    )


def _resolver_canal_peca(peca_id: str, client=None) -> str:
    """Busca canal da peça."""
    client = client or get_client()
    row = client.fetch_one(
        f"SELECT canal FROM {TABLE_PECA} WHERE peca_id = ?",
        (peca_id,),
    )
    return row[0] if row and row[0] else "email"


def _resolver_destinatario(cpf_cnpj: str, canal: str, client=None) -> str | None:
    """Busca email/telefone no golden_record."""
    client = client or get_client()
    row = client.fetch_one(
        f"SELECT email, telefone FROM {TABLE_GOLDEN_RECORD} WHERE cpf_cnpj = ? LIMIT 1",
        (cpf_cnpj,),
    )
    if not row:
        return None
    if canal == "whatsapp":
        return row[1]
    return row[0]


def _avaliar_condicao(
    estado: dict, campo: str, op: str, valor: Any, client=None
) -> bool:
    """Avalia condição simples baseada no contexto do cliente.

    Extensível: pode buscar features de customer_features_wide futuramente.
    Por ora usa contexto_json do estado.
    """
    contexto = estado.get("contexto_json", {})
    valor_real = contexto.get(campo)

    if valor_real is None:
        return False

    try:
        if op == "=":
            return str(valor_real) == str(valor)
        elif op == "!=":
            return str(valor_real) != str(valor)
        elif op == ">":
            return float(valor_real) > float(valor)
        elif op == ">=":
            return float(valor_real) >= float(valor)
        elif op == "<":
            return float(valor_real) < float(valor)
        elif op == "<=":
            return float(valor_real) <= float(valor)
        elif op == "in":
            lista = valor if isinstance(valor, list) else [valor]
            return str(valor_real) in [str(v) for v in lista]
        elif op == "not_in":
            lista = valor if isinstance(valor, list) else [valor]
            return str(valor_real) not in [str(v) for v in lista]
        elif op == "contains":
            return str(valor) in str(valor_real)
        elif op == "exists":
            return valor_real is not None
    except (ValueError, TypeError):
        return False

    return False


def _sortear_variante(variantes: list[dict]) -> int:
    """Sorteia variante por peso (Thompson Sampling simplificado).

    Se pesos não definidos, distribuição uniforme.
    Retorna índice da variante escolhida.
    """
    if not variantes:
        return 0

    pesos = []
    for v in variantes:
        peso = v.get("peso_atual") or v.get("peso") or 1.0
        try:
            pesos.append(float(peso))
        except (ValueError, TypeError):
            pesos.append(1.0)

    total = sum(pesos)
    if total <= 0:
        return random.randint(0, len(variantes) - 1)

    # Weighted random
    r = random.uniform(0, total)
    acumulado = 0.0
    for i, p in enumerate(pesos):
        acumulado += p
        if r <= acumulado:
            return i
    return len(variantes) - 1


def _executar_acao(estado: dict, tipo_acao: str, data: dict, client=None):
    """Executa side-effect de um nó 'acao'.

    Tipos suportados (extensível):
    - tag: adiciona tag ao contexto
    - atualizar_contexto: merge data no contexto_json
    - noop: não faz nada
    """
    if tipo_acao == "tag":
        tag = data.get("tag", "")
        if tag:
            tags = estado.get("contexto_json", {}).get("tags", [])
            tags.append(tag)
            estado.setdefault("contexto_json", {})["tags"] = tags
    elif tipo_acao == "atualizar_contexto":
        payload = data.get("payload", {})
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except (json.JSONDecodeError, TypeError):
                payload = {}
        estado.setdefault("contexto_json", {}).update(payload)


# ---------------------------------------------------------------------------
# Controle de loops
# ---------------------------------------------------------------------------

def _verificar_loop(estado: dict, proximo_no: str, nodes_map: dict, politica: dict) -> bool:
    """Verifica se avançar para proximo_no excederia max_iteracoes.

    Retorna True se é SEGURO avançar, False se loop excedido.
    """
    historico = estado.get("historico_nos", [])
    contagem = historico.count(proximo_no)

    # Pega max_iteracoes do nó destino (se definido)
    node = nodes_map.get(proximo_no, {})
    data = node.get("data", {}) or {}
    max_iter_no = data.get("max_iteracoes")

    # Teto global da política
    teto = politica.get("loop_max_iteracoes_teto", 50)

    if max_iter_no is not None:
        try:
            max_iter = int(max_iter_no)
        except (ValueError, TypeError):
            max_iter = teto
    else:
        max_iter = teto

    return contagem < max_iter


# ---------------------------------------------------------------------------
# Gravação de log e atualização de estado
# ---------------------------------------------------------------------------

def gravar_log(
    jornada_id: str, cpf_cnpj: str, no_id: str,
    no_tipo: str, acao: str, resultado: str, client=None
):
    """Grava entrada no jornada_log."""
    client = client or get_client()
    client.execute_insert(
        f"""
        INSERT INTO {TABLE_JORNADA_LOG}
        (log_id, jornada_id, cpf_cnpj, no_id, no_tipo, acao, resultado, executado_em)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            gerar_id("log"),
            jornada_id,
            cpf_cnpj,
            no_id,
            no_tipo,
            acao,
            resultado,
            utc_now().isoformat(),
        ),
    )


def atualizar_estado(
    estado: dict, novo_no: str | None, novo_status: str,
    proxima_acao_em: str | None, client=None
):
    """Atualiza jornada_estado_cliente com novo nó/status."""
    client = client or get_client()
    historico = estado.get("historico_nos", [])
    if novo_no and novo_no not in historico[-1:]:
        historico.append(novo_no)

    agora = utc_now().isoformat()
    client.execute_insert(
        f"""
        UPDATE {TABLE_ESTADO_CLIENTE}
        SET no_atual = ?,
            status = ?,
            proxima_acao_em = ?,
            ultimo_processamento = ?,
            historico_nos = ?,
            contexto_json = ?
        WHERE estado_id = ?
        """,
        (
            novo_no or estado["no_atual"],
            novo_status,
            proxima_acao_em,
            agora,
            json.dumps(historico),
            json.dumps(estado.get("contexto_json", {})),
            estado["estado_id"],
        ),
    )


def registrar_participacao_concluida(estado: dict, client=None):
    """Registra conclusão da jornada em jornada_participacao."""
    client = client or get_client()
    agora = utc_now().isoformat()
    # Verifica se já existe participação
    row = client.fetch_one(
        f"""
        SELECT vezes_participou FROM {TABLE_JORNADA_PARTICIPACAO}
        WHERE cpf_cnpj = ? AND jornada_id = ? AND campanha_id = ?
        """,
        (estado["cpf_cnpj"], estado["jornada_id"], estado["campanha_id"]),
    )
    if row:
        vezes = int(row[0] or 0) + 1
        client.execute_insert(
            f"""
            UPDATE {TABLE_JORNADA_PARTICIPACAO}
            SET saiu_em = ?, status_final = ?, vezes_participou = ?
            WHERE cpf_cnpj = ? AND jornada_id = ? AND campanha_id = ?
            """,
            (agora, "concluido", vezes, estado["cpf_cnpj"], estado["jornada_id"], estado["campanha_id"]),
        )
    else:
        client.execute_insert(
            f"""
            INSERT INTO {TABLE_JORNADA_PARTICIPACAO}
            (cpf_cnpj, jornada_id, campanha_id, entrou_em, saiu_em, status_final, vezes_participou)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (estado["cpf_cnpj"], estado["jornada_id"], estado["campanha_id"],
             estado.get("entrou_em", agora), agora, "concluido", 1),
        )


# ---------------------------------------------------------------------------
# Processamento de um estado individual
# ---------------------------------------------------------------------------

def processar_estado(
    estado: dict,
    nodes_map: dict,
    adjacencia: dict,
    edges_por_source: dict,
    politica: dict,
    client=None,
    max_avancos_por_ciclo: int = 20,
) -> dict[str, Any]:
    """Processa um estado, avançando nós até parar (esperar, saída, ou limite).

    Retorna métricas: {nos_processados, status_final, parou_em}.
    """
    client = client or get_client()
    nos_processados = 0
    no_atual = estado["no_atual"]

    for _ in range(max_avancos_por_ciclo):
        node = nodes_map.get(no_atual)
        if not node:
            # Nó inválido — encerra
            atualizar_estado(estado, no_atual, "erro", None, client)
            gravar_log(
                estado["jornada_id"], estado["cpf_cnpj"],
                no_atual, "?", "erro", f"no_id '{no_atual}' nao encontrado no grafo", client
            )
            break

        # Processa o nó
        resultado = processar_no(
            estado, node, adjacencia, edges_por_source, nodes_map, politica, client
        )
        nos_processados += 1

        # Log
        gravar_log(
            estado["jornada_id"], estado["cpf_cnpj"],
            no_atual, node.get("type", "?"),
            resultado["log_acao"], resultado["log_resultado"], client
        )

        # Se parou (esperar ou saída)
        if resultado["status"] in ("aguardando", "concluido", "erro"):
            atualizar_estado(
                estado, no_atual, resultado["status"],
                resultado["proxima_acao_em"], client
            )
            if resultado["status"] == "concluido":
                registrar_participacao_concluida(estado, client)
            break

        # Deve avançar
        proximo = resultado["avancar_para"]
        if not proximo:
            # Sem próximo nó — encerra
            atualizar_estado(estado, no_atual, "concluido", None, client)
            registrar_participacao_concluida(estado, client)
            break

        # Verificar loop
        if not _verificar_loop(estado, proximo, nodes_map, politica):
            atualizar_estado(estado, no_atual, "concluido", None, client)
            gravar_log(
                estado["jornada_id"], estado["cpf_cnpj"],
                proximo, nodes_map.get(proximo, {}).get("type", "?"),
                "loop_excedido", "max_iteracoes atingido", client
            )
            registrar_participacao_concluida(estado, client)
            break

        # Avança
        estado["historico_nos"] = estado.get("historico_nos", []) + [proximo]
        estado["no_atual"] = proximo
        no_atual = proximo

    else:
        # Atingiu max_avancos_por_ciclo — salva estado parcial
        atualizar_estado(estado, no_atual, "ativo", None, client)

    return {
        "nos_processados": nos_processados,
        "status_final": estado.get("status", "ativo"),
        "parou_em": no_atual,
    }


# ---------------------------------------------------------------------------
# EXECUTOR PRINCIPAL
# ---------------------------------------------------------------------------

def executar_motor_jornada(client=None) -> dict[str, Any]:
    """Executa o motor de jornada para todas as jornadas ativas.

    Retorna métricas consolidadas.
    """
    client = client or get_client()
    politica = carregar_politica_global(client)
    jornadas = carregar_jornadas_ativas(client)

    metricas = {
        "jornadas_processadas": 0,
        "novos_entrantes": 0,
        "estados_processados": 0,
        "nos_total": 0,
        "concluidos": 0,
        "aguardando": 0,
        "erros": 0,
        "detalhes": [],
    }

    for jornada in jornadas:
        grafo = parse_grafo(jornada["grafo_json"])
        if not grafo:
            logger.warning(f"Jornada {jornada['jornada_id']} sem grafo válido — skip")
            continue

        nodes_map = nodes_por_id(grafo)
        adjacencia, edges_por_source = construir_adjacencia(grafo)

        # 1. Criar estados para novos entrantes
        novos = criar_estados_novos(jornada, client)
        metricas["novos_entrantes"] += novos

        # 2. Buscar estados prontos
        estados = carregar_estados_prontos(jornada["jornada_id"], client)

        # 3. Processar cada estado
        for estado in estados:
            resultado = processar_estado(
                estado, nodes_map, adjacencia, edges_por_source, politica, client
            )
            metricas["estados_processados"] += 1
            metricas["nos_total"] += resultado["nos_processados"]

            if resultado["status_final"] == "concluido":
                metricas["concluidos"] += 1
            elif resultado["status_final"] == "aguardando":
                metricas["aguardando"] += 1
            elif resultado["status_final"] == "erro":
                metricas["erros"] += 1

        metricas["jornadas_processadas"] += 1
        metricas["detalhes"].append({
            "jornada_id": jornada["jornada_id"],
            "novos": novos,
            "processados": len(estados),
        })

    logger.info(
        f"✓ Motor Jornada: {metricas['jornadas_processadas']} jornadas, "
        f"{metricas['novos_entrantes']} novos, "
        f"{metricas['estados_processados']} processados, "
        f"{metricas['nos_total']} nós percorridos, "
        f"{metricas['concluidos']} concluídos"
    )
    return metricas
