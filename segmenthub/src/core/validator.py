"""
Validador de regras JSON contra o catálogo de características.
Verifica se campos, operadores e valores são válidos.
"""

from typing import List, Dict, Any, Optional
from src.models.regras import RegrasJson, RegraNo, RegraFolha
from src.db.databricks_client import get_client


class RegraValidator:
    """Valida regras JSON contra metadados do catálogo."""

    def __init__(self):
        self.client = get_client()
        self._cache_campos = None

    def _carregar_catalogo(self) -> Dict[str, Dict]:
        """Carrega o catálogo de características e indexa por caracteristica_id."""
        if self._cache_campos is not None:
            return self._cache_campos

        sql = """
            SELECT 
                caracteristica_id,
                tipo_dado,
                operadores,
                valores_dominio,
                ativo
            FROM plataforma.metadata.catalogo_caracteristicas
            WHERE ativo = true
        """
        results = self.client.execute_query(sql)
        catalogo = {}
        for row in results:
            # Converte operadores para lista (caso venha como array)
            ops = row["operadores"]
            if hasattr(ops, "tolist"):
                ops = ops.tolist()
            catalogo[row["caracteristica_id"]] = {
                "tipo_dado": row["tipo_dado"],
                "operadores": ops,
                "valores_dominio": row.get("valores_dominio"),
                "ativo": row["ativo"],
            }
        self._cache_campos = catalogo
        return catalogo

    def validar_regras(self, regras: RegrasJson) -> List[str]:
        """
        Valida a estrutura completa da regra.
        Retorna lista de erros (vazia se tudo OK).
        """
        erros = []
        catalogo = self._carregar_catalogo()

        # Valida público_base (se existe no catalogo_publicos)
        if not self._validar_publico(regras.publico_base):
            erros.append(f"Público base '{regras.publico_base}' não encontrado ou inativo.")

        # Valida nó de inclusão
        erros.extend(self._validar_no(regras.inclusao, catalogo, prefixo="inclusao"))

        # Valida nó de exclusão (se existir)
        if regras.exclusao:
            erros.extend(self._validar_no(regras.exclusao, catalogo, prefixo="exclusao"))

        return erros

    def _validar_no(self, no: RegraNo, catalogo: Dict, prefixo: str = "") -> List[str]:
        """Valida um nó recursivamente."""
        erros = []
        for idx, regra in enumerate(no.rules):  # <-- USANDO 'rules'
            if isinstance(regra, RegraFolha):
                erros.extend(self._validar_folha(regra, catalogo, prefixo=f"{prefixo}.rules[{idx}]"))
            elif isinstance(regra, RegraNo):
                erros.extend(self._validar_no(regra, catalogo, prefixo=f"{prefixo}.rules[{idx}]"))
            else:
                erros.append(f"{prefixo}.rules[{idx}]: tipo de regra inválido")
        return erros

    def _validar_folha(self, folha: RegraFolha, catalogo: Dict, prefixo: str = "") -> List[str]:
        """Valida uma folha (campo + operador + valor)."""
        erros = []
        campo = catalogo.get(folha.campo_id)
        if not campo:
            erros.append(f"{prefixo}.campo_id: campo '{folha.campo_id}' não encontrado no catálogo.")
            return erros

        # Valida operador
        if folha.op not in campo["operadores"]:
            erros.append(
                f"{prefixo}.op: operador '{folha.op}' não permitido para campo '{folha.campo_id}'. "
                f"Permitidos: {campo['operadores']}"
            )

        # Valida tipo do valor
        if not self._validar_valor(folha.value, campo["tipo_dado"], campo["valores_dominio"]):
            erros.append(
                f"{prefixo}.value: valor '{folha.value}' inválido para campo '{folha.campo_id}' "
                f"(esperado tipo {campo['tipo_dado']})"
            )

        return erros

    def _validar_valor(self, value: Any, tipo_dado: str, valores_dominio: Optional[List]) -> bool:
        """Valida se o valor é compatível com o tipo de dado e domínio."""
        if tipo_dado == "numeric":
            return isinstance(value, (int, float))
        elif tipo_dado == "categorical":
            if valores_dominio and value not in valores_dominio:
                return False
            return isinstance(value, str)
        elif tipo_dado == "boolean":
            return isinstance(value, bool)
        elif tipo_dado == "date":
            # Simplificado: aceita string ISO ou datetime
            return isinstance(value, str)
        else:
            return True

    def _validar_publico(self, publico_id: str) -> bool:
        """Verifica se o público existe e está ativo."""
        sql = """
            SELECT 1 FROM plataforma.metadata.catalogo_publicos
            WHERE publico_id = ? AND ativo = true
        """
        result = self.client.execute_query(sql, (publico_id,))
        return len(result) > 0