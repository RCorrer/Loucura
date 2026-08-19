"""Provider Registry (S3-BACK-04).

Factory que resolve provider_class (string do catalogo_canais) → instância.
Singleton por canal — providers são stateless, 1 instância basta.
"""

import logging
from typing import Dict, Optional

from src.providers.base import ChannelProvider
from src.providers.email_provider import EmailProvider
from src.providers.whatsapp_provider import WhatsAppProvider

logger = logging.getLogger(__name__)

# Mapa de provider_class (do DDL catalogo_canais.provider_class) → classe
_PROVIDER_MAP: Dict[str, type] = {
    "EmailProvider": EmailProvider,
    "WhatsAppProvider": WhatsAppProvider,
}

# Cache de instâncias (singleton per canal)
_instances: Dict[str, ChannelProvider] = {}


def get_provider(provider_class: str) -> ChannelProvider:
    """Resolve provider_class string para instância.

    Args:
        provider_class: Nome da classe (ex: 'EmailProvider')

    Returns:
        Instância do provider.

    Raises:
        ValueError: Se provider_class não registrado.
    """
    if provider_class in _instances:
        return _instances[provider_class]

    cls = _PROVIDER_MAP.get(provider_class)
    if cls is None:
        available = list(_PROVIDER_MAP.keys())
        raise ValueError(
            f"Provider '{provider_class}' não registrado. "
            f"Disponíveis: {available}"
        )

    instance = cls()
    _instances[provider_class] = instance
    logger.info(f"Provider instanciado: {provider_class}")
    return instance


def get_provider_by_canal(canal: str) -> Optional[ChannelProvider]:
    """Resolve canal ('email', 'whatsapp') para provider.

    Atalho para uso quando não se tem o provider_class do catálogo.
    """
    canal_map = {
        "email": "EmailProvider",
        "whatsapp": "WhatsAppProvider",
    }
    provider_class = canal_map.get(canal)
    if not provider_class:
        return None
    return get_provider(provider_class)


def list_providers() -> Dict[str, str]:
    """Lista providers registrados (para admin/debug)."""
    return {name: cls.__module__ + "." + cls.__name__ for name, cls in _PROVIDER_MAP.items()}


def register_provider(provider_class_name: str, cls: type) -> None:
    """Registra novo provider dinamicamente (para extensões/plugins)."""
    if not issubclass(cls, ChannelProvider):
        raise TypeError(f"{cls} deve herdar de ChannelProvider")
    _PROVIDER_MAP[provider_class_name] = cls
    # Invalida cache se existia
    _instances.pop(provider_class_name, None)
    logger.info(f"Provider registrado: {provider_class_name} -> {cls.__name__}")
