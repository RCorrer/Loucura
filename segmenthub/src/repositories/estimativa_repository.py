"""
Repository para estimativa de público.
Executa queries de contagem aproximada (HyperLogLog).
"""

from src.db.databricks_client import get_client


class EstimativaRepository:
    """Executa queries de estimativa no SQL Warehouse."""

    def __init__(self):
        self.client = get_client()

    def executar_estimativa(self, sql: str, params: tuple) -> int:
        """
        Executa uma query de estimativa e retorna a contagem aproximada.
        """
        result = self.client.execute_query(sql, params)
        if result and len(result) > 0:
            # result[0] é uma lista com os valores da primeira linha
            # o primeiro valor é a estimativa
            return result[0][0] or 0
        return 0

    def executar_contagem(self, sql: str, params: tuple) -> int:
        """
        Executa uma query de contagem exata (COUNT) para fins de debug.
        """
        result = self.client.execute_query(sql, params)
        if result and len(result) > 0:
            return result[0][0] or 0
        return 0