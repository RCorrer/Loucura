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
        rows = self.client.execute_query(sql)
        columns = [
            "seg_id", "health_status", "ultima_verificacao",
            "variacao_publico_pct", "taxa_sucesso_exec",
            "tempo_medio_exec_seg", "alertas_json", "publico_atual"
        ]
        # Converte cada lista em dicionário
        results = []
        for row in rows:
            row_list = list(row)
            # alertas_json pode ser um dict ou string; mantém como está
            # Se for string, podemos tentar parsear, mas não é obrigatório
            results.append(dict(zip(columns, row_list)))
        return results

    def buscar_saude_por_seg_id(self, seg_id: str) -> Optional[Dict]:
        """Retorna saúde de uma segmentação específica."""
        sql = """
            SELECT seg_id, health_status, ultima_verificacao,
                   variacao_publico_pct, taxa_sucesso_exec,
                   tempo_medio_exec_seg, alertas_json, publico_atual
            FROM plataforma.segmentacao.seg_saude
            WHERE seg_id = ?
        """
        rows = self.client.execute_query(sql, (seg_id,))
        if rows:
            columns = [
                "seg_id", "health_status", "ultima_verificacao",
                "variacao_publico_pct", "taxa_sucesso_exec",
                "tempo_medio_exec_seg", "alertas_json", "publico_atual"
            ]
            return dict(zip(columns, rows[0]))
        return None

    def listar_overlaps(self, seg_id: str) -> List[Dict]:
        """Retorna sobreposições de um segmento."""
        sql = """
            SELECT seg_id_a, seg_id_b, clientes_em_comum,
                   pct_sobre_a, pct_sobre_b, calculado_em
            FROM plataforma.segmentacao.seg_overlap
            WHERE seg_id_a = ? OR seg_id_b = ?
            ORDER BY clientes_em_comum DESC
        """
        rows = self.client.execute_query(sql, (seg_id, seg_id))
        columns = [
            "seg_id_a", "seg_id_b", "clientes_em_comum",
            "pct_sobre_a", "pct_sobre_b", "calculado_em"
        ]
        return [dict(zip(columns, row)) for row in rows]

    def ultima_atualizacao(self) -> Optional[Dict]:
        """Retorna a data da última atualização da tabela de saúde."""
        sql = """
            SELECT MAX(ultima_verificacao) as ultima_atualizacao
            FROM plataforma.segmentacao.seg_saude
        """
        rows = self.client.execute_query(sql)
        if rows:
            return {"ultima_atualizacao": rows[0][0]}
        return None

    def contar_por_status(self) -> Dict[str, int]:
        """Conta segmentações por status de saúde."""
        sql = """
            SELECT health_status, COUNT(*) as total
            FROM plataforma.segmentacao.seg_saude
            GROUP BY health_status
        """
        rows = self.client.execute_query(sql)
        contagem = {"verde": 0, "amarelo": 0, "vermelho": 0, "sem_dados": 0}
        for row in rows:
            status = row[0] or "sem_dados"  # health_status na posição 0
            total = row[1]                  # total na posição 1
            if status in contagem:
                contagem[status] = total
            else:
                contagem["sem_dados"] += total
        return contagem