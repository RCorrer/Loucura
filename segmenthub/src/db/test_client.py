import os
import logging
from databricks import sql
from databricks.sql.client import Connection

logger = logging.getLogger(__name__)


class TestDatabricksClient:
    def __init__(self):
        self.host = os.getenv("DATABRICKS_HOST", "").replace("https://", "")
        self.warehouse_id = os.getenv("DATABRICKS_WAREHOUSE_ID")
        self.catalog = os.getenv("UC_CATALOG", "plataforma")
        self.schema = os.getenv("UC_SCHEMA", "default")

        # Credenciais OAuth do Service Principal (injetadas)
        self.client_id = os.getenv("DATABRICKS_CLIENT_ID")
        self.client_secret = os.getenv("DATABRICKS_CLIENT_SECRET")

        if not self.host or not self.warehouse_id:
            raise ValueError("DATABRICKS_HOST e DATABRICKS_WAREHOUSE_ID são obrigatórios")
        if not self.client_id or not self.client_secret:
            raise ValueError("DATABRICKS_CLIENT_ID e DATABRICKS_CLIENT_SECRET são obrigatórios para OAuth")

        logger.info("✅ TestClient inicializado com sql.connect + OAuth (Service Principal)")

    def _get_connection(self) -> Connection:
        return sql.connect(
            server_hostname=self.host,
            http_path=f"/sql/1.0/warehouses/{self.warehouse_id}",
            catalog=self.catalog,
            schema=self.schema,
            auth_type='oauth',          # <-- OAuth explícito
            client_id=self.client_id,
            client_secret=self.client_secret,
        )

    def execute_query(self, sql: str, params: tuple = None) -> list:
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    if params:
                        cursor.execute(sql, params)
                    else:
                        cursor.execute(sql)
                    rows = cursor.fetchall()
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