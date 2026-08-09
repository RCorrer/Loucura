import os
import logging
from databricks import sql
from databricks.sql.client import Connection
from databricks.sdk.core import Config

logger = logging.getLogger(__name__)


class DatabricksSQLClient:
    def __init__(self):
        self.cfg = Config()
        self.warehouse_id = os.getenv("DATABRICKS_WAREHOUSE_ID")
        self.catalog = os.getenv("UC_CATALOG", "plataforma")
        self.schema = os.getenv("UC_SCHEMA", "default")

        if not self.warehouse_id:
            raise ValueError("DATABRICKS_WAREHOUSE_ID não definido")

        self.host = self.cfg.host.replace("https://", "").replace("http://", "")
        logger.info("✅ DatabricksSQLClient inicializado com Config() + credentials_provider")

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
                    # Mantém ? como placeholder (não converte!)
                    logger.info(f"SQL: {sql}")
                    logger.info(f"Params: {params}")
                    if params:
                        # Garante que params é uma tupla
                        if not isinstance(params, tuple):
                            params = tuple(params)
                        cursor.execute(sql, params)
                    else:
                        cursor.execute(sql)

                    # Usa PyArrow para evitar erro de parsing com nulos
                    try:
                        arrow_table = cursor.fetchall_arrow()
                        if arrow_table.num_rows == 0:
                            return []
                        columns = arrow_table.column_names
                        rows = []
                        for i in range(arrow_table.num_rows):
                            row = [arrow_table[col][i].as_py() for col in columns]
                            rows.append(row)
                        return rows
                    except AttributeError:
                        rows = cursor.fetchall()
                        return [list(row) for row in rows]

        except Exception as e:
            logger.error(f"Erro na query: {e}")
            raise

    def fetch_one(self, sql: str, params: tuple = None) -> list:
        rows = self.execute_query(sql, params)
        return rows[0] if rows else None

    def fetch_all(self, sql: str, params: tuple = None) -> list:
        return self.execute_query(sql, params)

    def execute_insert(self, sql: str, params: tuple = None) -> int:
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                if params:
                    if not isinstance(params, tuple):
                        params = tuple(params)
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)
                return cursor.rowcount or 0


_default_client = None

def get_client() -> DatabricksSQLClient:
    global _default_client
    if _default_client is None:
        _default_client = DatabricksSQLClient()
    return _default_client