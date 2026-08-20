"""Tracking de Abertura (BACK-09).

Endpoint público que retorna pixel 1x1 GIF transparente.
Quando o email client carrega a imagem, registra a abertura.

Usado em emails: <img src="{BASE_URL}/track/open/{envio_id}" />
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Response
from fastapi.responses import Response as FastAPIResponse

from src.core.config import TABLE_TRACKING, TABLE_DISPARO_EVENTOS
from src.db.databricks_client import get_client

logger = logging.getLogger(__name__)

router = APIRouter()

# Pixel transparente 1x1 GIF (43 bytes)
_PIXEL_GIF = (
    b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00"
    b"\x80\x00\x00\xff\xff\xff\x00\x00\x00\x21"
    b"\xf9\x04\x00\x00\x00\x00\x00\x2c\x00\x00"
    b"\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44"
    b"\x01\x00\x3b"
)


@router.get("/open/{envio_id}")
async def track_open(envio_id: str):
    """Registra abertura de email via pixel tracking.

    Retorna GIF 1x1 transparente (sem auth — endpoint público).
    Idempotente: primeira abertura registra timestamp, demais ignoram.
    """
    try:
        client = get_client()
        agora = datetime.now(timezone.utc).isoformat()

        # Atualizar tracking_disparo: setar aberto_em se NULL (primeira abertura)
        client.execute_insert(
            f"""
            UPDATE {TABLE_TRACKING}
            SET aberto_em = CASE WHEN aberto_em IS NULL THEN ? ELSE aberto_em END,
                status_atual = CASE WHEN status_atual = 'enviado' THEN 'aberto'
                               WHEN status_atual = 'entregue' THEN 'aberto'
                               ELSE status_atual END,
                atualizado_em = ?
            WHERE envio_id = ?
            """,
            (agora, agora, envio_id),
        )

        # Emitir evento
        _emitir_evento(client, envio_id, "aberto", agora)

        logger.info(f"Track open: envio_id={envio_id}")
    except Exception as e:
        # Não falhar a response — pixel deve sempre retornar
        logger.warning(f"Track open erro (não-bloqueante): {e}")

    return Response(
        content=_PIXEL_GIF,
        media_type="image/gif",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


def _emitir_evento(client, envio_id: str, tipo_evento: str, ocorrido_em: str):
    """Registra evento no disparo_eventos (append-only)."""
    from uuid import uuid4

    # Buscar dados do tracking para enriquecer o evento
    row = client.fetch_one(
        f"SELECT cpf_cnpj, campanha_id, jornada_id, canal FROM {TABLE_TRACKING} WHERE envio_id = ?",
        (envio_id,),
    )
    cpf_cnpj = row[0] if row else None
    campanha_id = row[1] if row else None
    jornada_id = row[2] if row else None
    canal = row[3] if row else None

    client.execute_insert(
        f"""
        INSERT INTO {TABLE_DISPARO_EVENTOS}
        (evento_id, envio_id, tipo_evento, canal, cpf_cnpj,
         campanha_id, jornada_id, ocorrido_em, metadata_json, criado_em)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)
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
            ocorrido_em,
        ),
    )
