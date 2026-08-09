"""
Databricks SQL Warehouse client for SegmentHub (S1).
Stateless client using WorkspaceClient + statement_execution.
"""

import os
import time
import logging
from typing import Dict, Any, List, Optional, Union

from databricks.sdk import WorkspaceClient

logger = logging.getLogger(__name__)


class DatabricksSQLClient:
    def __init__(self):
        self.client = WorkspaceClient()
        self.warehouse_id = os.getenv("DATABRICKS_WAREHOUSE_ID")
        self.catalog = os.getenv("UC_CATALOG", "plataforma")
        self.schema = os.getenv("UC_SCHEMA", "default")
        self.timeout = int(os.getenv("QUERY_TIMEOUT_SECONDS", "120"))
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        self.backoff = int(os.getenv("RETRY_BACKOFF_SECONDS", "1"))
        self.backoff_factor = float(os.getenv("RETRY_BACKOFF_FACTOR", "2"))

        if not self.warehouse_id:
            raise ValueError("DATABRICKS_WAREHOUSE_ID não definido")

    def _normalize_params(self, params: Optional[Union[Dict, tuple, list]]) -> Optional[List[Dict]]:
        """Converte parâmetros para o formato esperado: [{"name": k, "value": v}, ...]."""
        if not params:
            return None
        if isinstance(params, dict):
            return [{"name": k, "value": v} for k, v in params.items()]
        if isinstance(params, (tuple, list)):
            # Para tuplas/listas, cria nomes genéricos p0, p1, ...
            # E substitui placeholders ? por :p0, :p1 na SQL (feito no execute_query)
            return [{"name": f"p{i}", "value": v} for i, v in enumerate(params)]
        raise ValueError(f"Tipo de parâmetro não suportado: {type(params)}")

    def _replace_placeholders(self, sql: str, params: Optional[Union[Dict, tuple, list]]) -> str:
        """Substitui placeholders ? por :p0, :p1 quando params é tupla/lista."""
        if not params or isinstance(params, dict):
            return sql
        if isinstance(params, (tuple, list)):
            # Substitui cada ? por :pN na ordem
            for i in range(len(params)):
                sql = sql.replace("?", f":p{i}", 1)
            return sql
        return sql

    def execute_query(
        self,
        sql: str,
        params: Optional[Union[Dict, tuple, list]] = None,
        timeout: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        timeout = timeout or self.timeout

        # Normaliza params para o formato do Databricks
        param_list = self._normalize_params(params)
        # Ajusta a SQL se params for tupla/lista
        sql_ajustada = self._replace_placeholders(sql, params)

        for attempt in range(self.max_retries):
            try:
                response = self.client.statement_execution.execute_statement(
                    warehouse_id=self.warehouse_id,
                    statement=sql_ajustada,
                    parameters=param_list if param_list else None,
                    catalog=self.catalog,
                    schema=self.schema,
                    wait_timeout=timeout,
                )
                result = self.client.statement_execution.get_statement(response.statement_id)
                state = str(result.status.state)

                if state == "SUCCEEDED":
                    rows = result.result.data_array if result.result else []
                    if rows and result.result.column_names:
                        columns = result.result.column_names
                        return [dict(zip(columns, row)) for row in rows]
                    return []
                elif state in ["FAILED", "CANCELED", "CLOSED"]:
                    error_msg = getattr(result.status, "error", "Erro desconhecido")
                    raise RuntimeError(f"Query falhou: {error_msg}")
                else:
                    # Polling manual (fallback)
                    return self._poll_query(response.statement_id, timeout)

            except Exception as e:
                if "duration" in str(e) or "parsing" in str(e):
                    logger.warning(f"Erro de parsing, tentando sem formato: {e}")
                    try:
                        return self._execute_without_format(sql_ajustada, param_list, timeout)
                    except Exception as e2:
                        logger.error(f"Falha mesmo sem formato: {e2}")
                        if attempt < self.max_retries - 1:
                            wait = self.backoff * (self.backoff_factor ** attempt)
                            logger.info(f"Re-tentando em {wait}s...")
                            time.sleep(wait)
                            continue
                        raise
                elif attempt < self.max_retries - 1:
                    wait = self.backoff * (self.backoff_factor ** attempt)
                    logger.warning(f"Tentativa {attempt+1} falhou: {e}. Re-tentando em {wait}s...")
                    time.sleep(wait)
                else:
                    raise RuntimeError(f"Falha após {self.max_retries} tentativas: {e}")

        raise RuntimeError("Falha inesperada")

    def _execute_without_format(self, sql: str, param_list: Optional[List], timeout: int) -> List[Dict]:
        """Fallback: executa sem result_format especificado."""
        response = self.client.statement_execution.execute_statement(
            warehouse_id=self.warehouse_id,
            statement=sql,
            parameters=param_list if param_list else None,
            catalog=self.catalog,
            schema=self.schema,
            wait_timeout=timeout,
        )
        result = self.client.statement_execution.get_statement(response.statement_id)
        state = str(result.status.state)
        if state == "SUCCEEDED":
            rows = result.result.data_array if result.result else []
            if rows and result.result.column_names:
                columns = result.result.column_names
                return [dict(zip(columns, row)) for row in rows]
            return []
        else:
            error_msg = getattr(result.status, "error", "Erro desconhecido")
            raise RuntimeError(f"Query falhou: {error_msg}")

    def _poll_query(self, statement_id: str, timeout: int) -> List[Dict]:
        start = time.time()
        while time.time() - start < timeout:
            result = self.client.statement_execution.get_statement(statement_id)
            state = str(result.status.state)
            if state == "SUCCEEDED":
                rows = result.result.data_array if result.result else []
                if rows and result.result.column_names:
                    columns = result.result.column_names
                    return [dict(zip(columns, row)) for row in rows]
                return []
            if state in ["FAILED", "CANCELED", "CLOSED"]:
                error_msg = getattr(result.status, "error", "Erro desconhecido")
                raise RuntimeError(f"Query falhou: {error_msg}")
            time.sleep(2)
        raise TimeoutError(f"Timeout após {timeout}s")

    def fetch_one(self, sql: str, params: Optional[Union[Dict, tuple, list]] = None) -> Optional[Dict]:
        results = self.execute_query(sql, params)
        return results[0] if results else None

    def fetch_value(self, sql: str, params: Optional[Union[Dict, tuple, list]] = None):
        row = self.fetch_one(sql, params)
        return list(row.values())[0] if row else None

    def execute_insert(self, sql: str, params: Optional[Union[Dict, tuple, list]] = None) -> int:
        return self._execute_dml(sql, params)

    def _execute_dml(self, sql: str, params: Optional[Union[Dict, tuple, list]]) -> int:
        param_list = self._normalize_params(params)
        sql_ajustada = self._replace_placeholders(sql, params)
        response = self.client.statement_execution.execute_statement(
            warehouse_id=self.warehouse_id,
            statement=sql_ajustada,
            parameters=param_list if param_list else None,
            catalog=self.catalog,
            schema=self.schema,
            wait_timeout=self.timeout,
        )
        result = self.client.statement_execution.get_statement(response.statement_id)
        return result.status.row_count or 0


_default_client = None

def get_client() -> DatabricksSQLClient:
    global _default_client
    if _default_client is None:
        _default_client = DatabricksSQLClient()
    return _default_client