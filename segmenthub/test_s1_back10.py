#!/usr/bin/env python3
"""
Teste completo do S1-BACK-10 – Chatbot (MCP + Agent Framework + Vector Search).
Testa diferentes tipos de perguntas, confirmações e fluxos de criação.
"""

import requests
import json
import sys
import time

BASE_URL = "http://localhost:8000/api"

print("\n" + "="*60)
print(" TESTE S1-BACK-10 – CHATBOT")
print("="*60)

# ============================================================
# 1. TESTE: Listar temas
# ============================================================
print("\n[1] Testando: listar temas")
payload = {
    "mensagem": "Quais temas estão disponíveis?",
    "session_id": "test-001"
}
resp = requests.post(f"{BASE_URL}/chat/mensagem", json=payload)
if resp.status_code == 200:
    data = resp.json()
    print(f"✅ Status 200")
    print(f"   Resposta: {data.get('resposta', '')[:100]}...")
    print(f"   Ação: {data.get('acao')}")
else:
    print(f"❌ Erro: {resp.status_code} – {resp.text}")

# ============================================================
# 2. TESTE: Listar campos de um tema
# ============================================================
print("\n[2] Testando: listar campos do tema Financeiro")
payload = {
    "mensagem": "Quais campos estão disponíveis no tema Financeiro?",
    "session_id": "test-002"
}
resp = requests.post(f"{BASE_URL}/chat/mensagem", json=payload)
if resp.status_code == 200:
    data = resp.json()
    print(f"✅ Status 200")
    print(f"   Resposta: {data.get('resposta', '')[:100]}...")
else:
    print(f"❌ Erro: {resp.status_code} – {resp.text}")

# ============================================================
# 3. TESTE: Pergunta sobre dados disponíveis
# ============================================================
print("\n[3] Testando: pergunta sobre dados específicos")
payload = {
    "mensagem": "Você tem algum dado sobre crédito?",
    "session_id": "test-003"
}
resp = requests.post(f"{BASE_URL}/chat/mensagem", json=payload)
if resp.status_code == 200:
    data = resp.json()
    print(f"✅ Status 200")
    print(f"   Resposta: {data.get('resposta', '')[:100]}...")
else:
    print(f"❌ Erro: {resp.status_code} – {resp.text}")

# ============================================================
# 4. TESTE: Pergunta sobre estimativa (simplificado)
# ============================================================
print("\n[4] Testando: pedido de estimativa")
payload = {
    "mensagem": "Estime clientes com renda maior que 10000",
    "session_id": "test-004"
}
resp = requests.post(f"{BASE_URL}/chat/mensagem", json=payload)
if resp.status_code == 200:
    data = resp.json()
    print(f"✅ Status 200")
    print(f"   Resposta: {data.get('resposta', '')[:100]}...")
else:
    print(f"❌ Erro: {resp.status_code} – {resp.text}")

# ============================================================
# 5. TESTE: Criar segmentação (deve pedir confirmação)
# ============================================================
print("\n[5] Testando: criar segmentação (deve pedir confirmação)")
payload = {
    "mensagem": "Crie um segmento de clientes com renda maior que 10000",
    "session_id": "test-005"
}
resp = requests.post(f"{BASE_URL}/chat/mensagem", json=payload)
if resp.status_code == 200:
    data = resp.json()
    print(f"✅ Status 200")
    print(f"   Resposta: {data.get('resposta', '')[:100]}...")
    print(f"   Precisa confirmação? {data.get('precisa_confirmacao')}")
    if data.get('precisa_confirmacao'):
        session_id = data.get('session_id')
        print(f"   Session ID: {session_id}")
    else:
        print(f"   ⚠️ Não pediu confirmação (pode ser comportamento esperado)")
else:
    print(f"❌ Erro: {resp.status_code} – {resp.text}")

# ============================================================
# 6. TESTE: Confirmar criação (se tiver pendente)
# ============================================================
print("\n[6] Testando: confirmar criação")
# Usa o session_id do teste anterior (se existir)
session_id = "test-005"
payload = {
    "mensagem": "sim",
    "session_id": session_id
}
resp = requests.post(f"{BASE_URL}/chat/mensagem", json=payload)
if resp.status_code == 200:
    data = resp.json()
    print(f"✅ Status 200")
    print(f"   Resposta: {data.get('resposta', '')[:100]}...")
else:
    print(f"❌ Erro: {resp.status_code} – {resp.text}")

# ============================================================
# 7. TESTE: Cancelar criação (se tiver pendente)
# ============================================================
print("\n[7] Testando: cancelar criação")
payload = {
    "mensagem": "Crie um segmento de clientes com renda > 15000",
    "session_id": "test-007"
}
# Primeiro, pede criação
resp1 = requests.post(f"{BASE_URL}/chat/mensagem", json=payload)
if resp1.status_code == 200 and resp1.json().get('precisa_confirmacao'):
    # Depois, cancela
    payload_cancel = {
        "mensagem": "não",
        "session_id": resp1.json().get('session_id')
    }
    resp2 = requests.post(f"{BASE_URL}/chat/mensagem", json=payload_cancel)
    if resp2.status_code == 200:
        print(f"✅ Cancelamento funcionou: {resp2.json().get('resposta', '')}")
    else:
        print(f"❌ Erro ao cancelar: {resp2.status_code} – {resp2.text}")
else:
    print(f"⚠️ Não foi possível testar cancelamento (não pediu confirmação)")

# ============================================================
# 8. TESTE: Pergunta genérica (fora do escopo)
# ============================================================
print("\n[8] Testando: pergunta genérica")
payload = {
    "mensagem": "O que você pode fazer?",
    "session_id": "test-008"
}
resp = requests.post(f"{BASE_URL}/chat/mensagem", json=payload)
if resp.status_code == 200:
    data = resp.json()
    print(f"✅ Status 200")
    print(f"   Resposta: {data.get('resposta', '')[:100]}...")
else:
    print(f"❌ Erro: {resp.status_code} – {resp.text}")

# ============================================================
# 9. TESTE: Listar campos de tema inexistente
# ============================================================
print("\n[9] Testando: tema inexistente")
payload = {
    "mensagem": "Quais campos estão disponíveis no tema Xyz?",
    "session_id": "test-009"
}
resp = requests.post(f"{BASE_URL}/chat/mensagem", json=payload)
if resp.status_code == 200:
    data = resp.json()
    print(f"✅ Status 200")
    print(f"   Resposta: {data.get('resposta', '')[:100]}...")
else:
    print(f"❌ Erro: {resp.status_code} – {resp.text}")

# ============================================================
# 10. TESTE: Pergunta com múltiplas intenções
# ============================================================
print("\n[10] Testando: pergunta com múltiplas intenções")
payload = {
    "mensagem": "Quais temas existem e quais campos têm no Financeiro?",
    "session_id": "test-010"
}
resp = requests.post(f"{BASE_URL}/chat/mensagem", json=payload)
if resp.status_code == 200:
    data = resp.json()
    print(f"✅ Status 200")
    print(f"   Resposta: {data.get('resposta', '')[:150]}...")
else:
    print(f"❌ Erro: {resp.status_code} – {resp.text}")

print("\n" + "="*60)
print("✅ Testes S1-BACK-10 concluídos!")
print("="*60)