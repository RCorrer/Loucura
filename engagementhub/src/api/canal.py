"""API de Canais (S3-BACK-04): CRUD + Health Check + Provider info."""

import json
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from src.db.databricks_client import get_client
from src.core.security import get_user_or_raise, require_perfil
from src.core.config import TABLE_CANAIS
from src.models.canal import CanalCreate, CanalUpdate
from src.providers.registry import get_provider, list_providers

logger = logging.getLogger(__name__)
router = APIRouter()


# --- GET /api/canais/providers (ANTES de /{canal_id} para evitar conflito) ---
@router.get("/providers")
async def listar_providers_disponiveis(user: dict = Depends(require_perfil(["admin"]))):
    """Lista providers registrados no sistema."""
    return {"data": list_providers()}


# --- GET /api/canais ---
@router.get("")
async def listar_canais(
    ativo: Optional[bool] = None,
    user: dict = Depends(get_user_or_raise),
):
    client = get_client()
    where = "WHERE 1=1"
    params = []
    if ativo is not None:
        where += " AND ativo = ?"
        params.append(ativo)

    rows = client.fetch_all(
        f"SELECT canal_id, nome_exibicao, icone, suporta_html, suporta_imagem, "
        f"suporta_botoes, suporta_video, max_caracteres, formato_editor, "
        f"campos_obrigatorios, provider_class, rate_limit_por_segundo, "
        f"rate_limit_por_dia, ativo, atualizado_em "
        f"FROM {TABLE_CANAIS} {where} ORDER BY nome_exibicao",
        tuple(params)
    )
    return {"data": [_row_to_dict(r) for r in rows]}


# --- GET /api/canais/{canal_id} ---
@router.get("/{canal_id}")
async def detalhe_canal(canal_id: str, user: dict = Depends(get_user_or_raise)):
    client = get_client()
    row = client.fetch_one(
        f"SELECT canal_id, nome_exibicao, icone, suporta_html, suporta_imagem, "
        f"suporta_botoes, suporta_video, max_caracteres, formato_editor, "
        f"campos_obrigatorios, provider_class, rate_limit_por_segundo, "
        f"rate_limit_por_dia, ativo, atualizado_em "
        f"FROM {TABLE_CANAIS} WHERE canal_id = ?",
        (canal_id,)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Canal nao encontrado")

    canal = _row_to_dict(row)
    try:
        provider = get_provider(row[10])
        canal["provider_info"] = {
            "capabilities": {
                "suporta_html": provider.capabilities.suporta_html,
                "suporta_imagem": provider.capabilities.suporta_imagem,
                "suporta_botoes": provider.capabilities.suporta_botoes,
                "max_caracteres": provider.capabilities.max_caracteres,
                "formato_editor": provider.capabilities.formato_editor,
            },
            "registered": True,
        }
    except ValueError:
        canal["provider_info"] = {"registered": False}
    return {"data": canal}


# --- POST /api/canais (admin) ---
@router.post("", status_code=201)
async def criar_canal(payload: CanalCreate, user: dict = Depends(require_perfil(["admin"]))):
    client = get_client()
    try:
        get_provider(payload.provider_class)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    existing = client.fetch_one(
        f"SELECT canal_id FROM {TABLE_CANAIS} WHERE canal_id = ?", (payload.canal_id,))
    if existing:
        raise HTTPException(status_code=409, detail=f"Canal '{payload.canal_id}' ja existe")

    campos_json = json.dumps(payload.campos_obrigatorios) if payload.campos_obrigatorios else None
    client.execute_insert(
        f"INSERT INTO {TABLE_CANAIS} "
        f"(canal_id, nome_exibicao, icone, suporta_html, suporta_imagem, "
        f"suporta_botoes, suporta_video, max_caracteres, formato_editor, "
        f"campos_obrigatorios, provider_class, rate_limit_por_segundo, "
        f"rate_limit_por_dia, ativo, atualizado_em) "
        f"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, true, current_timestamp())",
        (payload.canal_id, payload.nome_exibicao, payload.icone,
         payload.suporta_html, payload.suporta_imagem, payload.suporta_botoes,
         payload.suporta_video, payload.max_caracteres, payload.formato_editor,
         campos_json, payload.provider_class, payload.rate_limit_por_segundo,
         payload.rate_limit_por_dia)
    )
    return {"data": {"canal_id": payload.canal_id, "message": "Canal criado"}}


# --- PUT /api/canais/{canal_id} (admin) ---
@router.put("/{canal_id}")
async def atualizar_canal(
    canal_id: str, payload: CanalUpdate, user: dict = Depends(require_perfil(["admin"]))
):
    client = get_client()
    existing = client.fetch_one(
        f"SELECT canal_id FROM {TABLE_CANAIS} WHERE canal_id = ?", (canal_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Canal nao encontrado")

    dados = payload.model_dump(exclude_none=True)
    if not dados:
        raise HTTPException(status_code=422, detail="Nenhum campo para atualizar")

    if "provider_class" in dados:
        try:
            get_provider(dados["provider_class"])
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

    updates, params = [], []
    for campo, valor in dados.items():
        if campo == "campos_obrigatorios":
            updates.append("campos_obrigatorios = ?")
            params.append(json.dumps(valor))
        else:
            updates.append(f"{campo} = ?")
            params.append(valor)

    updates.append("atualizado_em = current_timestamp()")
    params.append(canal_id)
    client.execute_insert(
        f"UPDATE {TABLE_CANAIS} SET {', '.join(updates)} WHERE canal_id = ?",
        tuple(params)
    )
    return {"data": {"canal_id": canal_id, "message": "Canal atualizado"}}


# --- POST /api/canais/{canal_id}/health ---
@router.post("/{canal_id}/health")
async def health_check_canal(canal_id: str, user: dict = Depends(require_perfil(["admin"]))):
    client = get_client()
    row = client.fetch_one(
        f"SELECT provider_class FROM {TABLE_CANAIS} WHERE canal_id = ?", (canal_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Canal nao encontrado")

    try:
        provider = get_provider(row[0])
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    result = provider.health_check()
    return {"data": {
        "canal_id": canal_id,
        "healthy": result.healthy,
        "latency_ms": result.latency_ms,
        "detail": result.detail,
    }}


def _row_to_dict(row) -> dict:
    campos_raw = row[9]
    campos = json.loads(campos_raw) if isinstance(campos_raw, str) and campos_raw else campos_raw
    return {
        "canal_id": row[0], "nome_exibicao": row[1], "icone": row[2],
        "suporta_html": row[3], "suporta_imagem": row[4],
        "suporta_botoes": row[5], "suporta_video": row[6],
        "max_caracteres": row[7], "formato_editor": row[8],
        "campos_obrigatorios": campos, "provider_class": row[10],
        "rate_limit_por_segundo": row[11], "rate_limit_por_dia": row[12],
        "ativo": row[13], "atualizado_em": row[14],
    }
