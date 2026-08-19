"""Modelos de resposta padrão do EngagementHub (S3)."""

from pydantic import BaseModel
from typing import Any, Optional, List


class ApiResponse(BaseModel):
    """Resposta padrão: {data, meta}"""
    data: Any
    meta: Optional[dict] = None


class PaginatedResponse(BaseModel):
    """Resposta paginada."""
    data: List[Any]
    meta: dict  # {total, page, size, pages}


class ErrorResponse(BaseModel):
    """Resposta de erro."""
    detail: str
    code: Optional[str] = None
