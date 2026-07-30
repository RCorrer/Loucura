"""
DTOs para o módulo de segmentação.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class SegmentacaoCreateDTO(BaseModel):
    """DTO para criar uma nova segmentação."""
    nome: str
    descricao: Optional[str] = None
    objetivo: str  # AQUISICAO/RENTABILIZACAO/RETENCAO/ENGAJAMENTO/COBRANCA
    seg_tags: Optional[List[str]] = None
    resumo: Optional[str] = None
    objetivo_negocio: Optional[str] = None
    publico_alvo_descricao: Optional[str] = None
    observacoes: Optional[str] = None
    documentacao_md: Optional[str] = None
    owner: str
    area_responsavel: Optional[str] = None
    email_contato: Optional[str] = None
    publico_base_id: str
    regras_json: Dict[str, Any]  # será validado pelo RegrasJson
    tipo: Optional[str] = "direta"  # direta/composta


class SegmentacaoUpdateDTO(BaseModel):
    """DTO para atualizar uma segmentação."""
    nome: Optional[str] = None
    descricao: Optional[str] = None
    objetivo: Optional[str] = None
    seg_tags: Optional[List[str]] = None
    resumo: Optional[str] = None
    objetivo_negocio: Optional[str] = None
    publico_alvo_descricao: Optional[str] = None
    observacoes: Optional[str] = None
    documentacao_md: Optional[str] = None
    owner: Optional[str] = None
    area_responsavel: Optional[str] = None
    email_contato: Optional[str] = None
    publico_base_id: Optional[str] = None
    regras_json: Optional[Dict[str, Any]] = None
    tipo: Optional[str] = None


class SegmentacaoResponseDTO(BaseModel):
    """DTO para resposta de segmentação (lista/detalhe)."""
    seg_id: str
    seg_codigo: str
    seg_slug: str
    nome: str
    descricao: Optional[str] = None
    objetivo: str
    seg_tags: Optional[List[str]] = None
    resumo: Optional[str] = None
    objetivo_negocio: Optional[str] = None
    publico_alvo_descricao: Optional[str] = None
    status: str
    versao_atual: int
    criado_por: str
    criado_em: datetime
    atualizado_em: datetime
    owner: str
    area_responsavel: Optional[str] = None
    publico_base_id: str
    tipo: str


class SegmentacaoDetalheDTO(SegmentacaoResponseDTO):
    """DTO para detalhe completo de uma segmentação."""
    regras_json: Optional[Dict[str, Any]] = None
    observacoes: Optional[str] = None
    documentacao_md: Optional[str] = None
    email_contato: Optional[str] = None
    vigencia_inicio: Optional[datetime] = None
    vigencia_fim: Optional[datetime] = None
    agendamento_cron: Optional[str] = None
    recorrencia: Optional[str] = None
    aprovado_por: Optional[str] = None
    aprovado_em: Optional[datetime] = None
    checklist_validacao_json: Optional[Dict[str, Any]] = None
    habilitado: bool = True


class TransicaoStatusDTO(BaseModel):
    """DTO para transição de status."""
    motivo: Optional[str] = None
    checklist_json: Optional[Dict[str, Any]] = None  # usado na aprovação


class CloneSegmentacaoDTO(BaseModel):
    """DTO para clonar uma segmentação."""
    nome: Optional[str] = None
    descricao: Optional[str] = None
    owner: Optional[str] = None
    area_responsavel: Optional[str] = None