"""Tracking de Click (BACK-09).

Endpoint público que registra o click e redireciona para URL destino.
Usado em emails: <a href="{BASE_URL}/track/click/{envio_id}?url=https://...">
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from urllib.parse import unquote

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import RedirectResponse

from src.core.config import TABLE_TRACKING, TABLE_DISPARO_EVENTOS
from src.db.databricks_client import get_client

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/click/{envio_id}")
async def track_click(
    envio_id: str,
    url: str = Query(..., description="URL destino para redirect"),
):
    """Registra click e redireciona para URL destino.

    Sem auth — endpoint público. Idempotente: registra primeira ocorrência,
    mas sempre redireciona.
    """
    # Validar URL mínima
    target_url = unquote(url)
    if not target_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="URL inválida")

    try:
        client = get_client()
        agora = datetime.now(timezone.utc).isoformat()

        # Atualizar tracking_disparo: setar clicou_em se NULL
        client.execute_insert(
            f"""
            UPDATE {TABLE_TRACKING}
            SET clicou_em = CASE WHEN clicou_em IS NULL THEN ? ELSE clicou_em END,
                status_atual = CASE
                    WHEN status_atual IN ('enviado', 'entregue', 'aberto') THEN 'clicou'
                    ELSE status_atual END,
                atualizado_em = ?
            WHERE envio_id = ?
            """,
            (agora, agora, envio_id),
        )

        # Emitir evento
        _emitir_evento(client, envio_id, "clicou", agora, {"url": target_url})

        logger.info(f"Track click: envio_id={envio_id} -> {target_url[:80]}")
    except Exception as e:
        # Não falhar o redirect — UX > tracking
        logger.warning(f"Track click erro (não-bloqueante): {e}")

    return RedirectResponse(url=target_url, status_code=302)


def _emitir_evento(
    client, envio_id: str, tipo_evento: str, ocorrido_em: str, metadata: dict | None = None
):
    """Registra evento no disparo_eventos."""
    import json
    from uuid import uuid4

    row = client.fetch_one(
        f"SELECT cpf_cnpj, campanha_id, jornada_id, canal FROM {TABLE_TRACKING} WHERE envio_id = ?",
        (envio_id,),
    )
    if not row:
        # envio_id não existe no tracking — não criar evento órfão
        return

    cpf_cnpj = row[0]
    campanha_id = row[1]
    jornada_id = row[2]
    canal = row[3]

    metadata_json = json.dumps(metadata) if metadata else None

    client.execute_insert(
        f"""
        INSERT INTO {TABLE_DISPARO_EVENTOS}
        (evento_id, envio_id, tipo_evento, canal, cpf_cnpj,
         campanha_id, jornada_id, ocorrido_em, metadata_json, criado_em)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"evt_{uuid4().hex[:16]}",
            envio_id,
            tipo_evento,
            canal,
            cpf_cnpj,
            campanha_id,
            jornada_id,
            ocorrido_em,
            metadata_json,
            ocorrido_em,
        ),
    )
