"""
Repository para metadados (catalogo_caracteristicas, catalogo_publicos, etc.).
"""

from src.db.databricks_client import get_client


class MetadataRepository:
    """Acesso a dados para metadados."""

    def __init__(self):
        self.client = get_client()

    def _row_to_dict(self, row, columns):
        """Converte uma linha (lista) em dicionário usando nomes de colunas."""
        return dict(zip(columns, row))

    def _rows_to_dicts(self, rows, columns):
        """Converte múltiplas linhas (listas) em lista de dicionários."""
        return [dict(zip(columns, row)) for row in rows]

    def get_temas(self):
        """Retorna a lista de temas distintos do catálogo."""
        sql = """
            SELECT DISTINCT tema, tema_ordem
            FROM plataforma.metadata.catalogo_caracteristicas
            WHERE ativo = true
            ORDER BY tema_ordem, tema
        """
        rows = self.client.execute_query(sql)
        columns = ["tema", "tema_ordem"]
        return self._rows_to_dicts(rows, columns)

    def get_campos_por_tema(self, tema: str):
        """Retorna características de um tema específico."""
        sql = """
            SELECT 
                caracteristica_id,
                campo_label,
                tipo_dado,
                operadores,
                sensibilidade
            FROM plataforma.metadata.catalogo_caracteristicas
            WHERE tema = ? AND ativo = true
            ORDER BY campo_label
        """
        rows = self.client.execute_query(sql, (tema,))
        columns = ["caracteristica_id", "campo_label", "tipo_dado", "operadores", "sensibilidade"]
        # Converte operadores de array para lista Python se necessário
        results = []
        for row in rows:
            row_list = list(row)
            # operadores está na posição 3 (índice 3)
            if len(row_list) > 3 and hasattr(row_list[3], "tolist"):
                row_list[3] = row_list[3].tolist()
            results.append(dict(zip(columns, row_list)))
        return results

    def get_campo_por_id(self, caracteristica_id: str):
        """Retorna detalhes de uma característica específica."""
        sql = """
            SELECT 
                caracteristica_id,
                campo_label,
                tipo_dado,
                operadores,
                valores_dominio,
                descricao,
                tabela_fisica,
                sensibilidade
            FROM plataforma.metadata.catalogo_caracteristicas
            WHERE caracteristica_id = ? AND ativo = true
        """
        rows = self.client.execute_query(sql, (caracteristica_id,))
        if rows:
            columns = [
                "caracteristica_id", "campo_label", "tipo_dado", "operadores",
                "valores_dominio", "descricao", "tabela_fisica", "sensibilidade"
            ]
            row = list(rows[0])
            # operadores está na posição 3
            if len(row) > 3 and hasattr(row[3], "tolist"):
                row[3] = row[3].tolist()
            # valores_dominio está na posição 4
            if len(row) > 4 and hasattr(row[4], "tolist"):
                row[4] = row[4].tolist()
            return dict(zip(columns, row))
        return None

    def get_publicos(self):
        """Retorna a lista de públicos-base."""
        sql = """
            SELECT publico_id, nome, descricao
            FROM plataforma.metadata.catalogo_publicos
            WHERE ativo = true
            ORDER BY nome
        """
        rows = self.client.execute_query(sql)
        columns = ["publico_id", "nome", "descricao"]
        return self._rows_to_dicts(rows, columns)

    def get_campos_em_uso(self):
        """Retorna campos em uso em segmentações ativas (via view)."""
        sql = """
            SELECT campo_id, qtd_segmentacoes_ativas, segmentacoes
            FROM plataforma.metadata.campos_em_uso
            ORDER BY qtd_segmentacoes_ativas DESC
        """
        rows = self.client.execute_query(sql)
        columns = ["campo_id", "qtd_segmentacoes_ativas", "segmentacoes"]
        # segmentacoes pode vir como array, converter para lista se necessário
        results = []
        for row in rows:
            row_list = list(row)
            # segmentacoes está na posição 2
            if len(row_list) > 2 and hasattr(row_list[2], "tolist"):
                row_list[2] = row_list[2].tolist()
            results.append(dict(zip(columns, row_list)))
        return results