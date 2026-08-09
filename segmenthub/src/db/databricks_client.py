"""
Databricks SQL Warehouse client for SegmentHub (S1).
Stateless client using WorkspaceClient (statement_execution).
Uses OBO (On-Behalf-Of) for user authentication or Service Principal for app identity.
"""

import time
import logging
from typing import Dict, Any, List, Optional
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import NotFound, PermissionDenied
import os

logger = logging.getLogger(__name__)


class DatabricksSQLClient:
    """Cliente stateless para executar queries no SQL Warehouse via WorkspaceClient."""

    def __init__(self, user_token: Optional[str] = None):
        """
        Args:
            user_token: Token de acesso do usuário (OBO) - obtido do cabeçalho X-Forwarded-Access-Token.
                        Se None, usa a identidade do app (Service Principal).
        """
        if user_token:
            self.client = WorkspaceClient(token=user_token)
        else:
            self.client = WorkspaceClient()  # usa service principal do app

        self.warehouse_id = os.getenv("DATABRICKS_WAREHOUSE_ID")
        self.catalog = os.getenv("UC_CATALOG", "plataforma")
        self.schema = os.getenv("UC_SCHEMA", "default")

        if not self.warehouse_id:
            raise ValueError("DATABRICKS_WAREHOUSE_ID não definido")

        self.timeout = int(os.getenv("QUERY_TIMEOUT_SECONDS", "120"))
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        self.backoff = int(os.getenv("RETRY_BACKOFF_SECONDS", "1"))
        self.backoff_factor = float(os.getenv("RETRY_BACKOFF_FACTOR", "2"))
        self.poll_interval = int(os.getenv("POLL_INTERVAL_SECONDS", "2"))

    def execute_query(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Executa uma query SQL com parâmetros nomeados.
        Usa statement_execution (stateless) e aguarda o resultado com polling.
        """
        timeout = timeout or self.timeout
        param_list = [{"name": k, "value": v} for k, v in (params or {}).items()]

        for attempt in range(self.max_retries):
            try:
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
                elif state in ["FAILED", "CANCELED", "CLOSED"]:
                    error_msg = getattr(result.status, "error", "Erro desconhecido")
                    raise RuntimeError(f"Query falhou: {error_msg}")
                else:
                    # Polling manual (fallback)
                    return self._poll_query(response.statement_id, timeout)

            except (TimeoutError, PermissionDenied, NotFound) as e:
                if attempt < self.max_retries - 1:
                    wait = self.backoff * (self.backoff_factor ** attempt)
                    logger.warning(f"Tentativa {attempt+1} falhou: {e}. Re-tentando em {wait}s...")
                    time.sleep(wait)
                else:
                    raise RuntimeError(f"Falha após {self.max_retries} tentativas: {e}") from e

        raise RuntimeError("Falha inesperada")

    def _poll_query(self, statement_id: str, timeout: int) -> List[Dict]:
        """Polling manual (fallback para estados inesperados)."""
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
            time.sleep(self.poll_interval)
        raise TimeoutError(f"Timeout após {timeout}s aguardando query")

    def fetch_one(self, sql: str, params: Optional[Dict] = None) -> Optional[Dict]:
        results = self.execute_query(sql, params)
        return results[0] if results else None

    def fetch_value(self, sql: str, params: Optional[Dict] = None):
        row = self.fetch_one(sql, params)
        return list(row.values())[0] if row else None

    def execute_insert(self, sql: str, params: Optional[Dict] = None) -> int:
        param_list = [{"name": k, "value": v} for k, v in (params or {}).items()]
        response = self.client.statement_execution.execute_statement(
            warehouse_id=self.warehouse_id,
            statement=sql,
            parameters=param_list if param_list else None,
            catalog=self.catalog,
            schema=self.schema,
            wait_timeout=self.timeout,
        )
        result = self.client.statement_execution.get_statement(response.statement_id)
        return result.status.row_count or 0


# Singleton (com token opcional)
_default_client = None

def get_client(user_token: Optional[str] = None) -> DatabricksSQLClient:
    global _default_client
    if user_token:
        return DatabricksSQLClient(user_token=user_token)
    if _default_client is None:
        _default_client = DatabricksSQLClient()
    return _default_client