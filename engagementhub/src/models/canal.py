"""Pydantic v2 schemas para Canais (S3-BACK-04)."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class CanalCreate(BaseModel):
    canal_id: str = Field(..., min_length=2, max_length=50, description="Identificador único (ex: 'email', 'sms')")
    nome_exibicao: str = Field(..., min_length=2, max_length=100)
    icone: Optional[str] = None
    suporta_html: bool = False
    suporta_imagem: bool = False
    suporta_botoes: bool = False
    suporta_video: bool = False
    max_caracteres: Optional[int] = None
    formato_editor: str = Field("mensagem_simples", description="rico_html/mensagem_simples/card")
    campos_obrigatorios: Optional[List[str]] = None
    provider_class: str = Field(..., description="Classe do provider (EmailProvider/WhatsAppProvider)")
    rate_limit_por_segundo: Optional[int] = None
    rate_limit_por_dia: Optional[int] = None


class CanalUpdate(BaseModel):
    nome_exibicao: Optional[str] = None
    icone: Optional[str] = None
    suporta_html: Optional[bool] = None
    suporta_imagem: Optional[bool] = None
    suporta_botoes: Optional[bool] = None
    suporta_video: Optional[bool] = None
    max_caracteres: Optional[int] = None
    formato_editor: Optional[str] = None
    campos_obrigatorios: Optional[List[str]] = None
    provider_class: Optional[str] = None
    rate_limit_por_segundo: Optional[int] = None
    rate_limit_por_dia: Optional[int] = None
    ativo: Optional[bool] = None


class CanalResponse(BaseModel):
    canal_id: str
    nome_exibicao: str
    icone: Optional[str] = None
    suporta_html: bool = False
    suporta_imagem: bool = False
    suporta_botoes: bool = False
    suporta_video: bool = False
    max_caracteres: Optional[int] = None
    formato_editor: str = "mensagem_simples"
    campos_obrigatorios: Optional[List[str]] = None
    provider_class: Optional[str] = None
    rate_limit_por_segundo: Optional[int] = None
    rate_limit_por_dia: Optional[int] = None
    ativo: bool = True
    atualizado_em: Optional[datetime] = None


class HealthResponse(BaseModel):
    canal_id: str
    healthy: bool
    latency_ms: Optional[int] = None
    detail: Optional[str] = None
