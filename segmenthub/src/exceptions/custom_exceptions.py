"""
Exceções customizadas para a aplicação.
"""

class MetadataError(Exception):
    """Erro base para o módulo de metadados."""
    pass


class TemaNotFoundError(MetadataError):
    """Erro quando um tema não é encontrado."""
    pass


class CampoNotFoundError(MetadataError):
    """Erro quando uma característica não é encontrada."""
    pass


class PublicoNotFoundError(MetadataError):
    """Erro quando um público não é encontrado."""
    pass