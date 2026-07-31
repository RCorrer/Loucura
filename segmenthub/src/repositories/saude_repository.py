"""
Repository para saúde e overlap.
"""

from typing import List, Dict, Optional
from src.db.databricks_client import get_client


class SaudeRepository:
    """Acesso a dados para saúde e overlap."""

    def __init__(self):
        self.client = get_client()

    def listar_saude(self) -> List[Dict]:
        """Retorna saúde de todas as segmentações."""
        sql = """
            SELECT seg_id, health_status, ultima_verificacao,
                   variacao_publico_pct, taxa_sucesso_exec,
                   tempo_medio_exec_seg, alertas_json, publico_atual
            FROM plataforma.segmentacao.seg_saude
            ORDER BY ultima_verificacao DESC
        """
        return self.client.execute_query(sql)

    def buscar_saude_por_seg_id(self, seg_id: str) -> Optional[Dict]:
        """Retorna saúde de uma segmentação específica."""
        sql = """
            SELECT seg_id, health_status, ultima_verificacao,
                   variacao_publico_pct, taxa_sucesso_exec,
                   tempo_medio_exec_seg, alertas_json, publico_atual
            FROM plataforma.segmentacao.seg_saude
            WHERE seg_id = ?
        """
        results = self.client.execute_query(sql, (seg_id,))
        return results[0] if results else None

    def listar_overlaps(self, seg_id: str) -> List[Dict]:
        """Retorna sobreposições de um segmento."""
        sql = """
            SELECT seg_id_a, seg_id_b, clientes_em_comum,
                   pct_sobre_a, pct_sobre_b, calculado_em
            FROM plataforma.segmentacao.seg_overlap
            WHERE seg_id_a = ? OR seg_id_b = ?
            ORDER BY clientes_em_comum DESC
        """
        return self.client.execute_query(sql, (seg_id, seg_id))

    def ultima_atualizacao(self) -> Optional[Dict]:
        """Retorna a data da última atualização da tabela de saúde."""
        sql = """
            SELECT MAX(ultima_verificacao) as ultima_atualizacao
            FROM plataforma.segmentacao.seg_saude
        """
        results = self.client.execute_query(sql)
        return results[0] if results else None

    def contar_por_status(self) -> Dict[str, int]:
        """Conta segmentações por status de saúde."""
        sql = """
            SELECT health_status, COUNT(*) as total
            FROM plataforma.segmentacao.seg_saude
            GROUP BY health_status
        """
        results = self.client.execute_query(sql)
        contagem = {"verde": 0, "amarelo": 0, "vermelho": 0, "sem_dados": 0}
        for row in results:
            status = row["health_status"] or "sem_dados"
            if status in contagem:
                contagem[status] = row["total"]
            else:
                contagem["sem_dados"] += row["total"]
        return contagem