"""
DTOs para o módulo de metadados (características).
"""

from pydantic import BaseModel
from typing import List, Optional


class CaracteristicaDTO(BaseModel):
    """DTO para representar uma característica/campo."""
    caracteristica_id: str
    campo_label: str
    tipo_dado: str
    operadores: List[str]
    sensibilidade: str


class CaracteristicaDetalheDTO(CaracteristicaDTO):
    """DTO para detalhes de uma característica."""
    valores_dominio: Optional[List[str]] = None
    descricao: Optional[str] = None
    tabela_fisica: Optional[str] = None


class PublicoDTO(BaseModel):
    """DTO para representar um público-base."""
    publico_id: str
    nome: str
    descricao: Optional[str] = None


class CaracteristicaEmUsoDTO(BaseModel):
    """DTO para característica em uso (vem da view)."""
    campo_id: str  # A view já tem esse nome
    qtd_segmentacoes_ativas: int
    segmentacoes: List[str]