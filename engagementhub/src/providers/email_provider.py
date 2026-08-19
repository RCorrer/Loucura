"""Email Provider via SMTP (S3-BACK-04).

Conecta ao relay SMTP corporativo Bradesco.
Env vars: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM
"""

import os
import re
import time
import uuid
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any, List

from src.providers.base import (
    ChannelProvider, ChannelCapabilities, DispatchResult,
    DeliveryStatus, HealthCheckResult,
)
from src.core.render_engine import render_preview

logger = logging.getLogger(__name__)

# Regex para email básico
_EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')


class EmailProvider(ChannelProvider):
    """Provider SMTP para envio de emails transacionais."""

    def __init__(self):
        self._host = os.getenv("SMTP_HOST", "smtp.bradesco.com.br")
        self._port = int(os.getenv("SMTP_PORT", "587"))
        self._user = os.getenv("SMTP_USER", "")
        self._password = os.getenv("SMTP_PASS", "")
        self._from_addr = os.getenv("SMTP_FROM", "noreply@bradesco.com.br")
        self._from_name = os.getenv("SMTP_FROM_NAME", "Bradesco")
        self._use_tls = os.getenv("SMTP_TLS", "true").lower() == "true"

    @property
    def canal_id(self) -> str:
        return "email"

    @property
    def capabilities(self) -> ChannelCapabilities:
        return ChannelCapabilities(
            suporta_html=True,
            suporta_imagem=True,
            suporta_botoes=True,
            suporta_video=False,
            max_caracteres=None,  # sem limite prático
            formato_editor="rico_html",
            campos_obrigatorios=["assunto", "conteudo_json"],
        )

    def validar_destinatario(self, destinatario: str) -> bool:
        """Valida formato de email."""
        return bool(_EMAIL_RE.match(destinatario))

    def validar_peca(self, conteudo: Dict[str, Any]) -> List[str]:
        """Valida peça de email."""
        erros = []
        if not conteudo.get("blocks"):
            erros.append("conteudo_json deve conter 'blocks' (lista de blocos)")
        tipo = conteudo.get("type")
        if tipo and tipo != "email":
            erros.append(f"type deve ser 'email', recebido: '{tipo}'")
        return erros

    def renderizar(self, conteudo: Dict[str, Any], variaveis: Dict[str, Any]) -> Dict[str, Any]:
        """Renderiza email: blocks → HTML via render_engine."""
        import json
        conteudo_str = json.dumps(conteudo) if isinstance(conteudo, dict) else conteudo
        result = render_preview(
            conteudo_json=conteudo_str,
            canal="email",
            variaveis_override=variaveis,
            assunto=conteudo.get("subject", ""),
        )
        return {
            "html": result["html"],
            "assunto": result["assunto_renderizado"] or conteudo.get("subject", "(sem assunto)"),
        }

    def disparar(self, destinatario: str, conteudo_renderizado: Dict[str, Any],
                 metadata: Optional[Dict[str, Any]] = None) -> DispatchResult:
        """Envia email via SMTP."""
        msg_id = f"<{uuid.uuid4().hex}@bradesco.com.br>"

        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = f"{self._from_name} <{self._from_addr}>"
            msg["To"] = destinatario
            msg["Subject"] = conteudo_renderizado.get("assunto", "")
            msg["Message-ID"] = msg_id

            # Header de rastreio (para webhooks de bounce)
            if metadata and metadata.get("envio_id"):
                msg["X-Engagement-ID"] = metadata["envio_id"]

            html_body = conteudo_renderizado.get("html", "")
            msg.attach(MIMEText(html_body, "html", "utf-8"))

            with smtplib.SMTP(self._host, self._port, timeout=30) as server:
                if self._use_tls:
                    server.starttls()
                if self._user:
                    server.login(self._user, self._password)
                server.sendmail(self._from_addr, [destinatario], msg.as_string())

            logger.info(f"Email enviado para {destinatario} | msg_id={msg_id}")
            return DispatchResult(success=True, provider_message_id=msg_id)

        except smtplib.SMTPRecipientsRefused as e:
            return DispatchResult(success=False, error_code="RECIPIENT_REFUSED",
                                 error_detail=str(e), retryable=False)
        except smtplib.SMTPAuthenticationError as e:
            return DispatchResult(success=False, error_code="AUTH_FAILED",
                                 error_detail=str(e), retryable=False)
        except (smtplib.SMTPException, OSError) as e:
            return DispatchResult(success=False, error_code="SMTP_ERROR",
                                 error_detail=str(e), retryable=True)

    def consultar_status(self, provider_message_id: str) -> DeliveryStatus:
        """SMTP não suporta consulta ativa — status vem via webhook de bounce/open."""
        return DeliveryStatus(status="enviado", detail="SMTP fire-and-forget; tracking via webhook")

    def health_check(self) -> HealthCheckResult:
        """Verifica conectividade SMTP."""
        start = time.time()
        try:
            with smtplib.SMTP(self._host, self._port, timeout=10) as server:
                if self._use_tls:
                    server.starttls()
                server.noop()
            latency = int((time.time() - start) * 1000)
            return HealthCheckResult(healthy=True, latency_ms=latency, detail="SMTP OK")
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            return HealthCheckResult(healthy=False, latency_ms=latency, detail=str(e))
