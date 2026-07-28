# Placeholder - S1 usa Service Principal
class DatabricksClient:
    def __init__(self):
        # TODO: configurar via ambiente (DATABRICKS_SERVER_HOSTNAME, TOKEN, etc)
        pass

    def execute_query(self, sql: str, params: tuple = ()):
        # TODO: implementar com databricks-sql-connector
        return []

    def execute_insert(self, sql: str, params: tuple = ()):
        # TODO: implementar
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
