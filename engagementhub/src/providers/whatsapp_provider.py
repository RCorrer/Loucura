"""WhatsApp Provider via Meta Cloud API (S3-BACK-04).

Conecta à API oficial do WhatsApp Business Platform.
Env vars: META_WPP_TOKEN, META_WPP_PHONE_ID, META_WPP_API_VERSION
"""

import os
import re
import time
import logging
from typing import Optional, Dict, Any, List

import httpx

from src.providers.base import (
    ChannelProvider, ChannelCapabilities, DispatchResult,
    DeliveryStatus, HealthCheckResult,
)

logger = logging.getLogger(__name__)

# E.164: +DDI (2-3 digitos) + numero (7-12 digitos)
_PHONE_RE = re.compile(r'^\+[1-9]\d{7,14}$')


class WhatsAppProvider(ChannelProvider):
    """Provider Meta Cloud API para WhatsApp Business."""

    def __init__(self):
        self._token = os.getenv("META_WPP_TOKEN", "")
        self._phone_id = os.getenv("META_WPP_PHONE_ID", "")
        self._api_version = os.getenv("META_WPP_API_VERSION", "v21.0")
        self._base_url = f"https://graph.facebook.com/{self._api_version}/{self._phone_id}"
        self._timeout = int(os.getenv("META_WPP_TIMEOUT", "30"))

    @property
    def canal_id(self) -> str:
        return "whatsapp"

    @property
    def capabilities(self) -> ChannelCapabilities:
        return ChannelCapabilities(
            suporta_html=False,
            suporta_imagem=True,
            suporta_botoes=True,
            suporta_video=True,
            max_caracteres=4096,
            formato_editor="mensagem_simples",
            campos_obrigatorios=["template_meta_id"],
        )

    def validar_destinatario(self, destinatario: str) -> bool:
        """Valida formato E.164."""
        return bool(_PHONE_RE.match(destinatario))

    def validar_peca(self, conteudo: Dict[str, Any]) -> List[str]:
        """Valida peça WhatsApp."""
        erros = []
        tipo = conteudo.get("type")
        if tipo and tipo != "whatsapp":
            erros.append(f"type deve ser 'whatsapp', recebido: '{tipo}'")
        if not conteudo.get("corpo") and not conteudo.get("body"):
            erros.append("Falta 'corpo' ou 'body' no conteúdo")
        params = conteudo.get("params", conteudo.get("variaveis_posicionais", []))
        if not isinstance(params, list):
            erros.append("'params' deve ser uma lista de nomes de variáveis")
        return erros

    def renderizar(self, conteudo: Dict[str, Any], variaveis: Dict[str, Any]) -> Dict[str, Any]:
        """Monta payload da Meta Cloud API com parâmetros resolvidos."""
        template_name = conteudo.get("template", conteudo.get("template_meta_id", ""))
        params = conteudo.get("params", conteudo.get("variaveis_posicionais", []))

        # Resolve variáveis posicionais
        components = []
        if params:
            parameters = []
            for param_name in params:
                valor = variaveis.get(param_name, f"[{param_name}]")
                parameters.append({"type": "text", "text": str(valor)})
            components.append({
                "type": "body",
                "parameters": parameters,
            })

        return {
            "template_name": template_name,
            "components": components,
            "language_code": conteudo.get("language", "pt_BR"),
        }

    def disparar(self, destinatario: str, conteudo_renderizado: Dict[str, Any],
                 metadata: Optional[Dict[str, Any]] = None) -> DispatchResult:
        """Envia mensagem via Meta Cloud API."""
        payload = {
            "messaging_product": "whatsapp",
            "to": destinatario.lstrip("+"),
            "type": "template",
            "template": {
                "name": conteudo_renderizado["template_name"],
                "language": {"code": conteudo_renderizado.get("language_code", "pt_BR")},
            },
        }
        if conteudo_renderizado.get("components"):
            payload["template"]["components"] = conteudo_renderizado["components"]

        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.post(f"{self._base_url}/messages", json=payload, headers=headers)

            if resp.status_code == 200:
                data = resp.json()
                msg_id = data.get("messages", [{}])[0].get("id", "")
                logger.info(f"WPP enviado para {destinatario} | wamid={msg_id}")
                return DispatchResult(success=True, provider_message_id=msg_id)

            # Erros da Meta API
            error_data = resp.json().get("error", {})
            error_code = str(error_data.get("code", resp.status_code))
            error_msg = error_data.get("message", resp.text)
            retryable = resp.status_code in (429, 500, 503)

            logger.warning(f"WPP falhou {destinatario}: {error_code} - {error_msg}")
            return DispatchResult(success=False, error_code=error_code,
                                 error_detail=error_msg, retryable=retryable)

        except httpx.TimeoutException:
            return DispatchResult(success=False, error_code="TIMEOUT",
                                 error_detail="Meta API timeout", retryable=True)
        except Exception as e:
            return DispatchResult(success=False, error_code="CONNECTION_ERROR",
                                 error_detail=str(e), retryable=True)

    def consultar_status(self, provider_message_id: str) -> DeliveryStatus:
        """Consulta status via Meta API (webhooks são preferíveis)."""
        # Meta não tem GET para status individual; vem via webhook
        return DeliveryStatus(
            status="enviado",
            detail="Status atualizado via webhook (não há polling na Meta API)"
        )

    def health_check(self) -> HealthCheckResult:
        """Verifica conectividade com a Meta Graph API."""
        start = time.time()
        try:
            headers = {"Authorization": f"Bearer {self._token}"}
            with httpx.Client(timeout=10) as client:
                resp = client.get(
                    f"https://graph.facebook.com/{self._api_version}/{self._phone_id}",
                    headers=headers,
                )
            latency = int((time.time() - start) * 1000)
            if resp.status_code == 200:
                return HealthCheckResult(healthy=True, latency_ms=latency, detail="Meta API OK")
            else:
                return HealthCheckResult(healthy=False, latency_ms=latency,
                                         detail=f"HTTP {resp.status_code}: {resp.text[:100]}")
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            return HealthCheckResult(healthy=False, latency_ms=latency, detail=str(e))
