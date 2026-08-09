import os
import time
import logging
from typing import Dict, Any, List, Optional, Tuple
from databricks import sql
from databricks.sql.client import Connection
from databricks.sdk import WorkspaceClient

logger = logging.getLogger(__name__)


class DatabricksSQLClient:
    def __init__(self):
        logger.info("=== Inicializando DatabricksSQLClient ===")
        
        # 1. Verifica variáveis de ambiente
        self.warehouse_id = os.getenv("DATABRICKS_WAREHOUSE_ID")
        self.catalog = os.getenv("UC_CATALOG", "plataforma")
        self.schema = os.getenv("UC_SCHEMA", "default")
        
        logger.info(f"DATABRICKS_WAREHOUSE_ID: {self.warehouse_id}")
        logger.info(f"UC_CATALOG: {self.catalog}")
        logger.info(f"UC_SCHEMA: {self.schema}")
        
        # 2. Tenta criar WorkspaceClient
        try:
            self.workspace = WorkspaceClient()
            logger.info("✅ WorkspaceClient criado com sucesso")
        except Exception as e:
            logger.error(f"❌ Erro ao criar WorkspaceClient: {e}")
            raise
        
        # 3. Verifica se o token foi obtido
        try:
            self.token = self.workspace.config.token
            logger.info(f"✅ Token OAuth obtido (primeiros 10 caracteres): {self.token[:10] if self.token else 'None'}")
        except Exception as e:
            logger.error(f"❌ Erro ao obter token: {e}")
            self.token = None
        
        # 4. Verifica o host
        try:
            self.host = self.workspace.config.host
            logger.info(f"✅ Host: {self.host}")
        except Exception as e:
            logger.error(f"❌ Erro ao obter host: {e}")
            self.host = None
        
        # 5. Verifica se há token
        if not self.token:
            logger.warning("⚠️ Token OAuth não disponível! Tentando usar variáveis de ambiente OAuth...")
            # Fallback: tenta usar DATABRICKS_CLIENT_ID e DATABRICKS_CLIENT_SECRET
            client_id = os.getenv("DATABRICKS_CLIENT_ID")
            client_secret = os.getenv("DATABRICKS_CLIENT_SECRET")
            logger.info(f"DATABRICKS_CLIENT_ID: {client_id[:10] if client_id else 'None'}")
            logger.info(f"DATABRICKS_CLIENT_SECRET: {'****' if client_secret else 'None'}")
        
        # 6. Verifica warehouse_id
        if not self.warehouse_id:
            raise ValueError("DATABRICKS_WAREHOUSE_ID não definido")
        
        # 7. Timeouts
        self.timeout = int(os.getenv("QUERY_TIMEOUT_SECONDS", "120"))
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        self.backoff = int(os.getenv("RETRY_BACKOFF_SECONDS", "1"))
        self.backoff_factor = float(os.getenv("RETRY_BACKOFF_FACTOR", "2"))
        
        logger.info("=== DatabricksSQLClient inicializado ===")

    def _get_connection(self) -> Connection:
        logger.info("=== Criando conexão SQL ===")
        logger.info(f"Host: {self.host}")
        logger.info(f"Warehouse path: /sql/1.0/warehouses/{self.warehouse_id}")
        logger.info(f"Catalog: {self.catalog}")
        logger.info(f"Schema: {self.schema}")
        logger.info(f"Token disponível: {bool(self.token)}")
        
        if not self.token:
            raise ValueError("Token OAuth não disponível para conexão")
        
        return sql.connect(
            server_hostname=self.host,
            http_path=f"/sql/1.0/warehouses/{self.warehouse_id}",
            access_token=self.token,
            catalog=self.catalog,
            schema=self.schema,
        )

    def execute_query(self, sql_query: str, params: Optional[tuple] = None, fetch: bool = True) -> List[Dict]:
        logger.info(f"Executando query: {sql_query[:100]}...")
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