import os
import time
import logging
from databricks import sql
from databricks.sql.client import Connection
from databricks.sdk import WorkspaceClient

logger = logging.getLogger(__name__)


class TestDatabricksClient:
    def __init__(self):
        # Obtém token do Service Principal via WorkspaceClient
        self.workspace = WorkspaceClient()
        self.warehouse_id = os.getenv("DATABRICKS_WAREHOUSE_ID")
        self.catalog = os.getenv("UC_CATALOG", "plataforma")
        self.schema = os.getenv("UC_SCHEMA", "default")
        self.timeout = int(os.getenv("QUERY_TIMEOUT_SECONDS", "120"))

        if not self.warehouse_id:
            raise ValueError("DATABRICKS_WAREHOUSE_ID não definido")

        # Token do Service Principal
        self.token = self.workspace.config.token
        if not self.token:
            raise ValueError("Não foi possível obter token do Service Principal")
        self.host = self.workspace.config.host

        logger.info("✅ TestClient inicializado com sql.connect (Service Principal)")

    def _get_connection(self) -> Connection:
        return sql.connect(
            server_hostname=self.host,
            http_path=f"/sql/1.0/warehouses/{self.warehouse_id}",
            access_token=self.token,
            catalog=self.catalog,
            schema=self.schema,
        )

    def execute_query(self, sql: str, params: tuple = None, timeout: int = None):
        timeout = timeout or self.timeout
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    if params:
                        cursor.execute(sql, params)
                    else:
                        cursor.execute(sql)
                    rows = cursor.fetchall()
                    # Retorna como lista de listas (sem nomes de colunas)
                    return [list(row) for row in rows]
        except Exception as e:
            logger.error(f"Erro na query: {e}")
            raise

    def fetch_one(self, sql: str, params: tuple = None):
        rows = self.execute_query(sql, params)
        return rows[0] if rows else None


_default_client = None

def get_test_client() -> TestDatabricksClient:
    global _default_client
    if _default_client is None:
        _default_client = TestDatabricksClient()
    return _default_client