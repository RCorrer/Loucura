"""Pydantic v2 schemas para Campanha (S3-BACK-02)."""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from enum import Enum
from datetime import datetime


# --- Ciclo de vida ---
class StatusCampanha(str, Enum):
    RASCUNHO = "rascunho"
    EM_APROVACAO = "em_aprovacao"
    APROVADA = "aprovada"
    ATIVA = "ativa"
    PAUSADA = "pausada"
    ENCERRADA = "encerrada"
    CONCLUIDA = "concluida"


# Transições válidas (estado_atual -> estados_permitidos)
TRANSICOES_VALIDAS = {
    StatusCampanha.RASCUNHO: [StatusCampanha.EM_APROVACAO],
    StatusCampanha.EM_APROVACAO: [StatusCampanha.APROVADA, StatusCampanha.RASCUNHO],
    StatusCampanha.APROVADA: [StatusCampanha.ATIVA],
    StatusCampanha.ATIVA: [StatusCampanha.PAUSADA, StatusCampanha.ENCERRADA, StatusCampanha.CONCLUIDA],
    StatusCampanha.PAUSADA: [StatusCampanha.ATIVA, StatusCampanha.ENCERRADA],
    StatusCampanha.ENCERRADA: [],
    StatusCampanha.CONCLUIDA: [],
}


# --- Request schemas ---
class CampanhaCreate(BaseModel):
    nome: str = Field(..., min_length=3, max_length=200)
    descricao: Optional[str] = None
    objetivo: Optional[str] = None
    objetivo_negocio: Optional[str] = None
    tags: Optional[List[str]] = None
    resumo: Optional[str] = None
    observacoes: Optional[str] = None
    area_responsavel: Optional[str] = None
    email_contato: Optional[str] = None
    vigencia_inicio: Optional[datetime] = None
    vigencia_fim: Optional[datetime] = None

    @field_validator("nome")
    @classmethod
    def nome_strip(cls, v):
        return v.strip() if v else v


class CampanhaUpdate(BaseModel):
    nome: Optional[str] = None
    descricao: Optional[str] = None
    objetivo: Optional[str] = None
    objetivo_negocio: Optional[str] = None
    tags: Optional[List[str]] = None
    resumo: Optional[str] = None
    observacoes: Optional[str] = None
    area_responsavel: Optional[str] = None
    email_contato: Optional[str] = None
    vigencia_inicio: Optional[datetime] = None
    vigencia_fim: Optional[datetime] = None
    motivo: Optional[str] = Field(None, description="Nota da alteração (versionamento)")

    @field_validator("nome")
    @classmethod
    def nome_strip(cls, v):
        return v.strip() if v else v


class LimiteUpdate(BaseModel):
    limite_envios: Optional[int] = Field(None, ge=0, description="NULL = ilimitado")
    alerta_pct_limite: Optional[int] = Field(None, ge=0, le=100)


# --- Response schemas ---
class CampanhaResponse(BaseModel):
    campanha_id: str
    campanha_codigo: str
    nome: str
    descricao: Optional[str] = None
    objetivo: Optional[str] = None
    status: str
    owner: Optional[str] = None
    area_responsavel: Optional[str] = None
    vigencia_inicio: Optional[datetime] = None
    vigencia_fim: Optional[datetime] = None
    limite_envios: Optional[int] = None
    alerta_pct_limite: Optional[int] = None
    envios_realizados: Optional[int] = 0
    versao_atual: int = 1
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None


class CampanhaDetalhe(CampanhaResponse):
    objetivo_negocio: Optional[str] = None
    tags: Optional[List[str]] = None
    resumo: Optional[str] = None
    observacoes: Optional[str] = None
    email_contato: Optional[str] = None
    aprovado_por: Optional[str] = None
    aprovado_em: Optional[datetime] = None
    criado_por: Optional[str] = None
    jornadas: Optional[List[dict]] = None
