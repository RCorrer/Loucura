"""Pydantic v2 schemas para Jornadas (S3-BACK-05-A)."""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from enum import Enum
from datetime import datetime


# --- Ciclo de vida ---
class StatusJornada(str, Enum):
    RASCUNHO = "rascunho"
    APROVADA = "aprovada"
    ATIVA = "ativa"
    PAUSADA = "pausada"
    ENCERRADA = "encerrada"


TRANSICOES_JORNADA = {
    StatusJornada.RASCUNHO: [StatusJornada.APROVADA],
    StatusJornada.APROVADA: [StatusJornada.ATIVA],
    StatusJornada.ATIVA: [StatusJornada.PAUSADA, StatusJornada.ENCERRADA],
    StatusJornada.PAUSADA: [StatusJornada.ATIVA, StatusJornada.ENCERRADA],
    StatusJornada.ENCERRADA: [],
}


# --- Tipos de nó do grafo ---
class TipoNo(str, Enum):
    ENTRADA = "entrada"
    ENVIAR_PECA = "enviar_peca"
    ESPERAR = "esperar"
    CONDICAO = "condicao"
    AB_SPLIT = "ab_split"
    ACAO = "acao"
    SAIDA = "saida"


# --- Request schemas ---
class JornadaCreate(BaseModel):
    campanha_id: str = Field(..., description="Campanha a vincular")
    nome: str = Field(..., min_length=3, max_length=200)
    descricao: Optional[str] = None
    seg_entrada_id: Optional[str] = Field(None, description="Segmento de entrada (S1)")
    grafo_json: Optional[str] = Field(None, description="Grafo React Flow (nodes + edges)")
    resumo: Optional[str] = None
    objetivo_negocio: Optional[str] = None
    observacoes: Optional[str] = None
    ao_sair_segmento: Optional[str] = Field(None, description="continua/remove")
    ao_pausar_campanha: Optional[str] = None
    cap_estourado: Optional[str] = None

    @field_validator("nome")
    @classmethod
    def nome_strip(cls, v):
        return v.strip() if v else v

    @field_validator("grafo_json")
    @classmethod
    def grafo_valid_json(cls, v):
        if v is None:
            return v
        import json
        try:
            parsed = json.loads(v)
            if not isinstance(parsed, dict):
                raise ValueError("grafo_json deve ser um objeto JSON")
        except (json.JSONDecodeError, TypeError):
            raise ValueError("grafo_json deve ser um JSON válido")
        return v


class JornadaUpdate(BaseModel):
    nome: Optional[str] = None
    descricao: Optional[str] = None
    seg_entrada_id: Optional[str] = None
    grafo_json: Optional[str] = None
    resumo: Optional[str] = None
    objetivo_negocio: Optional[str] = None
    observacoes: Optional[str] = None
    ao_sair_segmento: Optional[str] = None
    ao_pausar_campanha: Optional[str] = None
    cap_estourado: Optional[str] = None
    motivo: Optional[str] = Field(None, description="Nota da alteração")

    @field_validator("grafo_json")
    @classmethod
    def grafo_valid_json(cls, v):
        if v is None:
            return v
        import json
        try:
            parsed = json.loads(v)
            if not isinstance(parsed, dict):
                raise ValueError("grafo_json deve ser um objeto JSON")
        except (json.JSONDecodeError, TypeError):
            raise ValueError("grafo_json deve ser um JSON válido")
        return v


# --- Response schemas ---
class JornadaResponse(BaseModel):
    jornada_id: str
    jornada_codigo: str
    campanha_id: Optional[str] = None
    nome: str
    descricao: Optional[str] = None
    seg_entrada_id: Optional[str] = None
    status: str
    versao_atual: int = 1
    criado_por: Optional[str] = None
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None


class JornadaDetalhe(JornadaResponse):
    grafo_json: Optional[str] = None
    resumo: Optional[str] = None
    objetivo_negocio: Optional[str] = None
    observacoes: Optional[str] = None
    ao_sair_segmento: Optional[str] = None
    ao_pausar_campanha: Optional[str] = None
    cap_estourado: Optional[str] = None
    aprovado_por: Optional[str] = None
    aprovado_em: Optional[datetime] = None
    owner: Optional[str] = None
    versoes: Optional[List[dict]] = None
