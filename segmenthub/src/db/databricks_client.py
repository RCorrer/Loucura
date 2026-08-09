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
        
        self.warehouse_id = os.getenv("DATABRICKS_WAREHOUSE_ID")
        self.catalog = os.getenv("UC_CATALOG", "plataforma")
        self.schema = os.getenv("UC_SCHEMA", "default")
        self.host = os.getenv("DATABRICKS_HOST")  # ou pode ser obtido do WorkspaceClient
        
        # Obtém credenciais OAuth explicitamente
        client_id = os.getenv("DATABRICKS_CLIENT_ID")
        client_secret = os.getenv("DATABRICKS_CLIENT_SECRET")
        
        logger.info(f"DATABRICKS_WAREHOUSE_ID: {self.warehouse_id}")
        logger.info(f"UC_CATALOG: {self.catalog}")
        logger.info(f"UC_SCHEMA: {self.schema}")
        logger.info(f"DATABRICKS_CLIENT_ID: {client_id[:10] if client_id else 'None'}")
        logger.info(f"DATABRICKS_CLIENT_SECRET: {'****' if client_secret else 'None'}")
        
        # Tenta criar WorkspaceClient com credenciais explícitas
        if client_id and client_secret:
            try:
                self.workspace = WorkspaceClient(
                    client_id=client_id,
                    client_secret=client_secret,
                )
                logger.info("✅ WorkspaceClient criado com credenciais OAuth explícitas")
            except Exception as e:
                logger.error(f"❌ Erro ao criar WorkspaceClient com OAuth: {e}")
                self.workspace = None
        else:
            # Fallback: WorkspaceClient padrão (pode não funcionar)
            self.workspace = WorkspaceClient()
            logger.warning("⚠️ WorkspaceClient criado sem credenciais explícitas (modo padrão)")
        
        # Obtém token
        if self.workspace:
            try:
                self.token = self.workspace.config.token
                if not self.token:
                    # Tenta forçar autenticação
                    logger.warning("⚠️ Token vazio, tentando forçar autenticação...")
                    self.token = self.workspace.config.token  # pode ser que o token seja obtido após alguma chamada
            except Exception as e:
                logger.error(f"❌ Erro ao obter token: {e}")
                self.token = None
        else:
            self.token = None
        
        logger.info(f"Token obtido: {self.token[:10] if self.token else 'None'}")
        
        if not self.warehouse_id:
            raise ValueError("DATABRICKS_WAREHOUSE_ID não definido")
        
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
            # Se não temos token, tentamos obter um novo usando o WorkspaceClient
            if self.workspace:
                try:
                    logger.info("Tentando renovar token...")
                    self.token = self.workspace.config.token
                except Exception as e:
                    logger.error(f"Erro ao renovar token: {e}")
            if not self.token:
                raise ValueError("Token OAuth não disponível para conexão")
        
        return sql.connect(
            server_hostname=self.host or self.workspace.config.host,
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