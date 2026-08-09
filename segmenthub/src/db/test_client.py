import os
import time
import logging
from databricks.sdk import WorkspaceClient

logger = logging.getLogger(__name__)


class TestDatabricksClient:
    def __init__(self):
        self.client = WorkspaceClient()
        self.warehouse_id = os.getenv("DATABRICKS_WAREHOUSE_ID")
        self.catalog = os.getenv("UC_CATALOG", "plataforma")
        self.schema = os.getenv("UC_SCHEMA", "default")
        self.timeout = int(os.getenv("QUERY_TIMEOUT_SECONDS", "120"))

        if not self.warehouse_id:
            raise ValueError("DATABRICKS_WAREHOUSE_ID não definido")

        logger.info("✅ TestClient inicializado com WorkspaceClient + result_format=JSON_ARRAY")

    def execute_query(self, sql: str, params: dict = None, timeout: int = None):
        timeout = timeout or self.timeout
        param_list = [{"name": k, "value": v} for k, v in (params or {}).items()] if params else None

        try:
            response = self.client.statement_execution.execute_statement(
                warehouse_id=self.warehouse_id,
                statement=sql,
                parameters=param_list,
                catalog=self.catalog,
                schema=self.schema,
                wait_timeout=timeout,
                result_format="JSON_ARRAY",  # <-- FORÇA JSON
            )
        except Exception as e:
            logger.error(f"Erro ao executar statement: {e}")
            raise

        # Polling
        for _ in range(int(timeout / 2)):
            result = self.client.statement_execution.get_statement(response.statement_id)
            state = str(result.status.state)
            if "SUCCEEDED" in state:
                return result.result.data_array if result.result else []
            if any(x in state for x in ["FAILED", "CANCELED", "CLOSED"]):
                error_msg = getattr(result.status, "error", "Erro desconhecido")
                raise RuntimeError(f"Query falhou: {error_msg}")
            time.sleep(2)

        raise TimeoutError("Timeout aguardando query")

    def fetch_one(self, sql: str, params: dict = None):
        rows = self.execute_query(sql, params)
        return rows[0] if rows else None


_default_client = None

def get_test_client() -> TestDatabricksClient:
    global _default_client
    if _default_client is None:
        _default_client = TestDatabricksClient()
    return _default_client