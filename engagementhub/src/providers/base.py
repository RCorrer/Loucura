"""Interface base para providers de canal (S3-BACK-04).
Novo canal = implementar esta interface + 1 linha no catalogo_canais."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


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


@dataclass
class ChannelCapabilities:
    """Capacidades do canal."""
    suporta_html: bool = False
    suporta_imagem: bool = False
    suporta_botoes: bool = False
    suporta_video: bool = False
    max_caracteres: Optional[int] = None
    formato_editor: str = "mensagem_simples"  # rico_html / mensagem_simples / card
    campos_obrigatorios: List[str] = field(default_factory=list)


@dataclass
class HealthCheckResult:
    """Resultado de health check do provider."""
    healthy: bool
    latency_ms: Optional[int] = None
    detail: Optional[str] = None


class ChannelProvider(ABC):
    """Interface para providers de canal.

    Implementações: EmailProvider, WhatsAppProvider, (+) novos canais.
    Contrato: cada provider implementa 6 métodos + 2 properties.
    """

    @property
    @abstractmethod
    def canal_id(self) -> str:
        """Identificador único do canal (ex: 'email', 'whatsapp')."""
        ...

    @property
    @abstractmethod
    def capabilities(self) -> ChannelCapabilities:
        """Capacidades do canal (HTML, imagens, limite chars, etc)."""
        ...

    @abstractmethod
    def validar_destinatario(self, destinatario: str) -> bool:
        """Valida formato do destinatário (email válido, telefone E.164)."""
        ...

    @abstractmethod
    def validar_peca(self, conteudo: Dict[str, Any]) -> List[str]:
        """Valida se a peça está compatível com o canal.
        Retorna lista de erros (vazia = válido)."""
        ...

    @abstractmethod
    def renderizar(self, conteudo: Dict[str, Any], variaveis: Dict[str, Any]) -> Dict[str, Any]:
        """Renderiza peça com variáveis resolvidas. Retorna conteúdo pronto p/ envio."""
        ...

    @abstractmethod
    def disparar(self, destinatario: str, conteudo_renderizado: Dict[str, Any],
                 metadata: Optional[Dict[str, Any]] = None) -> DispatchResult:
        """Envia a mensagem para o destinatário. Retorna resultado."""
        ...

    @abstractmethod
    def consultar_status(self, provider_message_id: str) -> DeliveryStatus:
        """Consulta status de entrega (se suportado pelo provider)."""
        ...

    @abstractmethod
    def health_check(self) -> HealthCheckResult:
        """Verifica conectividade com o provider externo."""
        ...
