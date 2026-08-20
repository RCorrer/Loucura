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
from fastapi import APIRouter, Depends, HTTPException, Query

from src.db.databricks_client import get_client
from src.core.security import get_user_or_raise, require_perfil
from src.core.config import TABLE_JORNADA, TABLE_CAMPANHA, CATALOG, SCHEMA_ENG
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
