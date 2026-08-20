"""API administrativa do Orquestrador S3."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from src.core.config import TABLE_FILA, TABLE_SUPRESSAO
from src.core.orquestrador import executar_orquestrador
from src.core.security import require_perfil
from src.db.databricks_client import get_client

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/executar")
async def executar_orquestrador_manual(
    payload: dict | None = Body(default=None),
    user: dict = Depends(require_perfil(["admin"])),
):
    """Dispara execução manual do orquestrador."""
    body = payload or {}
    try:
        resultado = executar_orquestrador()
        return {
            "data": {
                "executado_por": user["usuario_id"],
                "modo": body.get("modo", "manual"),
                "resultado": resultado,
            }
        }
    except Exception as e:
        logger.exception(f"Erro ao executar orquestrador: {e}")
        raise HTTPException(status_code=500, detail=f"Falha ao executar orquestrador: {e}")


@router.get("/status")
async def status_orquestrador(user: dict = Depends(require_perfil(["admin", "analista"]))):
    """Resumo operacional simples baseado em fila + supressões recentes."""
    client = get_client()

    fila = client.fetch_one(
        f"""
        SELECT COUNT(*),
               SUM(CASE WHEN status = 'pendente' THEN 1 ELSE 0 END),
               SUM(CASE WHEN status = 'enviado' THEN 1 ELSE 0 END),
               SUM(CASE WHEN status = 'falha' THEN 1 ELSE 0 END)
        FROM {TABLE_FILA}
        """
    )
    cutoff_24h = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    sup = client.fetch_one(
        f"SELECT COUNT(*) FROM {TABLE_SUPRESSAO} WHERE data_execucao >= ?",
        (cutoff_24h,)
    )

    return {
        "data": {
            "fila_total": int(fila[0]) if fila and fila[0] is not None else 0,
            "fila_pendente": int(fila[1]) if fila and fila[1] is not None else 0,
            "fila_enviado": int(fila[2]) if fila and fila[2] is not None else 0,
            "fila_falha": int(fila[3]) if fila and fila[3] is not None else 0,
            "supressoes_24h": int(sup[0]) if sup and sup[0] is not None else 0,
        }
    }


@router.get("/supressoes")
async def listar_supressoes(
    limit: int = Query(default=50, ge=1, le=500),
    motivo: str | None = Query(default=None),
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    """Lista supressões recentes com filtro opcional por motivo."""
    client = get_client()

    if motivo:
        rows = client.fetch_all(
            f"""
            SELECT supressao_id, cpf_cnpj, campanha_id, canal, motivo, detalhe, data_execucao
            FROM {TABLE_SUPRESSAO}
            WHERE motivo = ?
            ORDER BY data_execucao DESC
            LIMIT {int(limit)}
            """,
            (motivo,),
        )
    else:
        rows = client.fetch_all(
            f"""
            SELECT supressao_id, cpf_cnpj, campanha_id, canal, motivo, detalhe, data_execucao
            FROM {TABLE_SUPRESSAO}
            ORDER BY data_execucao DESC
            LIMIT {int(limit)}
            """
        )

    return {
        "data": [
            {
                "supressao_id": r[0],
                "cpf_cnpj": r[1],
                "campanha_id": r[2],
                "canal": r[3],
                "motivo": r[4],
                "detalhe": r[5],
                "data_execucao": r[6],
            }
            for r in rows or []
        ]
    }


@router.put("/config")
async def atualizar_config_orquestrador(
    payload: dict | None = Body(default=None),
    user: dict = Depends(require_perfil(["admin"])),
):
    """Placeholder de configuração até persistência dedicada no BACK-12/Admin."""
    body = payload or {}
    config = {
        "batch_size": int(body.get("batch_size", 1000)),
        "modo_waterfall": body.get("modo_waterfall", "prioridade"),
        "respeitar_consentimento": bool(body.get("respeitar_consentimento", True)),
        "respeitar_capping": bool(body.get("respeitar_capping", True)),
    }
    return {
        "data": {
            "salvo": False,
            "config": config,
            "observacao": "Persistência ficará para BACK-12/Admin",
        }
    }
