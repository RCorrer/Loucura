import os
from dotenv import load_dotenv

load_dotenv()

class AppConfig:
    DATABRICKS_HOST = os.getenv("DATABRICKS_HOST", "").replace("https://", "")
    DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN", "")
    DATABRICKS_WAREHOUSE_ID = os.getenv("DATABRICKS_WAREHOUSE_ID", "")
    UC_CATALOG = os.getenv("UC_CATALOG", "plataforma")
    UC_SCHEMA = os.getenv("UC_SCHEMA", "default")

    QUERY_TIMEOUT_SECONDS = int(os.getenv("QUERY_TIMEOUT_SECONDS", "120"))
    POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "2"))
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_BACKOFF_SECONDS = int(os.getenv("RETRY_BACKOFF_SECONDS", "1"))
    RETRY_BACKOFF_FACTOR = float(os.getenv("RETRY_BACKOFF_FACTOR", "2"))

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")