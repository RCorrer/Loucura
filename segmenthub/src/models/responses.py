"""
Schemas de resposta padronizados para a API do SegmentHub.
"""

from typing import Any, Dict, List, Optional, Generic, TypeVar
from pydantic import BaseModel

T = TypeVar('T')


class RespostaErro(BaseModel):
    """Resposta padrão para erros."""
    erro: str
    detalhe: Optional[str] = None


class MetaPaginacao(BaseModel):
    """Metadados de paginação."""
    page: int
    size: int
    total: int
    total_pages: Optional[int] = None


class RespostaLista(BaseModel, Generic[T]):
    """Resposta padrão para listas paginadas."""
    data: List[T]
    meta: MetaPaginacao


class RespostaSucesso(BaseModel):
    """Resposta padrão para operações bem-sucedidas sem dados específicos."""
    mensagem: str
    dados: Optional[Dict[str, Any]] = None


class RespostaUnica(BaseModel, Generic[T]):
    """Resposta padrão para um único objeto."""
    data: T


def paginate(data: List[T], page: int, size: int, total: int) -> RespostaLista:
    """
    Helper para criar uma resposta paginada.
    """
    total_pages = (total + size - 1) // size if total > 0 else 0
    return RespostaLista(
        data=data,
        meta=MetaPaginacao(
            page=page,
            size=size,
            total=total,
            total_pages=total_pages
        )
    )
