"""
Query Engine: converte regras JSON em SQL parametrizado.
"""

from typing import List, Any, Tuple
from src.models.regras import RegrasJson, RegraNo, RegraFolha


class QueryEngine:
    """Constrói query SQL a partir de regras JSON."""

    def __init__(self):
        self._param_counter = 0

    def _get_param(self) -> str:
        self._param_counter += 1
        return "?"

    def _build_condition(self, regra, params: List[Any]) -> str:
        if isinstance(regra, RegraFolha):
            return self._build_folha(regra, params)
        elif isinstance(regra, RegraNo):
            return self._build_no(regra, params)
        else:
            raise ValueError(f"Tipo de regra inválido: {type(regra)}")

    def _build_folha(self, folha: RegraFolha, params: List[Any]) -> str:
        campo = folha.campo_id
        op = folha.op
        valor = folha.value

        if op == "=":
            sql = f"{campo} = {self._get_param()}"
            params.append(valor)
        elif op == "!=":
            sql = f"{campo} != {self._get_param()}"
            params.append(valor)
        elif op == ">":
            sql = f"{campo} > {self._get_param()}"
            params.append(valor)
        elif op == "<":
            sql = f"{campo} < {self._get_param()}"
            params.append(valor)
        elif op == ">=":
            sql = f"{campo} >= {self._get_param()}"
            params.append(valor)
        elif op == "<=":
            sql = f"{campo} <= {self._get_param()}"
            params.append(valor)
        elif op == "between":
            if not isinstance(valor, list) or len(valor) != 2:
                raise ValueError(f"Operador 'between' requer lista com 2 valores: {valor}")
            sql = f"{campo} BETWEEN {self._get_param()} AND {self._get_param()}"
            params.extend(valor)
        elif op == "in":
            if not isinstance(valor, list):
                raise ValueError(f"Operador 'in' requer lista de valores: {valor}")
            placeholders = ", ".join([self._get_param() for _ in valor])
            sql = f"{campo} IN ({placeholders})"
            params.extend(valor)
        elif op == "not_in":
            if not isinstance(valor, list):
                raise ValueError(f"Operador 'not_in' requer lista de valores: {valor}")
            placeholders = ", ".join([self._get_param() for _ in valor])
            sql = f"{campo} NOT IN ({placeholders})"
            params.extend(valor)
        elif op == "is_null":
            sql = f"{campo} IS NULL"
        elif op == "is_not_null":
            sql = f"{campo} IS NOT NULL"
        else:
            raise ValueError(f"Operador não suportado: {op}")

        return sql

    def _build_no(self, no: RegraNo, params: List[Any]) -> str:
        if not no.rules:
            return "1=1"

        conditions = []
        for rule in no.rules:
            cond = self._build_condition(rule, params)
            conditions.append(f"({cond})")

        separator = " AND " if no.operator == "AND" else " OR "
        return separator.join(conditions)

    def generate_query(self, regras: RegrasJson) -> Tuple[str, List[Any]]:
        params = []
        self._param_counter = 0

        inclusao_sql = self._build_condition(regras.inclusao, params)
        inclusao_sql = f"({inclusao_sql})" if inclusao_sql else "1=1"

        exclusao_sql = "1=1"
        if regras.exclusao:
            exclusao_sql = self._build_condition(regras.exclusao, params)
            exclusao_sql = f"({exclusao_sql})" if exclusao_sql else "1=1"

        sql = f"""
            SELECT cpf_cnpj
            FROM plataforma.publico.{regras.publico_base} p
            JOIN plataforma.caracteristicas.customer_features_wide f
                ON p.cpf_cnpj = f.cpf_cnpj
            WHERE {inclusao_sql}
              AND {exclusao_sql}
        """

        return sql, params

    def generate_estimativa_query(self, regras: RegrasJson) -> Tuple[str, List[Any]]:
        sql, params = self.generate_query(regras)
        estimativa_sql = sql.replace(
            "SELECT cpf_cnpj",
            "SELECT approx_count_distinct(cpf_cnpj) as estimativa"
        )
        return estimativa_sql, params