import os
import logging
from databricks.sdk import WorkspaceClient

logger = logging.getLogger(__name__)


class DatabricksSQLClient:
    def __init__(self):
        self.client = WorkspaceClient()
        self.warehouse_id = os.getenv("DATABRICKS_WAREHOUSE_ID")
        self.catalog = os.getenv("UC_CATALOG", "plataforma")
        self.schema = os.getenv("UC_SCHEMA", "default")
        self.timeout = int(os.getenv("QUERY_TIMEOUT_SECONDS", "120"))

        if not self.warehouse_id:
            raise ValueError("DATABRICKS_WAREHOUSE_ID não definido")

        logger.info("✅ DatabricksSQLClient inicializado com WorkspaceClient")

    def execute_query(self, sql: str, params: list = None):
        try:
            response = self.client.statement_execution.execute_statement(
                warehouse_id=self.warehouse_id,
                statement=sql,
                parameters=params,
                catalog=self.catalog,
                schema=self.schema,
                wait_timeout=self.timeout,
            )
            return response
        except Exception as e:
            logger.error(f"Erro na query: {e}")
            raise

    def fetch_one(self, sql: str, params: list = None):
        response = self.execute_query(sql, params)
        result = self.client.statement_execution.get_statement(response.statement_id)
        if result.status.state == "SUCCEEDED":
            rows = result.result.data_array if result.result else []
            if rows and result.result.column_names:
                columns = result.result.column_names
                return dict(zip(columns, rows[0])) if rows else None
        return None

    def fetch_all(self, sql: str, params: list = None):
        response = self.execute_query(sql, params)
        result = self.client.statement_execution.get_statement(response.statement_id)
        if result.status.state == "SUCCEEDED":
            rows = result.result.data_array if result.result else []
            if rows and result.result.column_names:
                columns = result.result.column_names
                return [dict(zip(columns, row)) for row in rows]
        return []


_default_client = None

def get_client() -> DatabricksSQLClient:
    global _default_client
    if _default_client is None:
        _default_client = DatabricksSQLClient()
    return _default_client