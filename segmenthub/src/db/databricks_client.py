"""
Databricks SQL Warehouse client for SegmentHub (S1).
Stateless client using databricks-sql-connector.
Each call opens and closes a connection – no shared state.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple
from databricks import sql
from databricks.sql.client import Connection
from src.core.config import AppConfig

logger = logging.getLogger(__name__)


class DatabricksSQLClient:
    """Cliente stateless para executar queries no SQL Warehouse."""

    def __init__(self):
        self.host = AppConfig.DATABRICKS_HOST.replace("https://", "")
        self.token = AppConfig.DATABRICKS_TOKEN
        self.warehouse_id = AppConfig.DATABRICKS_WAREHOUSE_ID
        self.catalog = AppConfig.UC_CATALOG
        self.schema = AppConfig.UC_SCHEMA
        self.timeout = AppConfig.QUERY_TIMEOUT_SECONDS
        self.max_retries = AppConfig.MAX_RETRIES
        self.backoff = AppConfig.RETRY_BACKOFF_SECONDS
        self.backoff_factor = AppConfig.RETRY_BACKOFF_FACTOR

        if not all([self.host, self.token, self.warehouse_id]):
            raise ValueError(
                "DATABRICKS_HOST, DATABRICKS_TOKEN e DATABRICKS_WAREHOUSE_ID são obrigatórios."
            )

    def _get_connection(self) -> Connection:
        """Cria uma nova conexão com o SQL Warehouse (stateless)."""
        return sql.connect(
            server_hostname=self.host,
            http_path=f"/sql/1.0/warehouses/{self.warehouse_id}",
            access_token=self.token,
            catalog=self.catalog,
            schema=self.schema,
        )

    def execute_query(
        self,
        sql_query: str,
        params: Optional[Tuple[Any, ...]] = None,
        fetch: bool = True,
        timeout: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Executa uma query SQL parametrizada.
        Usa placeholders '?' para parâmetros.
        """
        for attempt in range(self.max_retries):
            try:
                with self._get_connection() as conn:
                    with conn.cursor() as cursor:
                        if params:
                            cursor.execute(sql_query, params)
                        else:
                            cursor.execute(sql_query)

                        if fetch:
                            columns = [desc[0] for desc in cursor.description] if cursor.description else []
                            rows = cursor.fetchall()
                            return [dict(zip(columns, row)) for row in rows]
                        else:
                            # Para INSERT/UPDATE/DELETE, retorna rowcount
                            return cursor.rowcount or 0

            except Exception as e:
                logger.warning(f"Tentativa {attempt+1} falhou: {e}")
                if attempt < self.max_retries - 1:
                    wait = self.backoff * (self.backoff_factor ** attempt)
                    logger.info(f"Tentando novamente em {wait}s...")
                    time.sleep(wait)
                else:
                    raise RuntimeError(f"Falha após {self.max_retries} tentativas: {e}") from e

        return []

    def fetch_one(self, sql: str, params: Optional[Tuple] = None) -> Optional[Dict]:
        """Retorna a primeira linha da consulta."""
        results = self.execute_query(sql, params)
        return results[0] if results else None

    def fetch_value(self, sql: str, params: Optional[Tuple] = None):
        """Retorna o valor da primeira coluna da primeira linha."""
        row = self.fetch_one(sql, params)
        return list(row.values())[0] if row else None

    def execute_insert(self, sql: str, params: Optional[Tuple] = None) -> int:
        """Executa INSERT/UPDATE/DELETE e retorna número de linhas afetadas."""
        return self.execute_query(sql, params, fetch=False)


# Singleton – cada chamada ao cliente ainda é stateless, pois a conexão
# é criada e descartada dentro de cada método.
_default_client = None

def get_client() -> DatabricksSQLClient:
    global _default_client
    if _default_client is None:
        _default_client = DatabricksSQLClient()
    return _default_client