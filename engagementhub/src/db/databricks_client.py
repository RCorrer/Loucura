"""Cliente SQL para o EngagementHub (S3). Idêntico ao S1 — Service Principal + PyArrow."""

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
        self.schema = os.getenv("UC_SCHEMA", "engagement")

        if not self.warehouse_id:
            raise ValueError("DATABRICKS_WAREHOUSE_ID não definido")

        self.host = self.cfg.host.replace("https://", "").replace("http://", "")
        logger.info("\u2705 DatabricksSQLClient (S3) inicializado")

    def _get_connection(self) -> Connection:
        return sql.connect(
            server_hostname=self.host,
            http_path=f"/sql/1.0/warehouses/{self.warehouse_id}",
            catalog=self.catalog,
            schema=self.schema,
            credentials_provider=lambda: self.cfg.authenticate,
        )

    def execute_query(self, query: str, params: tuple = None) -> list:
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    if params:
                        if not isinstance(params, tuple):
                            params = tuple(params)
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)

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

    def fetch_one(self, query: str, params: tuple = None) -> list:
        rows = self.execute_query(query, params)
        return rows[0] if rows else None

    def fetch_all(self, query: str, params: tuple = None) -> list:
        return self.execute_query(query, params)

    def execute_insert(self, query: str, params: tuple = None) -> int:
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                if params:
                    if not isinstance(params, tuple):
                        params = tuple(params)
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                return cursor.rowcount or 0


_default_client = None


def get_client():
    """Singleton: retorna DatabricksSQLClient (ou FakeSQLiteClient em modo local)."""
    global _default_client
    if _default_client is None:
        env = os.getenv("ENV", "production").lower()
        if env == "local":
            from src.db.fake_client import FakeSQLiteClient
            _default_client = FakeSQLiteClient()
            logger.info("\ud83d\udd27 FakeSQLiteClient (modo local)")
        else:
            _default_client = DatabricksSQLClient()
    return _default_client
