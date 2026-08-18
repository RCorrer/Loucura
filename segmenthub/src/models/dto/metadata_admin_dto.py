"""
DTOs para o módulo admin de governança de catálogo.
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class FlagUpdateDTO(BaseModel):
    """DTO para atualização de flags de uma característica."""
    usavel_em_visao360: Optional[bool] = None
    usavel_em_peca: Optional[bool] = None
    bloco_visao360: Optional[str] = None


class StatusUpdateDTO(BaseModel):
    """DTO para ativar/desativar uma característica globalmente."""
    ativo: bool


class CampoAdminDTO(BaseModel):
    """DTO para listagem de características no admin."""
    caracteristica_id: str
    campo_label: str
    tema: str
    tipo_dado: str
    sensibilidade: str
    ativo: bool = False
    usavel_em_visao360: bool = False  # default False para campos com NULL no banco
    usavel_em_peca: bool = False      # default False para campos com NULL no banco
    bloco_visao360: Optional[str] = None


class CampoAdminDetalheDTO(CampoAdminDTO):
    """DTO para detalhe completo de uma característica."""
    tabela_fisica: str
    campo_fisico: str
    operadores: List[str]
    valores_dominio: Optional[List[str]]
    descricao: Optional[str]


class HistoricoGovernancaDTO(BaseModel):
    """DTO para registro de histórico de governança."""
    hist_id: str
    caracteristica_id: str
    campo_label: Optional[str]
    flag_alterada: str
    sistema_alvo: Optional[str]
    valor_anterior: Optional[str]
    valor_novo: str
    acao: str  # liberou, retirou, alterou_bloco
    alterado_por: str
    alterado_em: datetime