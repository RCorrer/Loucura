#!/usr/bin/env python3
"""
Teste completo de conexão com Databricks SQL Warehouse.
Testa todas as abordagens possíveis para encontrar uma solução stateless funcional.
"""

import os
import sys
import time
import subprocess
import importlib
from dotenv import load_dotenv

# Carrega .env
load_dotenv()

# ============================================================
# CONFIGURAÇÕES
# ============================================================
HOST = os.getenv("DATABRICKS_HOST")
TOKEN = os.getenv("DATABRICKS_TOKEN")
WAREHOUSE_ID = os.getenv("DATABRICKS_WAREHOUSE_ID")
CATALOG = os.getenv("UC_CATALOG", "plataforma")
SCHEMA = os.getenv("UC_SCHEMA", "default")

# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================
def print_header(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def print_result(test_name, success, detail=None):
    status = "✅" if success else "❌"
    print(f"{status} {test_name}")
    if detail:
        print(f"   {detail}")

# ============================================================
# TESTE 1: databricks-sql-connector (baseline)
# ============================================================
def test_connector():
    print_header("TESTE 1: databricks-sql-connector (baseline)")
    try:
        from databricks import sql
        conn = sql.connect(
            server_hostname=HOST.replace("https://", ""),
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
        print_result("Connector com SELECT 1", True, f"Resultado: {result}")
        return True
    except Exception as e:
        print_result("Connector com SELECT 1", False, str(e))
        return False

# ============================================================
# TESTE 2: WorkspaceClient com diferentes configurações
# ============================================================
def test_workspace_client():
    print_header("TESTE 2: WorkspaceClient (databricks-sdk)")
    try:
        from databricks.sdk import WorkspaceClient
        client = WorkspaceClient()
        
        # Configurações a testar
        configs = [
            ("Sem catalog/schema", None, None, "SELECT 1"),
            ("Com catalog/schema", CATALOG, SCHEMA, "SELECT 1"),
            ("Com CAST", CATALOG, SCHEMA, "SELECT CAST(1 AS INT) AS valor"),
            ("Com COUNT real", CATALOG, SCHEMA, "SELECT COUNT(*) FROM plataforma.core_cliente.golden_record"),
            ("Com wait_timeout=0 (async)", CATALOG, SCHEMA, "SELECT 1", 0),
            ("Com result_format=JSON_ARRAY", CATALOG, SCHEMA, "SELECT 1", 60, "JSON_ARRAY"),
        ]
        
        for label, cat, sch, sql, *extra in configs:
            wait = extra[0] if extra else 60
            fmt = extra[1] if len(extra) > 1 else None
            try:
                kwargs = {
                    "warehouse_id": WAREHOUSE_ID,
                    "statement": sql,
                    "catalog": cat,
                    "schema": sch,
                    "wait_timeout": wait,
                }
                if fmt:
                    kwargs["result_format"] = fmt
                
                response = client.statement_execution.execute_statement(**kwargs)
                
                # Se wait_timeout=0, faz polling manual
                if wait == 0:
                    stmt_id = response.statement_id
                    for _ in range(30):  # até 60s
                        result = client.statement_execution.get_statement(stmt_id)
                        state = str(result.status.state)
                        if state == "SUCCEEDED":
                            print_result(f"WorkspaceClient ({label})", True, f"Async OK, statement_id={stmt_id}")
                            break
                        elif state in ["FAILED", "CANCELED", "CLOSED"]:
                            print_result(f"WorkspaceClient ({label})", False, f"Estado: {state}")
                            break
                        time.sleep(2)
                    else:
                        print_result(f"WorkspaceClient ({label})", False, "Timeout no polling")
                else:
                    # Verifica resultado direto
                    result = client.statement_execution.get_statement(response.statement_id)
                    state = str(result.status.state)
                    if state == "SUCCEEDED":
                        print_result(f"WorkspaceClient ({label})", True, f"Estado: {state}")
                    else:
                        print_result(f"WorkspaceClient ({label})", False, f"Estado: {state}")
            except Exception as e:
                print_result(f"WorkspaceClient ({label})", False, str(e))
        
        return True
    except ImportError:
        print_result("WorkspaceClient", False, "databricks-sdk não instalado")
        return False
    except Exception as e:
        print_result("WorkspaceClient", False, f"Erro geral: {e}")
        return False

# ============================================================
# TESTE 3: API REST (stateless puro)
# ============================================================
def test_rest_api():
    print_header("TESTE 3: API REST (stateless puro)")
    try:
        import requests
        headers = {
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
        }
        
        # Testa diferentes endpoints e payloads
        endpoints = [
            ("/api/2.0/sql/statements", "POST"),
            ("/api/2.0/sql/statements/execute", "POST"),  # síncrono
        ]
        
        queries = [
            ("SELECT 1", None, None, "JSON_ARRAY"),
            ("SELECT 1", CATALOG, SCHEMA, "JSON_ARRAY"),
            ("SELECT CAST(1 AS INT) AS valor", CATALOG, SCHEMA, "JSON_ARRAY"),
            ("SELECT 1", CATALOG, SCHEMA, "ARRAY"),
            ("SELECT COUNT(*) FROM plataforma.core_cliente.golden_record", CATALOG, SCHEMA, "JSON_ARRAY"),
        ]
        
        for endpoint, method in endpoints:
            for sql, cat, sch, fmt in queries:
                label = f"{endpoint} | {sql[:30]}..."
                try:
                    payload = {
                        "warehouse_id": WAREHOUSE_ID,
                        "statement": sql,
                        "catalog": cat,
                        "schema": sch,
                        "wait_timeout": 60,
                        "result_format": fmt,
                    }
                    url = f"{HOST}{endpoint}"
                    response = requests.post(url, headers=headers, json=payload, timeout=70)
                    if response.status_code == 200:
                        data = response.json()
                        if "statement_id" in data:
                            print_result(f"REST ({label})", True, f"Statement ID: {data['statement_id']}")
                        else:
                            print_result(f"REST ({label})", True, f"Resposta: {data}")
                    else:
                        print_result(f"REST ({label})", False, f"HTTP {response.status_code}: {response.text[:100]}")
                except Exception as e:
                    print_result(f"REST ({label})", False, str(e))
        
        return True
    except ImportError:
        print_result("API REST", False, "requests não instalado")
        return False

# ============================================================
# TESTE 4: Versões do databricks-sdk
# ============================================================
def test_sdk_versions():
    print_header("TESTE 4: Testando versões do databricks-sdk")
    versions = ["0.100.0", "0.110.0", "0.115.0", "0.120.0", "0.122.0"]
    
    current_version = None
    try:
        import databricks
        current_version = databricks.__version__
        print(f"Versão atual: {current_version}")
    except:
        print("databricks-sdk não instalado")
    
    for ver in versions:
        print(f"\n📦 Instalando databricks-sdk=={ver}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", f"databricks-sdk=={ver}", "--quiet"])
            # Recarrega o módulo
            import importlib
            import databricks.sdk
            importlib.reload(databricks.sdk)
            from databricks.sdk import WorkspaceClient
            
            client = WorkspaceClient()
            # Testa uma query simples
            response = client.statement_execution.execute_statement(
                warehouse_id=WAREHOUSE_ID,
                statement="SELECT 1",
                catalog=CATALOG,
                schema=SCHEMA,
                wait_timeout=60,
            )
            result = client.statement_execution.get_statement(response.statement_id)
            state = str(result.status.state)
            if state == "SUCCEEDED":
                print_result(f"SDK {ver}", True)
            else:
                print_result(f"SDK {ver}", False, f"Estado: {state}")
        except Exception as e:
            print_result(f"SDK {ver}", False, str(e))
    
    # Volta para a versão atual (opcional)
    if current_version:
        subprocess.check_call([sys.executable, "-m", "pip", "install", f"databricks-sdk=={current_version}", "--quiet"])
        print(f"\n↩️ Voltando para versão {current_version}")

# ============================================================
# TESTE 5: Cliente custom com requests e polling
# ============================================================
def test_custom_rest_client():
    print_header("TESTE 5: Cliente REST com polling manual")
    try:
        import requests
        headers = {
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
        }
        
        # 1. Executa a query
        payload = {
            "warehouse_id": WAREHOUSE_ID,
            "statement": "SELECT 1",
            "catalog": CATALOG,
            "schema": SCHEMA,
            "wait_timeout": 0,  # assíncrono
            "result_format": "JSON_ARRAY",
        }
        response = requests.post(
            f"{HOST}/api/2.0/sql/statements",
            headers=headers,
            json=payload,
            timeout=10,
        )
        if response.status_code != 200:
            print_result("REST custom (async)", False, f"HTTP {response.status_code}")
            return False
        
        data = response.json()
        stmt_id = data.get("statement_id")
        if not stmt_id:
            print_result("REST custom (async)", False, "Statement ID não retornado")
            return False
        
        # 2. Polling
        for _ in range(30):
            status_resp = requests.get(
                f"{HOST}/api/2.0/sql/statements/{stmt_id}",
                headers=headers,
            )
            if status_resp.status_code != 200:
                print_result("REST custom (async)", False, f"HTTP {status_resp.status_code}")
                return False
            status_data = status_resp.json()
            state = status_data.get("status", {}).get("state")
            if state == "SUCCEEDED":
                result = status_data.get("result", {}).get("data_array")
                print_result("REST custom (async)", True, f"Resultado: {result}")
                return True
            elif state in ["FAILED", "CANCELED", "CLOSED"]:
                error = status_data.get("status", {}).get("error")
                print_result("REST custom (async)", False, f"Estado: {state}, Erro: {error}")
                return False
            time.sleep(2)
        print_result("REST custom (async)", False, "Timeout no polling")
        return False
    except Exception as e:
        print_result("REST custom (async)", False, str(e))
        return False

# ============================================================
# FUNÇÃO PRINCIPAL
# ============================================================
def main():
    print("\n" + "=" * 70)
    print("  TESTE COMPLETO DE CONEXÃO DATABRICKS")
    print("=" * 70)
    print(f"Host: {HOST}")
    print(f"Warehouse ID: {WAREHOUSE_ID}")
    print(f"Catalog: {CATALOG}")
    print(f"Schema: {SCHEMA}")
    print(f"Token: {'***' + TOKEN[-4:] if TOKEN else 'NÃO DEFINIDO'}")
    print("=" * 70)
    
    # Verifica se as variáveis essenciais estão definidas
    if not all([HOST, TOKEN, WAREHOUSE_ID]):
        print("❌ Variáveis de ambiente incompletas. Verifique o .env")
        return
    
    # Executa os testes
    results = {}
    
    # 1. Connector (baseline)
    results["connector"] = test_connector()
    
    # 2. WorkspaceClient
    results["workspace"] = test_workspace_client()
    
    # 3. API REST
    results["rest"] = test_rest_api()
    
    # 4. Versões da SDK (opcional, demora mais)
    # Descomente se quiser testar versões
    results["sdk_versions"] = test_sdk_versions()
    
    # 5. Cliente REST custom
    results["custom_rest"] = test_custom_rest_client()
    
    # Resumo final
    print_header("RESUMO FINAL")
    for name, success in results.items():
        status = "✅" if success else "❌"
        print(f"{status} {name}")
    
    if results.get("connector"):
        print("\n✅ Conclusão: Use databricks-sql-connector para a conexão stateless.")
        print("   Ele é confiável, já testado e funciona no seu ambiente.")
    elif results.get("custom_rest"):
        print("\n✅ Conclusão: Use a API REST com polling manual.")
    else:
        print("\n❌ Nenhuma abordagem funcionou. Verifique:")
        print("   - Token tem permissões para SQL Warehouse?")
        print("   - Warehouse está em execução?")
        print("   - Rede/firewall permitindo acesso?")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()