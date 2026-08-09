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

        logger.info("=" * 60)
        logger.info("🧪 TestClient inicializado")
        logger.info(f"   Warehouse ID: {self.warehouse_id}")
        logger.info(f"   Catalog: {self.catalog}")
        logger.info(f"   Schema: {self.schema}")
        logger.info("=" * 60)

    def _poll_result(self, statement_id: str, timeout: int) -> dict:
        """Polling manual para buscar o resultado."""
        start = time.time()
        while time.time() - start < timeout:
            result = self.client.statement_execution.get_statement(statement_id)
            state = str(result.status.state)
            logger.info(f"   📊 Polling: estado={state}")
            if "SUCCEEDED" in state:
                rows = result.result.data_array if result.result else []
                columns = result.result.column_names if result.result else []
                logger.info(f"   ✅ Query concluída! Linhas: {len(rows)}, Colunas: {columns}")
                return {"status": "success", "rows": rows, "columns": columns}
            if any(x in state for x in ["FAILED", "CANCELED", "CLOSED"]):
                error_msg = getattr(result.status, "error", "Erro desconhecido")
                logger.error(f"   ❌ Query falhou: {error_msg}")
                raise RuntimeError(f"Query falhou: {error_msg}")
            time.sleep(2)
        raise TimeoutError(f"Timeout após {timeout}s aguardando query")

    def execute_query(self, sql: str, params: dict = None, timeout: int = None):
        """
        Tenta executar a query com diferentes combinações de parâmetros.
        Todas as tentativas são registradas em logs.
        """
        timeout = timeout or self.timeout
        param_list = [{"name": k, "value": v} for k, v in (params or {}).items()] if params else None

        logger.info("")
        logger.info("=" * 60)
        logger.info(f"🚀 Executando query: {sql[:80]}...")
        logger.info("=" * 60)

        # ============================================================
        # TENTATIVA 1: Sem format (usa padrão JSON_ARRAY)
        # ============================================================
        logger.info("")
        logger.info("📌 [Tentativa 1] Sem parâmetro 'format' (padrão)")
        try:
            response = self.client.statement_execution.execute_statement(
                warehouse_id=self.warehouse_id,
                statement=sql,
                parameters=param_list,
                catalog=self.catalog,
                schema=self.schema,
                wait_timeout=timeout,
            )
            logger.info("   ✅ execute_statement chamado com sucesso (sem format)")
            result = self._poll_result(response.statement_id, timeout)
            return result
        except Exception as e:
            logger.error(f"   ❌ Falhou: {e}")

        # ============================================================
        # TENTATIVA 2: Com format='JSON_ARRAY' (explícito)
        # ============================================================
        logger.info("")
        logger.info("📌 [Tentativa 2] Com format='JSON_ARRAY'")
        try:
            response = self.client.statement_execution.execute_statement(
                warehouse_id=self.warehouse_id,
                statement=sql,
                parameters=param_list,
                catalog=self.catalog,
                schema=self.schema,
                wait_timeout=timeout,
                format="JSON_ARRAY",
            )
            logger.info("   ✅ execute_statement chamado com sucesso (format=JSON_ARRAY)")
            result = self._poll_result(response.statement_id, timeout)
            return result
        except Exception as e:
            logger.error(f"   ❌ Falhou: {e}")

        # ============================================================
        # TENTATIVA 3: wait_timeout=0 (assíncrono) + polling
        # ============================================================
        logger.info("")
        logger.info("📌 [Tentativa 3] wait_timeout=0 (assíncrono)")
        try:
            response = self.client.statement_execution.execute_statement(
                warehouse_id=self.warehouse_id,
                statement=sql,
                parameters=param_list,
                catalog=self.catalog,
                schema=self.schema,
                wait_timeout=0,
            )
            logger.info(f"   ✅ Statement iniciado (assíncrono), ID: {response.statement_id}")
            result = self._poll_result(response.statement_id, timeout)
            return result
        except Exception as e:
            logger.error(f"   ❌ Falhou: {e}")

        # ============================================================
        # TENTATIVA 4: wait_timeout=0 + format='JSON_ARRAY'
        # ============================================================
        logger.info("")
        logger.info("📌 [Tentativa 4] wait_timeout=0 + format='JSON_ARRAY'")
        try:
            response = self.client.statement_execution.execute_statement(
                warehouse_id=self.warehouse_id,
                statement=sql,
                parameters=param_list,
                catalog=self.catalog,
                schema=self.schema,
                wait_timeout=0,
                format="JSON_ARRAY",
            )
            logger.info(f"   ✅ Statement iniciado, ID: {response.statement_id}")
            result = self._poll_result(response.statement_id, timeout)
            return result
        except Exception as e:
            logger.error(f"   ❌ Falhou: {e}")

        # ============================================================
        # TENTATIVA 5: Sem catalog/schema (deixar o warehouse resolver)
        # ============================================================
        logger.info("")
        logger.info("📌 [Tentativa 5] Sem catalog/schema")
        try:
            response = self.client.statement_execution.execute_statement(
                warehouse_id=self.warehouse_id,
                statement=sql,
                parameters=param_list,
                wait_timeout=timeout,
            )
            logger.info("   ✅ execute_statement chamado com sucesso (sem catalog/schema)")
            result = self._poll_result(response.statement_id, timeout)
            return result
        except Exception as e:
            logger.error(f"   ❌ Falhou: {e}")

        # ============================================================
        # TENTATIVA 6: Sem parâmetros (query literal)
        # ============================================================
        logger.info("")
        logger.info("📌 [Tentativa 6] Query literal (sem parâmetros)")
        try:
            response = self.client.statement_execution.execute_statement(
                warehouse_id=self.warehouse_id,
                statement=sql,
                catalog=self.catalog,
                schema=self.schema,
                wait_timeout=timeout,
            )
            logger.info("   ✅ execute_statement chamado com sucesso (query literal)")
            result = self._poll_result(response.statement_id, timeout)
            return result
        except Exception as e:
            logger.error(f"   ❌ Falhou: {e}")

        # ============================================================
        # TENTATIVA 7: wait_timeout=5s + on_wait_timeout=CANCEL
        # ============================================================
        logger.info("")
        logger.info("📌 [Tentativa 7] wait_timeout=5s + on_wait_timeout=CANCEL")
        try:
            from databricks.sdk.service.sql import ExecuteStatementRequestOnWaitTimeout
            response = self.client.statement_execution.execute_statement(
                warehouse_id=self.warehouse_id,
                statement=sql,
                parameters=param_list,
                catalog=self.catalog,
                schema=self.schema,
                wait_timeout=5,
                on_wait_timeout=ExecuteStatementRequestOnWaitTimeout.CANCEL,
            )
            logger.info("   ✅ execute_statement chamado com sucesso")
            result = self._poll_result(response.statement_id, timeout)
            return result
        except Exception as e:
            logger.error(f"   ❌ Falhou: {e}")

        # ============================================================
        # TENTATIVA 8: wait_timeout=5s + on_wait_timeout=CONTINUE
        # ============================================================
        logger.info("")
        logger.info("📌 [Tentativa 8] wait_timeout=5s + on_wait_timeout=CONTINUE")
        try:
            from databricks.sdk.service.sql import ExecuteStatementRequestOnWaitTimeout
            response = self.client.statement_execution.execute_statement(
                warehouse_id=self.warehouse_id,
                statement=sql,
                parameters=param_list,
                catalog=self.catalog,
                schema=self.schema,
                wait_timeout=5,
                on_wait_timeout=ExecuteStatementRequestOnWaitTimeout.CONTINUE,
            )
            logger.info("   ✅ execute_statement chamado com sucesso")
            result = self._poll_result(response.statement_id, timeout)
            return result
        except Exception as e:
            logger.error(f"   ❌ Falhou: {e}")

        # ============================================================
        # NENHUMA TENTATIVA FUNCIONOU
        # ============================================================
        logger.error("")
        logger.error("❌❌❌ TODAS AS TENTATIVAS FALHARAM ❌❌❌")
        raise RuntimeError("Nenhuma combinação de parâmetros funcionou")

    def fetch_one(self, sql: str, params: dict = None):
        result = self.execute_query(sql, params)
        if result and result.get("rows"):
            return result["rows"][0]
        return None


_default_client = None

def get_test_client() -> TestDatabricksClient:
    global _default_client
    if _default_client is None:
        _default_client = TestDatabricksClient()
    return _default_client