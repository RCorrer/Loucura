"""
Cliente para Foundation Model via API REST (stateless).
"""

import os
import logging
import json
import requests
from typing import Optional, Dict, Any

from src.core.config import AppConfig

logger = logging.getLogger(__name__)


class LLMClient:
    """Cliente para chamar Foundation Model via REST."""

    def __init__(self, model: str = "databricks-llama-4-maverick"):
        self.model = model
        self.host = AppConfig.DATABRICKS_HOST.replace("https://", "")
        self.token = AppConfig.DATABRICKS_TOKEN

        # Endpoint do modelo (via Model Serving ou AI Gateway)
        self.endpoint = f"https://{self.host}/serving-endpoints/{self.model}/invocations"

    def chat_completion(
        self,
        messages: list,
        temperature: float = 0.3,
        max_tokens: int = 1000,
    ) -> Dict[str, Any]:
        """
        Envia uma lista de mensagens e retorna a resposta do modelo.
        """
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

        # Estrutura de payload para Foundation Model API (compatível com OpenAI)
        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            logger.info(f"Chamando modelo {self.model} em {self.endpoint}")
            response = requests.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()

            # Resposta pode vir em diferentes formatos
            # Tentamos extrair o conteúdo da mensagem
            if "choices" in data:
                return data["choices"][0]["message"]
            elif "response" in data:
                return {"role": "assistant", "content": data["response"]}
            else:
                return {"role": "assistant", "content": str(data)}

        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao chamar LLM: {e}")
            raise RuntimeError(f"Falha na comunicação com o modelo: {e}")
        except Exception as e:
            logger.error(f"Erro inesperado: {e}")
            raise