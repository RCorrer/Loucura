"""
Service para metadados.
Contém a lógica de negócio relacionada ao catálogo de características.
"""

from src.repositories.metadata_repository import MetadataRepository
from src.exceptions.custom_exceptions import TemaNotFoundError, CampoNotFoundError


class MetadataService:
    """Serviço para operações de metadados."""

    def __init__(self):
        self.repository = MetadataRepository()

    def listar_temas(self):
        """Retorna lista de temas formatada."""
        results = self.repository.get_temas()
        return [{"tema": row["tema"], "tema_ordem": row["tema_ordem"]} for row in results]

    def listar_campos_por_tema(self, tema: str):
        """Retorna características de um tema, validando se o tema existe."""
        caracteristicas = self.repository.get_campos_por_tema(tema)
        if not caracteristicas:
            # Verifica se o tema existe (pode ser um tema sem características ativas)
            temas = self.repository.get_temas()
            temas_existentes = [t["tema"] for t in temas]
            if tema not in temas_existentes:
                raise TemaNotFoundError(f"Tema '{tema}' não encontrado")
            # Se existe mas não tem características, retorna lista vazia
        return [
            {
                "caracteristica_id": row["caracteristica_id"],
                "campo_label": row["campo_label"],
                "tipo_dado": row["tipo_dado"],
                "operadores": row["operadores"],
                "sensibilidade": row["sensibilidade"],
            }
            for row in caracteristicas
        ]

    def obter_campo(self, caracteristica_id: str):
        campo = self.repository.get_campo_por_id(caracteristica_id)
        if not campo:
            raise CampoNotFoundError(f"Característica '{caracteristica_id}' não encontrada")

        # Converte operadores para lista
        operadores = campo.get("operadores")
        if hasattr(operadores, "tolist"):
            operadores = operadores.tolist()
        elif isinstance(operadores, str):
            import json
            operadores = json.loads(operadores)

        # Converte valores_dominio para lista ou None
        valores_dominio = campo.get("valores_dominio")
        if hasattr(valores_dominio, "tolist"):
            valores_dominio = valores_dominio.tolist()
        elif isinstance(valores_dominio, str):
            import json
            valores_dominio = json.loads(valores_dominio) if valores_dominio else None

        return {
            "caracteristica_id": campo["caracteristica_id"],
            "campo_label": campo["campo_label"],
            "tipo_dado": campo["tipo_dado"],
            "operadores": operadores,
            "sensibilidade": campo["sensibilidade"],  # <-- DEVE ESTAR AQUI
            "valores_dominio": valores_dominio,
            "descricao": campo.get("descricao"),
            "tabela_fisica": campo.get("tabela_fisica"),
        }

    def listar_publicos(self):
        """Retorna lista de públicos-base."""
        results = self.repository.get_publicos()
        return [
            {"publico_id": row["publico_id"], "nome": row["nome"], "descricao": row["descricao"]}
            for row in results
        ]

    def listar_campos_em_uso(self):
        """Retorna campos em uso em segmentações ativas."""
        results = self.repository.get_campos_em_uso()
        return [
            {
                "campo_id": row["campo_id"],
                "qtd_segmentacoes_ativas": row["qtd_segmentacoes_ativas"],
                "segmentacoes": row["segmentacoes"],
            }
            for row in results
        ]