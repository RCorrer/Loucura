"""
Schemas para regras JSON (árvore de condições).
Compatível com Pydantic v2.
"""

from typing import List, Optional, Union
from pydantic import BaseModel, Field
from typing import Literal


class RegraFolha(BaseModel):
    """Regra folha: campo_id + operador + valor."""
    campo_id: str
    op: str
    value: Optional[Union[str, int, float, bool, List]] = None


class RegraNo(BaseModel):
    """Regra nó: operador AND/OR + lista de regras filhas."""
    operator: Literal["AND", "OR"]
    rules: List[Union['RegraFolha', 'RegraNo']]


# Resolve forward references automaticamente no Pydantic v2
RegraNo.model_rebuild()


class RegrasJson(BaseModel):
    """Estrutura completa da regra JSON."""
    publico_base: str
    inclusao: Optional[RegraNo] = None
    exclusao: Optional[RegraNo] = None