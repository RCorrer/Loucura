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
        columns = ["caracteristica_id", "tipo_dado", "operadores", "valores_dominio", "ativo"]
        
        for row in results:
            # Converte linha (lista) para dicionário
            row_dict = dict(zip(columns, row))
            
            # Converte operadores para lista (caso venha como array)
            ops = row_dict["operadores"]
            if hasattr(ops, "tolist"):
                ops = ops.tolist()
            
            catalogo[row_dict["caracteristica_id"]] = {
                "tipo_dado": row_dict["tipo_dado"],
                "operadores": ops,
                "valores_dominio": row_dict.get("valores_dominio"),
                "ativo": row_dict["ativo"],
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

        # Valida que inclusão não é None/vazia
        if not regras.inclusao:
            erros.append("Regras de inclusão são obrigatórias. Adicione pelo menos uma condição.")
            return erros  # Retorna cedo para evitar validações subsequentes

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

    def _validar_valor(self, value: Any, tipo_dado: str, valores_dominio: Optional[List], op: str = "") -> bool:
        """Valida se o valor é compatível com o tipo de dado e domínio."""
        # Operadores que não usam valor
        if op in ("is_null", "is_not_null"):
            return True  # value deve ser None, mas não é erro se vier algo

        # Operadores de lista: validar cada elemento
        if op in ("in", "not_in"):
            if not isinstance(value, list):
                return False
            return all(self._validar_valor_escalar(v, tipo_dado, valores_dominio) for v in value)

        if op == "between":
            if not isinstance(value, list) or len(value) != 2:
                return False
            return all(self._validar_valor_escalar(v, tipo_dado, valores_dominio) for v in value)

        # Operadores escalares
        return self._validar_valor_escalar(value, tipo_dado, valores_dominio)

    def _validar_valor_escalar(self, value: Any, tipo_dado: str, valores_dominio: Optional[List]) -> bool:
        """Valida um valor escalar contra tipo e domínio."""
        if value is None:
            return False
        if tipo_dado == "numeric":
            return isinstance(value, (int, float))
        elif tipo_dado == "categorical":
            if valores_dominio and value not in valores_dominio:
                return False
            return isinstance(value, str)
        elif tipo_dado == "boolean":
            return isinstance(value, bool)
        elif tipo_dado == "date":
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