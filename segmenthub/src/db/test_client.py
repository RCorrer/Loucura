import os
import logging
from databricks import sql
from databricks.sql.client import Connection
from databricks.sdk.core import Config

logger = logging.getLogger(__name__)


class TestDatabricksClient:
    def __init__(self):
        self.cfg = Config()
        self.warehouse_id = os.getenv("DATABRICKS_WAREHOUSE_ID")
        self.catalog = os.getenv("UC_CATALOG", "plataforma")
        self.schema = os.getenv("UC_SCHEMA", "default")

        if not self.warehouse_id:
            raise ValueError("DATABRICKS_WAREHOUSE_ID não definido")

        self.host = self.cfg.host.replace("https://", "").replace("http://", "")

        logger.info(f"✅ TestClient inicializado com Config() + credentials_provider")
        logger.info(f"   Host: {self.host}")
        logger.info(f"   Warehouse: {self.warehouse_id}")

    def _get_connection(self) -> Connection:
        return sql.connect(
            server_hostname=self.host,
            http_path=f"/sql/1.0/warehouses/{self.warehouse_id}",
            catalog=self.catalog,
            schema=self.schema,
            credentials_provider=lambda: self.cfg.authenticate,
        )

    def execute_query(self, sql: str, params: tuple = None) -> list:
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    if params:
                        cursor.execute(sql, params)
                    else:
                        cursor.execute(sql)

                    # Tenta fetchall_arrow primeiro (PyArrow)
                    try:
                        arrow_table = cursor.fetchall_arrow()
                        # Converte para lista de listas
                        if arrow_table.num_rows == 0:
                            return []
                        # Obtém nomes das colunas e converte cada linha
                        columns = arrow_table.column_names
                        rows = []
                        for i in range(arrow_table.num_rows):
                            row = [arrow_table[col][i].as_py() for col in columns]
                            rows.append(row)
                        return rows
                    except AttributeError:
                        # Fallback: fetchall normal (pode causar erro com nulos)
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