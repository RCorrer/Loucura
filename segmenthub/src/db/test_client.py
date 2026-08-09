import os
import logging
from databricks import sql
from databricks.sql.client import Connection
from databricks.sdk.core import Config

logger = logging.getLogger(__name__)


class TestDatabricksClient:
    def __init__(self):
        # Config detecta automaticamente as credenciais do ambiente
        self.cfg = Config()
        self.warehouse_id = os.getenv("DATABRICKS_WAREHOUSE_ID")
        self.catalog = os.getenv("UC_CATALOG", "plataforma")
        self.schema = os.getenv("UC_SCHEMA", "default")

        if not self.warehouse_id:
            raise ValueError("DATABRICKS_WAREHOUSE_ID não definido")

        logger.info("✅ TestClient inicializado com Config() + credentials_provider")

    def _get_connection(self) -> Connection:
        return sql.connect(
            server_hostname=self.cfg.host,
            http_path=f"/sql/1.0/warehouses/{self.warehouse_id}",
            catalog=self.catalog,
            schema=self.schema,
            credentials_provider=lambda: self.cfg.authenticate,  # <-- método correto
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