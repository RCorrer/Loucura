"""
Query Engine: converte regras JSON em SQL parametrizado.

Resolve campo_id (caracteristica_id) → tabela_fisica.campo_fisico via catálogo,
e monta JOINs dinâmicos — mesma lógica do seg_exec mas com params parametrizados (?).
"""

from typing import List, Any, Tuple, Dict, Set
from src.models.regras import RegrasJson, RegraNo, RegraFolha
from src.db.databricks_client import get_client


class QueryEngine:
    """Constrói query SQL a partir de regras JSON, resolvendo campos via catálogo."""

    def __init__(self):
        self._param_counter = 0
        self._cache_catalogo: Dict[str, Dict] = {}
        self._cache_publicos: Dict[str, Dict] = {}
        self._tabelas_usadas: Set[tuple] = set()  # {(tabela_fisica, join_key)}

    def _carregar_catalogo(self) -> None:
        """Carrega catálogo de características indexado por caracteristica_id."""
        if self._cache_catalogo:
            return
        client = get_client()
        sql = """
            SELECT caracteristica_id, campo_fisico, tabela_fisica, join_key, tipo_dado
            FROM plataforma.metadata.catalogo_caracteristicas
            WHERE ativo = true
        """
        rows = client.execute_query(sql)
        columns = ["caracteristica_id", "campo_fisico", "tabela_fisica", "join_key", "tipo_dado"]
        for row in rows:
            d = dict(zip(columns, row))
            self._cache_catalogo[d["caracteristica_id"]] = d

    def _carregar_publicos(self) -> None:
        """Carrega catálogo de públicos indexado por publico_id."""
        if self._cache_publicos:
            return
        client = get_client()
        sql = """
            SELECT publico_id, tabela_fisica, join_key
            FROM plataforma.metadata.catalogo_publicos
            WHERE ativo = true
        """
        rows = client.execute_query(sql)
        columns = ["publico_id", "tabela_fisica", "join_key"]
        for row in rows:
            d = dict(zip(columns, row))
            self._cache_publicos[d["publico_id"]] = d

    def _resolver_campo(self, campo_id: str) -> str:
        """Resolve caracteristica_id → tabela_fisica.campo_fisico.
        Também registra a tabela para JOINs dinâmicos."""
        info = self._cache_catalogo.get(campo_id)
        if not info:
            raise ValueError(f"Campo '{campo_id}' não encontrado no catálogo")
        self._tabelas_usadas.add((info["tabela_fisica"], info["join_key"]))
        return f"{info['tabela_fisica']}.{info['campo_fisico']}"

    def _is_string_field(self, campo_id: str) -> bool:
        """Verifica se um campo é do tipo string para aplicar LOWER() nas comparações."""
        info = self._cache_catalogo.get(campo_id)
        if not info:
            return False
        return info.get("tipo_dado") == "string"

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
        campo = self._resolver_campo(folha.campo_id)
        op = folha.op
        valor = folha.value
        is_string = self._is_string_field(folha.campo_id)

        if op == "=":
            if is_string:
                sql = f"LOWER({campo}) = LOWER({self._get_param()})"
            else:
                sql = f"{campo} = {self._get_param()}"
            params.append(valor)
        elif op == "!=":
            if is_string:
                sql = f"LOWER({campo}) != LOWER({self._get_param()})"
            else:
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
            if is_string:
                # Para strings, aplicar LOWER() tanto no campo quanto nos valores
                lower_placeholders = ", ".join([f"LOWER({self._get_param()})" for _ in valor])
                sql = f"LOWER({campo}) IN ({lower_placeholders})"
            else:
                sql = f"{campo} IN ({placeholders})"
            params.extend(valor)
        elif op == "not_in":
            if not isinstance(valor, list):
                raise ValueError(f"Operador 'not_in' requer lista de valores: {valor}")
            placeholders = ", ".join([self._get_param() for _ in valor])
            if is_string:
                # Para strings, aplicar LOWER() tanto no campo quanto nos valores
                lower_placeholders = ", ".join([f"LOWER({self._get_param()})" for _ in valor])
                sql = f"LOWER({campo}) NOT IN ({lower_placeholders})"
            else:
                sql = f"{campo} NOT IN ({placeholders})"
            params.extend(valor)
        elif op == "contains":
            sql = f"LOWER({campo}) LIKE LOWER({self._get_param()})"
            params.append(f"%{valor}%")
        elif op == "starts_with":
            sql = f"LOWER({campo}) LIKE LOWER({self._get_param()})"
            params.append(f"{valor}%")
        elif op == "ends_with":
            sql = f"LOWER({campo}) LIKE LOWER({self._get_param()})"
            params.append(f"%{valor}")
        elif op == "not_contains":
            sql = f"LOWER({campo}) NOT LIKE LOWER({self._get_param()})"
            params.append(f"%{valor}%")
        elif op == "not_starts_with":
            sql = f"LOWER({campo}) NOT LIKE LOWER({self._get_param()})"
            params.append(f"{valor}%")
        elif op == "not_ends_with":
            sql = f"LOWER({campo}) NOT LIKE LOWER({self._get_param()})"
            params.append(f"%{valor}")
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

    def _build_full_query(self, regras: RegrasJson, select_expr: str) -> Tuple[str, List[Any]]:
        """Gera query completa com resolução de campos via catálogo e JOINs dinâmicos."""
        # Reset estado
        params: List[Any] = []
        self._param_counter = 0
        self._tabelas_usadas = set()

        # Carrega metadados
        self._carregar_catalogo()
        self._carregar_publicos()

        # Resolve público base
        publico_info = self._cache_publicos.get(regras.publico_base)
        if not publico_info:
            raise ValueError(f"Público base '{regras.publico_base}' não encontrado")
        tabela_base = publico_info["tabela_fisica"]
        join_key_base = publico_info["join_key"]

        # Monta WHERE (resolvendo campos → registra tabelas usadas)
        inclusao_sql = self._build_condition(regras.inclusao, params)
        inclusao_sql = f"({inclusao_sql})" if inclusao_sql else "1=1"

        exclusao_clause = ""
        if regras.exclusao:
            exclusao_sql = self._build_condition(regras.exclusao, params)
            if exclusao_sql:
                exclusao_clause = f"\n            AND NOT ({exclusao_sql})"

        # Monta JOINs dinâmicos (mesma lógica do seg_exec)
        joins_sql = ""
        for tabela, join_key in self._tabelas_usadas:
            if tabela != tabela_base:
                joins_sql += (
                    f"\n            LEFT JOIN {tabela}"
                    f" ON {tabela}.{join_key} = {tabela_base}.{join_key_base}"
                )

        # Resolve SELECT expression (substitui placeholders)
        select_final = select_expr.replace(
            "{tabela_base}", tabela_base
        ).replace(
            "{join_key}", join_key_base
        )

        sql = f"""
            SELECT {select_final}
            FROM {tabela_base}{joins_sql}
            WHERE {inclusao_sql}{exclusao_clause}
        """

        return sql, params

    def generate_query(self, regras: RegrasJson) -> Tuple[str, List[Any]]:
        """Gera query de seleção de CPFs (DISTINCT)."""
        return self._build_full_query(
            regras, "DISTINCT {tabela_base}.{join_key} AS cpf_cnpj"
        )

    def generate_estimativa_query(self, regras: RegrasJson) -> Tuple[str, List[Any]]:
        """Gera query de estimativa (approx_count_distinct)."""
        return self._build_full_query(
            regras, "approx_count_distinct({tabela_base}.{join_key}) AS estimativa"
        )