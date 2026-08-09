import os
import time
import logging
from typing import Dict, Any, List, Optional, Tuple
from databricks import sql
from databricks.sql.client import Connection

logger = logging.getLogger(__name__)


class DatabricksSQLClient:
    def __init__(self):
        self.host = os.getenv("DATABRICKS_HOST", "").replace("https://", "")
        self.token = os.getenv("DATABRICKS_TOKEN")
        self.warehouse_id = os.getenv("DATABRICKS_WAREHOUSE_ID")
        self.catalog = os.getenv("UC_CATALOG", "plataforma")
        self.schema = os.getenv("UC_SCHEMA", "default")
        self.timeout = int(os.getenv("QUERY_TIMEOUT_SECONDS", "120"))
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        self.backoff = int(os.getenv("RETRY_BACKOFF_SECONDS", "1"))
        self.backoff_factor = float(os.getenv("RETRY_BACKOFF_FACTOR", "2"))

        if not self.host:
            raise ValueError("DATABRICKS_HOST não definido")
        if not self.token:
            raise ValueError("DATABRICKS_TOKEN não definido")
        if not self.warehouse_id:
            raise ValueError("DATABRICKS_WAREHOUSE_ID não definido")

        logger.info("✅ DatabricksSQLClient inicializado com sql.connect (PAT)")

    def _get_connection(self) -> Connection:
        return sql.connect(
            server_hostname=self.host,
            http_path=f"/sql/1.0/warehouses/{self.warehouse_id}",
            access_token=self.token,
            catalog=self.catalog,
            schema=self.schema,
        )

    def execute_query(self, sql_query: str, params: Optional[tuple] = None, fetch: bool = True) -> List[Dict]:
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
                            return cursor.rowcount or 0
            except Exception as e:
                logger.warning(f"Tentativa {attempt+1} falhou: {e}")
                if attempt < self.max_retries - 1:
                    wait = self.backoff * (self.backoff_factor ** attempt)
                    logger.info(f"Re-tentando em {wait}s...")
                    time.sleep(wait)
                else:
                    raise RuntimeError(f"Falha após {self.max_retries} tentativas: {e}")
        return []

    def fetch_one(self, sql: str, params: Optional[tuple] = None) -> Optional[Dict]:
        results = self.execute_query(sql, params)
        return results[0] if results else None

    def fetch_value(self, sql: str, params: Optional[tuple] = None):
        row = self.fetch_one(sql, params)
        return list(row.values())[0] if row else None

    def execute_insert(self, sql: str, params: Optional[tuple] = None) -> int:
        return self.execute_query(sql, params, fetch=False)


_default_client = None

def get_client() -> DatabricksSQLClient:
    global _default_client
    if _default_client is None:
        _default_client = DatabricksSQLClient()
    return _default_client