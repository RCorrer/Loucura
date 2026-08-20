"""API de Disparo (BACK-08).

Endpoints para consulta de fila, execução manual e estatísticas.
"""

from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException, Query

from src.core.config import TABLE_FILA, TABLE_TRACKING
from src.core.motor_disparo import executar_motor_disparo, processar_item, carregar_fila_pendente
from src.core.security import require_perfil
from src.db.databricks_client import get_client

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/fila")
async def listar_fila(
    status: str = Query(default="pendente"),
    canal: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    """Lista itens da fila de disparo com filtros."""
    client = get_client()
    filtros = ["status = ?"]
    params: list = [status]

    if canal:
        filtros.append("canal = ?")
        params.append(canal)

    where = " AND ".join(filtros)
    params.append(limit)

    rows = client.fetch_all(
        f"""
        SELECT fila_id, cpf_cnpj, campanha_id, jornada_id, peca_id, canal,
               destinatario, agendado_para, prioridade, status, tentativas,
               criado_em, atualizado_em
        FROM {TABLE_FILA}
        WHERE {where}
        ORDER BY agendado_para DESC
        LIMIT ?
        """,
        tuple(params),
    )

    return {
        "data": [
            {
                "fila_id": r[0],
                "cpf_cnpj": r[1],
                "campanha_id": r[2],
                "jornada_id": r[3],
                "peca_id": r[4],
                "canal": r[5],
                "destinatario": r[6],
                "agendado_para": r[7],
                "prioridade": r[8],
                "status": r[9],
                "tentativas": r[10],
                "criado_em": r[11],
                "atualizado_em": r[12],
            }
            for r in (rows or [])
        ]
    }


@router.post("/executar")
async def executar_disparo_manual(
    batch_size: int = Query(default=200, ge=1, le=1000),
    user: dict = Depends(require_perfil(["admin"])),
):
    """Dispara execução manual do motor de disparo."""
    try:
        metricas = executar_motor_disparo(batch_size=batch_size)
        return {
            "data": {
                "executado_por": user["usuario_id"],
                "metricas": metricas,
            }
        }
    except Exception as e:
        logger.exception(f"Erro no motor de disparo: {e}")
        raise HTTPException(status_code=500, detail=f"Falha: {e}")


@router.post("/reprocessar/{fila_id}")
async def reprocessar_item(
    fila_id: str,
    user: dict = Depends(require_perfil(["admin"])),
):
    """Força reprocessamento de um item específico da fila."""
    client = get_client()

    # Buscar item
    row = client.fetch_one(
        f"""
        SELECT fila_id, cpf_cnpj, campanha_id, jornada_id, no_id,
               peca_id, canal, destinatario, agendado_para,
               prioridade, tentativas
        FROM {TABLE_FILA}
        WHERE fila_id = ?
        """,
        (fila_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail=f"fila_id '{fila_id}' não encontrado")

    item = {
        "fila_id": row[0], "cpf_cnpj": row[1], "campanha_id": row[2],
        "jornada_id": row[3], "no_id": row[4], "peca_id": row[5],
        "canal": row[6], "destinatario": row[7], "agendado_para": row[8],
        "prioridade": row[9], "tentativas": int(row[10] or 0),
    }

    resultado = processar_item(item, client)
    return {
        "data": {
            "fila_id": fila_id,
            "reprocessado_por": user["usuario_id"],
            "resultado": resultado,
        }
    }


@router.get("/stats")
async def stats_disparo(
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    """Estatísticas resumidas de fila + tracking."""
    client = get_client()

    fila_stats = client.fetch_one(
        f"""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN status = 'pendente' THEN 1 ELSE 0 END),
            SUM(CASE WHEN status = 'enviado' THEN 1 ELSE 0 END),
            SUM(CASE WHEN status = 'falha' THEN 1 ELSE 0 END),
            SUM(CASE WHEN status = 'processado' THEN 1 ELSE 0 END)
        FROM {TABLE_FILA}
        """
    )

    tracking_stats = client.fetch_one(
        f"""
        SELECT
            COUNT(*),
            SUM(CASE WHEN status_atual = 'enviado' THEN 1 ELSE 0 END),
            SUM(CASE WHEN status_atual = 'aberto' THEN 1 ELSE 0 END),
            SUM(CASE WHEN status_atual = 'clicou' THEN 1 ELSE 0 END),
            SUM(CASE WHEN status_atual = 'converteu' THEN 1 ELSE 0 END),
            SUM(CASE WHEN status_atual = 'falha' THEN 1 ELSE 0 END)
        FROM {TABLE_TRACKING}
        """
    )

    return {
        "data": {
            "fila": {
                "total": int(fila_stats[0] or 0) if fila_stats else 0,
                "pendente": int(fila_stats[1] or 0) if fila_stats else 0,
                "enviado": int(fila_stats[2] or 0) if fila_stats else 0,
                "falha": int(fila_stats[3] or 0) if fila_stats else 0,
                "processado": int(fila_stats[4] or 0) if fila_stats else 0,
            },
            "tracking": {
                "total": int(tracking_stats[0] or 0) if tracking_stats else 0,
                "enviado": int(tracking_stats[1] or 0) if tracking_stats else 0,
                "aberto": int(tracking_stats[2] or 0) if tracking_stats else 0,
                "clicou": int(tracking_stats[3] or 0) if tracking_stats else 0,
                "converteu": int(tracking_stats[4] or 0) if tracking_stats else 0,
                "falha": int(tracking_stats[5] or 0) if tracking_stats else 0,
            },
        }
    }
