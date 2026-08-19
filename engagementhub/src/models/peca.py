"""Pydantic v2 schemas para Peças (S3-BACK-03)."""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from enum import Enum
from datetime import datetime


# --- Ciclo de aprovação ---
class StatusAprovacao(str, Enum):
    RASCUNHO = "rascunho"
    EM_APROVACAO = "em_aprovacao"
    APROVADA = "aprovada"
    REPROVADA = "reprovada"


TRANSICOES_APROVACAO = {
    StatusAprovacao.RASCUNHO: [StatusAprovacao.EM_APROVACAO],
    StatusAprovacao.EM_APROVACAO: [StatusAprovacao.APROVADA, StatusAprovacao.REPROVADA],
    StatusAprovacao.APROVADA: [],
    StatusAprovacao.REPROVADA: [StatusAprovacao.RASCUNHO],  # pode reabrir
}


class CanalPeca(str, Enum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"


# --- Request schemas ---
class PecaCreate(BaseModel):
    nome: str = Field(..., min_length=3, max_length=200)
    descricao: Optional[str] = None
    canal: CanalPeca
    tags: Optional[List[str]] = None
    conteudo_json: str = Field(..., description="JSON do editor (GrapesJS/msg)")
    assunto: Optional[str] = Field(None, description="Subject line (email)")
    template_meta_id: Optional[str] = Field(None, description="WhatsApp HSM template ID")
    area_responsavel: Optional[str] = None

    @field_validator("nome")
    @classmethod
    def nome_strip(cls, v):
        return v.strip() if v else v

    @field_validator("conteudo_json")
    @classmethod
    def conteudo_valid_json(cls, v):
        import json
        try:
            json.loads(v)
        except (json.JSONDecodeError, TypeError):
            raise ValueError("conteudo_json deve ser um JSON válido")
        return v


class PecaUpdate(BaseModel):
    nome: Optional[str] = None
    descricao: Optional[str] = None
    tags: Optional[List[str]] = None
    conteudo_json: Optional[str] = None
    assunto: Optional[str] = None
    template_meta_id: Optional[str] = None
    area_responsavel: Optional[str] = None
    motivo: Optional[str] = Field(None, description="Nota da alteração")

    @field_validator("conteudo_json")
    @classmethod
    def conteudo_valid_json(cls, v):
        if v is None:
            return v
        import json
        try:
            json.loads(v)
        except (json.JSONDecodeError, TypeError):
            raise ValueError("conteudo_json deve ser um JSON válido")
        return v


class AprovarPayload(BaseModel):
    etapa: str = Field("conteudo", description="conteudo/compliance/juridico/marca")
    comentario: Optional[str] = None


class ReprovarPayload(BaseModel):
    motivo: str = Field(..., min_length=5, description="Motivo da reprovação (obrigatório)")
    etapa: str = Field("conteudo")


class PreviewPayload(BaseModel):
    variaveis: Optional[dict] = Field(None, description="Override de variáveis para preview")


# --- Response schemas ---
class PecaResponse(BaseModel):
    peca_id: str
    peca_codigo: str
    nome: str
    descricao: Optional[str] = None
    canal: str
    status_aprovacao: str
    owner: Optional[str] = None
    area_responsavel: Optional[str] = None
    versao_atual: int = 1
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None


class PecaDetalhe(PecaResponse):
    tags: Optional[List[str]] = None
    conteudo_json: Optional[str] = None
    html_renderizado: Optional[str] = None
    assunto: Optional[str] = None
    template_meta_id: Optional[str] = None
    variaveis_usadas: Optional[List[str]] = None
    aprovado_por: Optional[str] = None
    aprovado_em: Optional[datetime] = None
    motivo_reprovacao: Optional[str] = None
    criado_por: Optional[str] = None
    versoes: Optional[List[dict]] = None
    aprovacoes: Optional[List[dict]] = None
