"""
Repository para metadados (catalogo_caracteristicas, catalogo_publicos, etc.).
"""

from src.db.databricks_client import get_client


class MetadataRepository:
    """Acesso a dados para metadados."""

    def __init__(self):
        self.client = get_client()

    def get_temas(self):
        """Retorna a lista de temas distintos do catálogo."""
        sql = """
            SELECT DISTINCT tema, tema_ordem
            FROM plataforma.metadata.catalogo_caracteristicas
            WHERE ativo = true
            ORDER BY tema_ordem, tema
        """
        return self.client.execute_query(sql)

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
        return self.client.execute_query(sql, (tema,))

    def get_campo_por_id(self, caracteristica_id: str):
        sql = """
            SELECT 
                caracteristica_id,
                campo_label,
                tipo_dado,
                operadores,
                valores_dominio,
                descricao,
                tabela_fisica,
                sensibilidade   -- <-- DEVE ESTAR AQUI
            FROM plataforma.metadata.catalogo_caracteristicas
            WHERE caracteristica_id = ? AND ativo = true
        """
        result = self.client.execute_query(sql, (caracteristica_id,))
        return result[0] if result else None

    def get_publicos(self):
        """Retorna a lista de públicos-base."""
        sql = """
            SELECT publico_id, nome, descricao
            FROM plataforma.metadata.catalogo_publicos
            WHERE ativo = true
            ORDER BY nome
        """
        return self.client.execute_query(sql)

    def get_campos_em_uso(self):
        """Retorna campos em uso em segmentações ativas (via view)."""
        sql = """
            SELECT campo_id, qtd_segmentacoes_ativas, segmentacoes
            FROM plataforma.metadata.campos_em_uso
            ORDER BY qtd_segmentacoes_ativas DESC
        """
        return self.client.execute_query(sql)