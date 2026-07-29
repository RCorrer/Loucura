#!/usr/bin/env python3
"""
Teste do módulo security.py (RBAC).
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Define DEV_USER para teste (se não estiver no .env)
if not os.getenv("DEV_USER"):
    os.environ["DEV_USER"] = "admin"

# Importa o módulo security (já corrigido)
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from src.core.security import get_current_user, require_perfil, get_user_or_raise

# Cria app FastAPI de teste
app = FastAPI()

@app.get("/test-user")
async def test_user(user: dict = Depends(get_current_user)):
    return {"user": user}

@app.get("/test-admin")
async def test_admin(user: dict = Depends(require_perfil(["admin"]))):
    return {"message": "Acesso admin liberado!", "user": user}

@app.get("/test-analista")
async def test_analista(user: dict = Depends(require_perfil(["analista"]))):
    return {"message": "Acesso analista liberado!", "user": user}

@app.get("/test-multiplo")
async def test_multiplo(user: dict = Depends(require_perfil(["admin", "gerente"]))):
    return {"message": "Acesso múltiplo liberado!", "user": user}

@app.get("/test-user-or-raise")
async def test_user_or_raise(user: dict = Depends(get_user_or_raise)):
    return {"user": user}


def test_security():
    print("=" * 60)
    print("  TESTE DO MÓDULO SECURITY (RBAC)")
    print("=" * 60)
    print(f"DEV_USER: {os.getenv('DEV_USER')}")
    print("=" * 60)
    
    client = TestClient(app)
    
    # 1. get_current_user
    print("\n[1] Testando get_current_user...")
    response = client.get("/test-user")
    if response.status_code == 200:
        print("✅ get_current_user OK")
        print(f"   Usuário retornado: {response.json()}")
    else:
        print(f"❌ get_current_user falhou: {response.status_code} - {response.text}")
        return
    
    # 2. Admin
    print("\n[2] Testando require_perfil(['admin'])...")
    response = client.get("/test-admin")
    if response.status_code == 200:
        print("✅ Admin autorizado!")
        print(f"   Resposta: {response.json()}")
    else:
        print(f"❌ Admin NÃO autorizado: {response.status_code} - {response.text}")
    
    # 3. Analista (deve falhar)
    print("\n[3] Testando require_perfil(['analista'])...")
    response = client.get("/test-analista")
    if response.status_code == 403:
        print("✅ Analista NEGADO (esperado)!")
    else:
        print(f"⚠️ Analista inesperado: {response.status_code} - {response.text}")
    
    # 4. Múltiplos perfis
    print("\n[4] Testando require_perfil(['admin', 'gerente'])...")
    response = client.get("/test-multiplo")
    if response.status_code == 200:
        print("✅ Múltiplos perfis OK (admin está na lista)!")
    else:
        print(f"❌ Falha: {response.status_code} - {response.text}")
    
    # 5. get_user_or_raise
    print("\n[5] Testando get_user_or_raise...")
    response = client.get("/test-user-or-raise")
    if response.status_code == 200:
        print("✅ get_user_or_raise OK")
    else:
        print(f"❌ Falha: {response.status_code} - {response.text}")
    
    print("\n" + "=" * 60)
    print("  FIM DOS TESTES")
    print("=" * 60)


if __name__ == "__main__":
    test_security()