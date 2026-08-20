"""API de Jornadas — Parte A (S3-BACK-05-A): CRUD + Versionamento.

Endpoints:
  GET    /api/jornadas              - Lista paginada (filtro campanha_id, status)
  GET    /api/jornadas/{id}         - Detalhe + grafo + versões
  POST   /api/jornadas              - Criar + vincular campanha + v1
  PUT    /api/jornadas/{id}         - Editar + versionar (só rascunho)
"""

import uuid
import json
import logging
from typing import Optional
from fastapi import APIRouter, Body, Depends, HTTPException, Query

from src.db.databricks_client import get_client
from src.core.security import get_user_or_raise, require_perfil
from src.core.config import TABLE_JORNADA, TABLE_CAMPANHA, CATALOG, SCHEMA_ENG
from src.core.grafo_validator import validar_grafo
from src.models.jornada import (
    JornadaCreate, JornadaUpdate, StatusJornada, TRANSICOES_JORNADA,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _gerar_codigo(nome: str) -> str:
    """Gera código: JOR-{SLUG}-{HEX4}"""
    slug = nome.upper().replace(" ", "-")[:15]
    hex4 = uuid.uuid4().hex[:4].upper()
    return f"JOR-{slug}-{hex4}"


# --- GET /api/jornadas ---
@router.get("")
async def listar_jornadas(
    campanha_id: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_user_or_raise),
):
    """Lista jornadas com filtros e paginação."""
    client = get_client()
    offset = (page - 1) * size
    where = "WHERE 1=1"
    params = []

    if campanha_id:
        where += " AND campanha_id = ?"
        params.append(campanha_id)
    if status:
        where += " AND status = ?"
        params.append(status)

    total_row = client.fetch_one(
        f"SELECT COUNT(*) FROM {TABLE_JORNADA} {where}", tuple(params))
    total = total_row[0] if total_row else 0

    rows = client.fetch_all(
        f"SELECT jornada_id, jornada_codigo, campanha_id, nome, descricao, "
        f"seg_entrada_id, status, versao_atual, criado_por, criado_em, atualizado_em "
        f"FROM {TABLE_JORNADA} {where} ORDER BY atualizado_em DESC LIMIT ? OFFSET ?",
        tuple(params + [size, offset])
    )

    jornadas = [{
        "jornada_id": r[0], "jornada_codigo": r[1], "campanha_id": r[2],
        "nome": r[3], "descricao": r[4], "seg_entrada_id": r[5],
        "status": r[6], "versao_atual": r[7], "criado_por": r[8],
        "criado_em": r[9], "atualizado_em": r[10],
    } for r in rows]

    return {"data": jornadas, "meta": {"total": total, "page": page, "size": size,
            "pages": (total + size - 1) // size if total > 0 else 0}}


# --- GET /api/jornadas/{id} ---
@router.get("/{jornada_id}")
async def detalhe_jornada(jornada_id: str, user: dict = Depends(get_user_or_raise)):
    """Detalhe da jornada + grafo + versões."""
    client = get_client()
    COLS = (
        "jornada_id, jornada_codigo, campanha_id, nome, descricao, grafo_json, "
        "seg_entrada_id, resumo, objetivo_negocio, observacoes, status, "
        "ao_sair_segmento, ao_pausar_campanha, cap_estourado, "
        "aprovado_por, aprovado_em, criado_por, criado_em, owner, "
        "versao_atual, atualizado_em"
    )
    row = client.fetch_one(
        f"SELECT {COLS} FROM {TABLE_JORNADA} WHERE jornada_id = ?", (jornada_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Jornada não encontrada")

    # Versões
    versoes = client.fetch_all(
        f"SELECT versao, alterado_por, alterado_em, motivo "
        f"FROM {CATALOG}.{SCHEMA_ENG}.jornada_versao "
        f"WHERE jornada_id = ? ORDER BY versao DESC",
        (jornada_id,)
    )

    return {"data": {
        "jornada_id": row[0], "jornada_codigo": row[1], "campanha_id": row[2],
        "nome": row[3], "descricao": row[4], "grafo_json": row[5],
        "seg_entrada_id": row[6], "resumo": row[7], "objetivo_negocio": row[8],
        "observacoes": row[9], "status": row[10],
        "ao_sair_segmento": row[11], "ao_pausar_campanha": row[12],
        "cap_estourado": row[13], "aprovado_por": row[14], "aprovado_em": row[15],
        "criado_por": row[16], "criado_em": row[17], "owner": row[18],
        "versao_atual": row[19], "atualizado_em": row[20],
        "versoes": [{"versao": v[0], "alterado_por": v[1], "alterado_em": v[2], "motivo": v[3]} for v in versoes],
    }}


# --- POST /api/jornadas ---
@router.post("", status_code=201)
async def criar_jornada(payload: JornadaCreate, user: dict = Depends(get_user_or_raise)):
    """Cria jornada + vincula a campanha + versão 1."""
    client = get_client()

    # Valida que campanha existe e é editável
    campanha = client.fetch_one(
        f"SELECT status FROM {TABLE_CAMPANHA} WHERE campanha_id = ?",
        (payload.campanha_id,)
    )
    if not campanha:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")
    if campanha[0] not in ("rascunho", "em_aprovacao", "aprovada"):
        raise HTTPException(
            status_code=422,
            detail=f"Não é possível vincular jornada a campanha no status '{campanha[0]}'")

    jornada_id = f"jor_{uuid.uuid4().hex[:10]}"
    jornada_codigo = _gerar_codigo(payload.nome)

    # INSERT jornada (21 colunas no DDL, inserimos 21)
    client.execute_insert(
        f"INSERT INTO {TABLE_JORNADA} "
        f"(jornada_id, jornada_codigo, campanha_id, nome, descricao, grafo_json, "
        f"seg_entrada_id, resumo, objetivo_negocio, observacoes, status, "
        f"ao_sair_segmento, ao_pausar_campanha, cap_estourado, "
        f"aprovado_por, aprovado_em, criado_por, criado_em, owner, "
        f"versao_atual, atualizado_em) "
        f"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'rascunho', "
        f"?, ?, ?, NULL, NULL, ?, current_timestamp(), ?, 1, current_timestamp())",
        (
            jornada_id, jornada_codigo, payload.campanha_id,
            payload.nome, payload.descricao, payload.grafo_json,
            payload.seg_entrada_id, payload.resumo,
            payload.objetivo_negocio, payload.observacoes,
            payload.ao_sair_segmento, payload.ao_pausar_campanha,
            payload.cap_estourado,
            user["usuario_id"], user["usuario_id"],
        )
    )

    # Vincula campanha <-> jornada
    # Calcula próxima ordem
    ordem_row = client.fetch_one(
        f"SELECT COALESCE(MAX(ordem), 0) + 1 FROM {CATALOG}.{SCHEMA_ENG}.campanha_jornada "
        f"WHERE campanha_id = ?",
        (payload.campanha_id,)
    )
    ordem = ordem_row[0] if ordem_row else 1

    client.execute_insert(
        f"INSERT INTO {CATALOG}.{SCHEMA_ENG}.campanha_jornada "
        f"(campanha_id, jornada_id, ordem, ativo) VALUES (?, ?, ?, true)",
        (payload.campanha_id, jornada_id, ordem)
    )

    # Versão 1
    client.execute_insert(
        f"INSERT INTO {CATALOG}.{SCHEMA_ENG}.jornada_versao "
        f"(jornada_id, versao, grafo_json, alterado_por, alterado_em, motivo) "
        f"VALUES (?, 1, ?, ?, current_timestamp(), 'Criação')",
        (jornada_id, payload.grafo_json, user["usuario_id"])
    )

    logger.info(f"✓ Jornada criada: {jornada_codigo} ({jornada_id}) -> campanha {payload.campanha_id}")
    return {"data": {
        "jornada_id": jornada_id,
        "jornada_codigo": jornada_codigo,
        "campanha_id": payload.campanha_id,
        "ordem": ordem,
    }}


# --- PUT /api/jornadas/{id} ---
@router.put("/{jornada_id}")
async def editar_jornada(
    jornada_id: str, payload: JornadaUpdate, user: dict = Depends(get_user_or_raise)
):
    """Edita jornada e cria nova versão (só rascunho)."""
    client = get_client()
    row = client.fetch_one(
        f"SELECT status, versao_atual, grafo_json FROM {TABLE_JORNADA} WHERE jornada_id = ?",
        (jornada_id,)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Jornada não encontrada")
    if row[0] != "rascunho":
        raise HTTPException(status_code=422, detail=f"Não editável no status '{row[0]}'")

    dados = payload.model_dump(exclude_none=True, exclude={"motivo"})
    if not dados:
        raise HTTPException(status_code=422, detail="Nenhum campo para atualizar")

    nova_versao = row[1] + 1
    grafo_atual = row[2]  # grafo vigente (fallback se não editou grafo)
    updates, params = [], []

    for campo, valor in dados.items():
        updates.append(f"{campo} = ?")
        params.append(valor)

    updates.append("versao_atual = ?")
    params.append(nova_versao)
    updates.append("atualizado_em = current_timestamp()")
    params.append(jornada_id)

    client.execute_insert(
        f"UPDATE {TABLE_JORNADA} SET {', '.join(updates)} WHERE jornada_id = ?",
        tuple(params)
    )

    # Nova versão (sempre snapshot do grafo vigente, mesmo se não editado)
    grafo_snap = dados.get("grafo_json", grafo_atual)
    client.execute_insert(
        f"INSERT INTO {CATALOG}.{SCHEMA_ENG}.jornada_versao "
        f"(jornada_id, versao, grafo_json, alterado_por, alterado_em, motivo) "
        f"VALUES (?, ?, ?, ?, current_timestamp(), ?)",
        (jornada_id, nova_versao, grafo_snap, user["usuario_id"], payload.motivo)
    )

    return {"data": {"jornada_id": jornada_id, "versao": nova_versao}}


# --- POST /api/jornadas/{id}/validar ---
@router.post("/{jornada_id}/validar")
async def validar_jornada(jornada_id: str, user: dict = Depends(get_user_or_raise)):
    """Valida o grafo da jornada: estrutura, conectividade, peças, loops."""
    client = get_client()
    row = client.fetch_one(
        f"SELECT grafo_json FROM {TABLE_JORNADA} WHERE jornada_id = ?",
        (jornada_id,)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Jornada não encontrada")

    grafo_json = row[0]

    # Busca peças existentes para validação cruzada
    pecas_rows = client.fetch_all(
        f"SELECT peca_id FROM {CATALOG}.{SCHEMA_ENG}.peca"
    )
    peca_ids_existentes = {r[0] for r in pecas_rows} if pecas_rows else set()

    resultado = validar_grafo(grafo_json, peca_ids_existentes)

    return {"data": {
        "valido": resultado.valido,
        "erros": resultado.erros,
        "avisos": resultado.avisos,
        "stats": resultado.stats,
    }}


# --- POST /api/jornadas/{id}/ativar ---
@router.post("/{jornada_id}/ativar")
async def ativar_jornada(jornada_id: str, user: dict = Depends(require_perfil(["admin"]))):
    """Transita jornada para ATIVA. Exige: status=aprovada + grafo válido + peças aprovadas."""
    client = get_client()
    row = client.fetch_one(
        f"SELECT status, grafo_json FROM {TABLE_JORNADA} WHERE jornada_id = ?",
        (jornada_id,)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Jornada não encontrada")

    status_atual = row[0]
    grafo_json = row[1]

    # Guard: só ativa a partir de APROVADA
    if status_atual != StatusJornada.APROVADA.value:
        try:
            estado_enum = StatusJornada(status_atual)
            permitidos = TRANSICOES_JORNADA.get(estado_enum, [])
            msg_permitidos = [e.value for e in permitidos]
        except ValueError:
            msg_permitidos = ["(status inválido no BD)"]
        raise HTTPException(
            status_code=422,
            detail=f"Não é possível ativar no status '{status_atual}'. "
                   f"Transições permitidas: {msg_permitidos}"
        )

    # Busca peças existentes
    pecas_rows = client.fetch_all(
        f"SELECT peca_id FROM {CATALOG}.{SCHEMA_ENG}.peca"
    )
    peca_ids_existentes = {r[0] for r in pecas_rows} if pecas_rows else set()

    # Validação do grafo
    resultado = validar_grafo(grafo_json, peca_ids_existentes)
    if not resultado.valido:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Grafo possui erros que impedem a ativação",
                "erros": resultado.erros,
            }
        )

    # Valida que peças referenciadas estão APROVADAS
    pecas_ref = set(resultado.stats.get("pecas_referenciadas", []))
    if pecas_ref:
        placeholders = ', '.join(['?' for _ in pecas_ref])
        pecas_nao_aprovadas = client.fetch_all(
            f"SELECT peca_id, nome, status_aprovacao FROM {CATALOG}.{SCHEMA_ENG}.peca "
            f"WHERE peca_id IN ({placeholders}) AND status_aprovacao != 'aprovada'",
            tuple(pecas_ref)
        )
        if pecas_nao_aprovadas:
            nomes = [f"{r[1]} ({r[2]})" for r in pecas_nao_aprovadas]
            raise HTTPException(
                status_code=422,
                detail=f"Peças não aprovadas: {nomes}. Todas devem estar aprovadas para ativar."
            )

    # Transita estado
    client.execute_insert(
        f"UPDATE {TABLE_JORNADA} SET status = ?, atualizado_em = current_timestamp() "
        f"WHERE jornada_id = ?",
        (StatusJornada.ATIVA.value, jornada_id)
    )

    logger.info(f"✓ Jornada ativada: {jornada_id}")
    return {"data": {"status": "ativa", "avisos": resultado.avisos}}


# --- POST /api/jornadas/{id}/preview ---
@router.post("/{jornada_id}/preview")
async def preview_jornada(jornada_id: str, payload: dict = Body(default={}), user: dict = Depends(get_user_or_raise)):
    """Simula percurso no grafo sem enviar (dry-run).

    Payload opcional: {"variaveis": {...}, "decisoes": {"<node_id>": true/false}}
    - variaveis: override de variáveis para renderização
    - decisoes: força resultado de nós condição (true/false path)
    """
    client = get_client()
    row = client.fetch_one(
        f"SELECT grafo_json FROM {TABLE_JORNADA} WHERE jornada_id = ?",
        (jornada_id,)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Jornada não encontrada")

    grafo_json = row[0]
    if not grafo_json:
        raise HTTPException(status_code=422, detail="Jornada não possui grafo definido")

    try:
        grafo = json.loads(grafo_json)
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=422, detail="grafo_json inválido")

    # Parâmetros de simulação
    body = payload or {}
    decisoes_override = body.get("decisoes", {})
    variaveis = body.get("variaveis", {})

    # Simula percurso
    resultado = _simular_percurso(grafo, decisoes_override, variaveis)

    return {"data": resultado}


def _simular_percurso(grafo: dict, decisoes: dict, variaveis: dict) -> dict:
    """Percorre o grafo a partir da entrada, simulando execução.

    Returns:
        dict com: caminho, nos_visitados, decisoes_tomadas, tempo_estimado_dias, alertas
    """
    nodes = {n["id"]: n for n in grafo.get("nodes", []) if isinstance(n, dict) and "id" in n}
    edges = grafo.get("edges", [])

    # Monta adjacência com labels das arestas
    adjacencia = {}  # node_id -> [(target, edge_data)]
    for edge in edges:
        src = edge.get("source")
        tgt = edge.get("target")
        if src and tgt:
            adjacencia.setdefault(src, []).append((tgt, edge.get("data", {})))

    # Encontra nó entrada
    entrada_id = None
    for nid, node in nodes.items():
        if node.get("type") == "entrada":
            entrada_id = nid
            break

    if not entrada_id:
        return {"erro": "Nenhum nó de entrada encontrado", "caminho": []}

    # Calcula limite de iterações permitido (baseado em max_iteracoes global)
    max_iter_global = 0
    for nd in nodes.values():
        mi = nd.get("data", {}).get("max_iteracoes")
        if mi is not None and isinstance(mi, (int, float)) and int(mi) > max_iter_global:
            max_iter_global = int(mi)

    # Percorre
    caminho = []
    decisoes_tomadas = []
    tempo_total_dias = 0
    alertas = []
    visitas = {}  # node_id -> count (permite loops controlados)
    atual = entrada_id
    max_passos = 50  # guard contra loops infinitos

    for _ in range(max_passos):
        visitas[atual] = visitas.get(atual, 0) + 1
        if visitas[atual] > max_iter_global + 1:
            alertas.append(f"Loop detectado em '{atual}' — simulação interrompida após {visitas[atual] - 1} iterações")
            break

        node = nodes.get(atual)
        if not node:
            alertas.append(f"Nó '{atual}' não encontrado no grafo")
            break

        tipo = node.get("type", "")
        data = node.get("data", {})

        passo = {"node_id": atual, "tipo": tipo, "acao": None}

        if tipo == "entrada":
            passo["acao"] = "Segmento de entrada carregado"

        elif tipo == "enviar_peca":
            peca_id = data.get("peca_id", "?")
            passo["acao"] = f"Enviaria peça '{peca_id}'"
            passo["peca_id"] = peca_id

        elif tipo == "esperar":
            dias = data.get("dias", 0)
            horas = data.get("horas", 0)
            tempo_total_dias += dias + (horas / 24)
            if data.get("ate_evento"):
                passo["acao"] = f"Aguardaria evento '{data['ate_evento']}'"
            else:
                passo["acao"] = f"Aguardaria {dias}d {horas}h"

        elif tipo == "condicao":
            campo = data.get("campo", "?")
            op = data.get("op", "?")
            valor = data.get("valor", "?")
            # Decide com base no override ou default True
            decisao = decisoes.get(atual, True)
            passo["acao"] = f"Condição: {campo} {op} {valor} → {'SIM' if decisao else 'NÃO'}"
            passo["decisao"] = decisao
            decisoes_tomadas.append({"node_id": atual, "resultado": decisao})

        elif tipo == "ab_split":
            variantes = data.get("variantes", [])
            escolhida = variantes[0] if variantes else "A"
            passo["acao"] = f"A/B Split → variante '{escolhida}'"
            passo["variante"] = escolhida

        elif tipo == "acao":
            tipo_acao = data.get("tipo_acao", "?")
            passo["acao"] = f"Executaria ação '{tipo_acao}'"

        elif tipo == "saida":
            passo["acao"] = "Cliente sai da jornada"
            caminho.append(passo)
            break

        caminho.append(passo)

        # Próximo nó
        vizinhos = adjacencia.get(atual, [])
        if not vizinhos:
            alertas.append(f"Nó '{atual}' não tem arestas de saída (dead-end)")
            break

        # Escolhe próximo baseado no tipo
        if tipo == "condicao" and len(vizinhos) >= 2:
            # Primeira aresta = true path, segunda = false path
            decisao = decisoes.get(atual, True)
            atual = vizinhos[0][0] if decisao else vizinhos[1][0]
        elif tipo == "ab_split" and len(vizinhos) >= 1:
            # Sempre segue primeira variante na simulação
            atual = vizinhos[0][0]
        else:
            atual = vizinhos[0][0]
    else:
        alertas.append(f"Simulação atingiu limite de {max_passos} passos")

    return {
        "caminho": caminho,
        "total_passos": len(caminho),
        "tempo_estimado_dias": round(tempo_total_dias, 1),
        "decisoes_tomadas": decisoes_tomadas,
        "alertas": alertas,
    }


# --- POST /api/jornadas/{id}/aprovar ---
@router.post("/{jornada_id}/aprovar")
async def aprovar_jornada(jornada_id: str, user: dict = Depends(require_perfil(["admin"]))):
    """Transita jornada para APROVADA. Exige: status=rascunho + grafo válido."""
    client = get_client()
    row = client.fetch_one(
        f"SELECT status, grafo_json FROM {TABLE_JORNADA} WHERE jornada_id = ?",
        (jornada_id,)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Jornada não encontrada")

    status_atual = row[0]
    grafo_json = row[1]

    # Guard: só aprova de RASCUNHO
    if status_atual != StatusJornada.RASCUNHO.value:
        raise HTTPException(
            status_code=422,
            detail=f"Só é possível aprovar no status 'rascunho'. Atual: '{status_atual}'"
        )

    # Valida grafo antes de aprovar
    pecas_rows = client.fetch_all(
        f"SELECT peca_id FROM {CATALOG}.{SCHEMA_ENG}.peca"
    )
    peca_ids_existentes = {r[0] for r in pecas_rows} if pecas_rows else set()

    resultado = validar_grafo(grafo_json, peca_ids_existentes)
    if not resultado.valido:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Grafo possui erros que impedem a aprovação",
                "erros": resultado.erros,
            }
        )

    # Transita
    client.execute_insert(
        f"UPDATE {TABLE_JORNADA} SET status = ?, aprovado_por = ?, "
        f"aprovado_em = current_timestamp(), atualizado_em = current_timestamp() "
        f"WHERE jornada_id = ?",
        (StatusJornada.APROVADA.value, user["usuario_id"], jornada_id)
    )

    logger.info(f"✓ Jornada aprovada: {jornada_id}")
    return {"data": {"status": "aprovada", "avisos": resultado.avisos}}


# --- POST /api/jornadas/{id}/pausar ---
@router.post("/{jornada_id}/pausar")
async def pausar_jornada(jornada_id: str, user: dict = Depends(get_user_or_raise)):
    """Transita jornada para PAUSADA (só de ATIVA)."""
    client = get_client()
    row = client.fetch_one(
        f"SELECT status FROM {TABLE_JORNADA} WHERE jornada_id = ?",
        (jornada_id,)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Jornada não encontrada")

    if row[0] != StatusJornada.ATIVA.value:
        raise HTTPException(
            status_code=422,
            detail=f"Só é possível pausar no status 'ativa'. Atual: '{row[0]}'"
        )

    client.execute_insert(
        f"UPDATE {TABLE_JORNADA} SET status = ?, atualizado_em = current_timestamp() "
        f"WHERE jornada_id = ?",
        (StatusJornada.PAUSADA.value, jornada_id)
    )

    return {"data": {"status": "pausada"}}


# --- POST /api/jornadas/{id}/encerrar ---
@router.post("/{jornada_id}/encerrar")
async def encerrar_jornada(jornada_id: str, user: dict = Depends(get_user_or_raise)):
    """Transita jornada para ENCERRADA (de ATIVA ou PAUSADA)."""
    client = get_client()
    row = client.fetch_one(
        f"SELECT status FROM {TABLE_JORNADA} WHERE jornada_id = ?",
        (jornada_id,)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Jornada não encontrada")

    status_atual = row[0]
    if status_atual not in (StatusJornada.ATIVA.value, StatusJornada.PAUSADA.value):
        raise HTTPException(
            status_code=422,
            detail=f"Só é possível encerrar nos status 'ativa' ou 'pausada'. Atual: '{status_atual}'"
        )

    client.execute_insert(
        f"UPDATE {TABLE_JORNADA} SET status = ?, atualizado_em = current_timestamp() "
        f"WHERE jornada_id = ?",
        (StatusJornada.ENCERRADA.value, jornada_id)
    )

    return {"data": {"status": "encerrada"}}
