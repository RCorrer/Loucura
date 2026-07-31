"""
DTOs para o módulo de saúde e overlap.
"""

from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime


class SaudeDTO(BaseModel):
    """DTO para saúde de uma segmentação."""
    seg_id: str
    health_status: Optional[str]  # verde/amarelo/vermelho
    ultima_verificacao: Optional[datetime]
    variacao_publico_pct: Optional[float]
    taxa_sucesso_exec: Optional[float]
    tempo_medio_exec_seg: Optional[int]
    alertas_json: Optional[Dict]
    publico_atual: Optional[int]


class SaudeDashboardDTO(BaseModel):
    """DTO para dashboard de saúde (consolidado)."""
    total_segmentacoes: int
    verde: int
    amarelo: int
    vermelho: int
    sem_dados: int
    ultima_atualizacao: Optional[datetime]
    detalhes: List[SaudeDTO]


class OverlapDTO(BaseModel):
    """DTO para sobreposição entre segmentos."""
    seg_id_a: str
    seg_id_b: str
    clientes_em_comum: int
    pct_sobre_a: Optional[float]
    pct_sobre_b: Optional[float]
    calculado_em: Optional[datetime]


class OverlapListaDTO(BaseModel):
    """DTO para lista de sobreposições de um segmento."""
    seg_id: str
    overlaps: List[OverlapDTO]