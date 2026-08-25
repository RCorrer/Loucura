"""Webhooks de Providers (BACK-09).

Recebe notificações assíncronas dos providers de canal:
- Meta Cloud API (WhatsApp): status de mensagem (delivered, read, failed)
- Email (SMTP bounce/delivery): notificações via header tracking

Atualiza tracking_disparo e emite disparo_eventos.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import PlainTextResponse

from src.core.config import TABLE_TRACKING, TABLE_DISPARO_EVENTOS
from src.db.databricks_client import get_client

# Ordem do funil — só avançar, nunca regredir
_FUNIL_ORDEM = {
    "pendente": 0, "processando": 1, "enviado": 2,
    "entregue": 3, "aberto": 4, "clicou": 5, "converteu": 6,
    "falha": -1,
}

logger = logging.getLogger(__name__)

router = APIRouter()

# Meta Webhook Verify Token
_META_VERIFY_TOKEN = os.getenv("META_WPP_VERIFY_TOKEN", "engagementhub_verify_2026")
_META_APP_SECRET = os.getenv("META_WPP_APP_SECRET", "")


# ---------------------------------------------------------------------------
# WhatsApp (Meta Cloud API) Webhooks
# ---------------------------------------------------------------------------

@router.get("/whatsapp")
async def whatsapp_verify(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """Webhook verification (Meta envia GET para validar endpoint)."""
    if hub_mode == "subscribe" and hub_verify_token == _META_VERIFY_TOKEN:
        logger.info("WhatsApp webhook verificado com sucesso")
        return int(hub_challenge) if hub_challenge else 0
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    """Recebe status updates do WhatsApp (delivered, read, failed).

    Payload Meta:
    {
      "entry": [{"changes": [{"value": {
        "statuses": [{
          "id": "wamid.xxx",
          "status": "delivered|read|failed",
          "timestamp": "1692000000",
          "errors": [{"code": 131047, "title": "..."}]
        }]
      }}]}]
    }
    """
    body = await request.body()

    # Validar assinatura (opcional, mas recomendado em prod)
    if _META_APP_SECRET:
        signature = request.headers.get("X-Hub-Signature-256", "")
        if not _verify_meta_signature(body, signature):
            raise HTTPException(status_code=403, detail="Assinatura inválida")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="JSON inválido")

    processados = 0
    client = get_client()

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for status_obj in value.get("statuses", []):
                wamid = status_obj.get("id", "")
                status = status_obj.get("status", "")
                timestamp = status_obj.get("timestamp", "")
                errors = status_obj.get("errors", [])

                _processar_status_whatsapp(client, wamid, status, timestamp, errors)
                processados += 1

    logger.info(f"WhatsApp webhook: {processados} status processados")
    return {"processados": processados}


def _processar_status_whatsapp(
    client, wamid: str, status: str, timestamp: str, errors: list
):
    """Atualiza tracking_disparo com base no status do WhatsApp."""
    agora = datetime.now(timezone.utc).isoformat()

    # Converter timestamp Unix para ISO
    try:
        ocorrido_em = datetime.fromtimestamp(int(timestamp), tz=timezone.utc).isoformat()
    except (ValueError, TypeError, OSError):
        ocorrido_em = agora

    # Mapear status Meta → nosso funil
    status_map = {
        "sent": ("enviado", "enviado_em"),
        "delivered": ("entregue", "entregue_em"),
        "read": ("aberto", "visualizado_em"),
        "failed": ("falha", None),
    }

    mapeado = status_map.get(status)
    if not mapeado:
        logger.debug(f"Status WPP ignorado: {status} (wamid={wamid})")
        return

    status_nosso, coluna_data = mapeado
    erro_detalhe = errors[0].get("title", "") if errors else None

    # UPDATE tracking_disparo por provider_message_id
    if coluna_data:
        client.execute_insert(
            f"""
            UPDATE {TABLE_TRACKING}
            SET {coluna_data} = CASE WHEN {coluna_data} IS NULL THEN ? ELSE {coluna_data} END,
                status_atual = ?,
                atualizado_em = ?
            WHERE provider_message_id = ?
            """,
            (ocorrido_em, status_nosso, agora, wamid),
        )
    else:
        # Falha: atualizar status + erro
        client.execute_insert(
            f"""
            UPDATE {TABLE_TRACKING}
            SET status_atual = 'falha',
                erro_detalhe = ?,
                atualizado_em = ?
            WHERE provider_message_id = ?
            """,
            (erro_detalhe, agora, wamid),
        )

    # Emitir evento
    _emitir_evento_por_provider_id(client, wamid, status_nosso, ocorrido_em, {
        "provider": "whatsapp",
        "status_original": status,
        "erro": erro_detalhe,
    })


# ---------------------------------------------------------------------------
# Email Webhooks (bounce/delivery)
# ---------------------------------------------------------------------------

@router.post("/email")
async def email_webhook(request: Request):
    """Recebe notificações de email (bounce, delivery, complaint).

    Formato genérico (adaptado por relay corporativo):
    {
      "events": [{
        "type": "delivered|bounced|complained|opened",
        "message_id": "<uuid@bradesco.com.br>",
        "timestamp": "2026-08-20T10:00:00Z",
        "detail": "..."
      }]
    }
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON inválido")

    processados = 0
    client = get_client()

    for event in payload.get("events", []):
        event_type = event.get("type", "")
        message_id = event.get("message_id", "")
        timestamp = event.get("timestamp", datetime.now(timezone.utc).isoformat())
        detail = event.get("detail", "")

        _processar_evento_email(client, event_type, message_id, timestamp, detail)
        processados += 1

    logger.info(f"Email webhook: {processados} eventos processados")
    return {"processados": processados}


