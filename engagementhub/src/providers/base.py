"""Interface base para providers de canal (S3-BACK-04).
Novo canal = implementar esta interface + 1 linha no catalogo_canais."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class DispatchResult:
    """Resultado de um disparo."""
    success: bool
    provider_message_id: Optional[str] = None
    error_code: Optional[str] = None
    error_detail: Optional[str] = None
    retryable: bool = False


@dataclass
class DeliveryStatus:
    """Status de entrega consultado do provider."""
    status: str  # enviado/entregue/visualizado/falha
    timestamp: Optional[str] = None
    detail: Optional[str] = None


class ChannelProvider(ABC):
    """
    Interface para providers de canal.
    Implementações: EmailProvider, WhatsAppProvider, (+) novos canais.
    """

    @abstractmethod
    def validar_peca(self, peca: Dict[str, Any]) -> bool:
        """Valida se a peça está compatível com o canal."""
        ...

    @abstractmethod
    def renderizar(self, peca: Dict[str, Any], variaveis: Dict[str, Any]) -> Dict[str, Any]:
        """Renderiza peça com variáveis resolvidas. Retorna conteúdo pronto."""
        ...

    @abstractmethod
    def disparar(self, destinatario: str, conteudo: Dict[str, Any]) -> DispatchResult:
        """Envia a mensagem para o destinatário. Retorna resultado."""
        ...

    @abstractmethod
    def consultar_status(self, envio_id: str) -> DeliveryStatus:
        """Consulta status de entrega (se suportado pelo provider)."""
        ...
