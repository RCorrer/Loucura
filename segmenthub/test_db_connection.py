# test_db_connection.py
"""
Teste completo de conexão com Databricks SQL Warehouse.
Testa diferentes abordagens e opções para identificar a melhor.
"""
import os
import time
import json
import requests
from databricks import sql
from databricks.sdk import WorkspaceClient
from dotenv import load_dotenv

load_dotenv()

# ===== CONFIGURAÇÕES =====
HOST = os.getenv("DATABRICKS_HOST", "").replace("https://", "")
TOKEN = os.getenv("DATABRICKS_TOKEN", "")
WAREHOUSE_ID = os.getenv("DATABRICKS_WAREHOUSE_ID", "")
CATALOG = os.getenv("UC_CATALOG", "plataforma")
SCHEMA = os.getenv("UC_SCHEMA", "default")
BASE_URL = f"https://{HOST}" if HOST else ""

print("=" * 60)
print("TESTE DE CONEXÃO DATABRICKS SQL WAREHOUSE")
print("=" * 60)
print(f"Host: {HOST}")
print(f"Warehouse ID: {WAREHOUSE_ID}")
print(f"Catalog: {CATALOG}")
print(f"Schema: {SCHEMA}")
print("=" * 60)


# ===== 1. TESTE COM databricks-sql-connector (já funcionou) =====
def test_connector():
    print("\n[1] Testando databricks-sql-connector...")
    try:
        conn = sql.connect(
            server_hostname=HOST,
            http_path=f"/sql/1.0/warehouses/{WAREHOUSE_ID}",
            access_token=TOKEN,
            catalog=CATALOG,
            schema=SCHEMA,
        )
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchall()
        cursor.close()
        conn.close()
        print("✅ Connector funcionou! Resultado:", result)
        return True
    except Exception as e:
        print("❌ Connector falhou:", e)
        return False


# ===== 2. TESTE COM WorkspaceClient (SDK stateless) =====
def test_workspace_client(query="SELECT 1", catalog=None, schema=None, result_format=None):
    print(f"\n[2] Testando WorkspaceClient com query: {query}")
    print(f"    Catalog: {catalog or 'None'}, Schema: {schema or 'None'}")
    try:
        client = WorkspaceClient()
        response = client.statement_execution.execute_statement(
            warehouse_id=WAREHOUSE_ID,
            statement=query,
            catalog=catalog,
            schema=schema,
            wait_timeout=60,
            # result_format=result_format,  # descomente se quiser testar
        )
        # Aguarda resultado
        result = client.statement_execution.get_statement(response.statement_id)
        state = str(result.status.state)
        print(f"    Estado: {state}")
        if state == "SUCCEEDED":
            print("✅ WorkspaceClient funcionou!")
            print("    Resultados:", result.result.data_array if result.result else "vazio")
            return True
        else:
            print("❌ WorkspaceClient falhou (estado não SUCEDED):", state)
            return False
    except Exception as e:
        print("❌ WorkspaceClient falhou:", e)
        return False


# ===== 3. TESTE COM API REST =====
def test_rest_api(query="SELECT 1", catalog=None, schema=None, result_format="JSON_ARRAY"):
    print(f"\n[3] Testando API REST com query: {query}")
    print(f"    Catalog: {catalog or 'None'}, Schema: {schema or 'None'}, Format: {result_format}")
    
    if not BASE_URL:
        print("❌ HOST não definido")
        return False
    
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "warehouse_id": WAREHOUSE_ID,
        "statement": query,
        "wait_timeout": 60,
        "result_format": result_format,
    }
    if catalog:
        payload["catalog"] = catalog
    if schema:
        payload["schema"] = schema
    
    try:
        # Executa a query
        response = requests.post(
            f"{BASE_URL}/api/2.0/sql/statements",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        statement_id = data.get("statement_id")
        print(f"    Statement ID: {statement_id}")
        
        # Polling para aguardar resultado
        for _ in range(30):  # até 60s
            status_resp = requests.get(
                f"{BASE_URL}/api/2.0/sql/statements/{statement_id}",
                headers=headers,
            )
            status_data = status_resp.json()
            state = status_data.get("status", {}).get("state")
            print(f"    Estado: {state}")
            
            if state == "SUCCEEDED":
                result = status_data.get("result", {}).get("data_array")
                print("✅ API REST funcionou!")
                print("    Resultados:", result)
                return True
            elif state in ["FAILED", "CANCELED", "CLOSED"]:
                error = status_data.get("status", {}).get("error")
                print(f"❌ API REST falhou: {error}")
                return False
            time.sleep(2)
        else:
            print("⏰ Timeout aguardando resultado")
            return False
            
    except Exception as e:
        print("❌ API REST falhou:", e)
        return False


# ===== EXECUTAR TESTES =====
print("\n🔍 Executando testes...\n")

# Teste 1: Connector (baseline)
test_connector()

# Teste 2: WorkspaceClient com diferentes configurações
# 2a: sem catalog/schema
test_workspace_client("SELECT 1", catalog=None, schema=None)
# 2b: com catalog e schema
test_workspace_client("SELECT 1", catalog=CATALOG, schema=SCHEMA)
# 2c: query com CAST
test_workspace_client("SELECT CAST(1 AS INT) AS valor", catalog=CATALOG, schema=SCHEMA)
# 2d: query real (COUNT)
test_workspace_client("SELECT COUNT(*) FROM plataforma.core_cliente.golden_record", catalog=CATALOG, schema=SCHEMA)

# Teste 3: API REST com diferentes configurações
# 3a: sem catalog/schema
test_rest_api("SELECT 1", catalog=None, schema=None)
# 3b: com catalog e schema
test_rest_api("SELECT 1", catalog=CATALOG, schema=SCHEMA)
# 3c: com CAST
test_rest_api("SELECT CAST(1 AS INT) AS valor", catalog=CATALOG, schema=SCHEMA)
# 3d: com ARRAY format
test_rest_api("SELECT 1", catalog=CATALOG, schema=SCHEMA, result_format="ARRAY")
# 3e: query real (COUNT)
test_rest_api("SELECT COUNT(*) FROM plataforma.core_cliente.golden_record", catalog=CATALOG, schema=SCHEMA)

print("\n" + "=" * 60)
print("FIM DOS TESTES")
print("=" * 60)