def _processar_evento_email(
    client, event_type: str, message_id: str, timestamp: str, detail: str
):
    """Atualiza tracking_disparo com base em evento de email."""
    agora = datetime.now(timezone.utc).isoformat()

    # Mapear tipo de evento → nosso funil
    type_map = {
        "delivered": ("entregue", "entregue_em"),
        "bounced": ("falha", None),
        "complained": ("falha", None),
        "opened": ("aberto", "aberto_em"),
    }

    mapeado = type_map.get(event_type)
    if not mapeado:
        logger.debug(f"Evento email ignorado: {event_type} (msg={message_id})")
        return

    status_nosso, coluna_data = mapeado

    if coluna_data:
        client.execute_insert(
            f"""
            UPDATE {TABLE_TRACKING}
            SET {coluna_data} = CASE WHEN {coluna_data} IS NULL THEN ? ELSE {coluna_data} END,
                status_atual = ?,
                atualizado_em = ?
            WHERE provider_message_id = ?
            """,
            (timestamp, status_nosso, agora, message_id),
        )
    else:
        # Bounce/complaint: marcar falha
        client.execute_insert(
            f"""
            UPDATE {TABLE_TRACKING}
            SET status_atual = 'falha',
                erro_detalhe = ?,
                atualizado_em = ?
            WHERE provider_message_id = ?
            """,
            (f"{event_type}: {detail}"[:500], agora, message_id),
        )

    _emitir_evento_por_provider_id(client, message_id, status_nosso, timestamp, {
        "provider": "email",
        "event_type": event_type,
        "detail": detail,
    })


# ---------------------------------------------------------------------------
# Conversão (genérico)
# ---------------------------------------------------------------------------

@router.post("/conversao")
async def registrar_conversao(request: Request):
    """Registra conversão para um envio específico.

    Payload: {"envio_id": "...", "valor": 100.0, "tipo": "compra"}
    Usado pelo JOB-07 (consumidor_conversao) ou por sistemas externos.
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON inválido")

    envio_id = payload.get("envio_id")
    if not envio_id:
        raise HTTPException(status_code=400, detail="envio_id obrigatório")

    client = get_client()
    agora = datetime.now(timezone.utc).isoformat()

    # Atualizar tracking
    client.execute_insert(
        f"""
        UPDATE {TABLE_TRACKING}
        SET converteu_em = CASE WHEN converteu_em IS NULL THEN ? ELSE converteu_em END,
            status_atual = 'converteu',
            atualizado_em = ?
        WHERE envio_id = ?
        """,
        (agora, agora, envio_id),
    )

    # Emitir evento
    _emitir_evento_direto(client, envio_id, "converteu", agora, {
        "valor": payload.get("valor"),
        "tipo": payload.get("tipo"),
    })

    logger.info(f"Conversão registrada: envio_id={envio_id}")
    return {"data": {"envio_id": envio_id, "status": "converteu"}}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _verify_meta_signature(body: bytes, signature_header: str) -> bool:
    """Verifica X-Hub-Signature-256 da Meta."""
    if not signature_header.startswith("sha256="):
        return False
    expected = signature_header[7:]
    computed = hmac.new(
        _META_APP_SECRET.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, computed)


def _emitir_evento_por_provider_id(
    client, provider_message_id: str, tipo_evento: str,
    ocorrido_em: str, metadata: dict | None = None
):
    """Emite evento buscando envio_id pelo provider_message_id."""
    row = client.fetch_one(
        f"SELECT envio_id, cpf_cnpj, campanha_id, jornada_id, canal FROM {TABLE_TRACKING} WHERE provider_message_id = ?",
        (provider_message_id,),
    )
    if not row:
        logger.warning(f"Evento ignorado: provider_message_id={provider_message_id} não encontrado")
        return

    envio_id, cpf_cnpj, campanha_id, jornada_id, canal = row

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


def _emitir_evento_direto(
    client, envio_id: str, tipo_evento: str,
    ocorrido_em: str, metadata: dict | None = None
):
    """Emite evento quando já temos o envio_id."""
    row = client.fetch_one(
        f"SELECT cpf_cnpj, campanha_id, jornada_id, canal FROM {TABLE_TRACKING} WHERE envio_id = ?",
        (envio_id,),
    )
    cpf_cnpj = row[0] if row else None
    campanha_id = row[1] if row else None
    jornada_id = row[2] if row else None
    canal = row[3] if row else None

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
