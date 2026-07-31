#!/usr/bin/env python3
"""
Teste dos endpoints do S1-BACK-11 (Governança de Catálogo).
Testa listagem, atualização de flags/status e histórico.
"""

import requests
import sys
import json

BASE_URL = "http://localhost:8000/api"

print("\n" + "="*60)
print(" TESTE S1-BACK-11 – GOVERNANÇA DE CATÁLOGO")
print("="*60)

# ============================================================
# 1. LISTAR CAMPOS (admin)
# ============================================================
print("\n1. Listando campos (admin)...")
resp = requests.get(f"{BASE_URL}/metadata/admin/campos")
if resp.status_code == 200:
    data = resp.json()
    print(f"✅ Status 200 – Total: {data['meta']['total']}")
    if data['data']:
        campo = data['data'][0]
        print(f"   Exemplo: {campo['campo_label']} | ativo: {campo['ativo']} | S2: {campo['usavel_em_visao360']} | S3: {campo['usavel_em_peca']}")
        campo_id = campo['caracteristica_id']
    else:
        print("   Nenhuma característica encontrada")
        sys.exit(1)
else:
    print(f"❌ Erro: {resp.status_code} – {resp.text}")
    sys.exit(1)

# ============================================================
# 2. OBTER DETALHE DE UM CAMPO
# ============================================================
print(f"\n2. Obtendo detalhe de {campo_id}...")
resp = requests.get(f"{BASE_URL}/metadata/admin/campos/{campo_id}")
if resp.status_code == 200:
    data = resp.json()
    print(f"✅ Status 200 – {data['campo_label']} | Bloco: {data.get('bloco_visao360')}")
else:
    print(f"❌ Erro: {resp.status_code} – {resp.text}")

# ============================================================
# 3. ALTERAR FLAGS (S2)
# ============================================================
print("\n3. Alterando flag S2 (toggle)...")
# Pega o valor atual e inverte
campo_atual = requests.get(f"{BASE_URL}/metadata/admin/campos/{campo_id}").json()
novo_s2 = not campo_atual.get('usavel_em_visao360', False)

payload = {"usavel_em_visao360": novo_s2}
resp = requests.put(f"{BASE_URL}/metadata/admin/campos/{campo_id}/flags", json=payload)
if resp.status_code == 200:
    data = resp.json()
    print(f"✅ Status 200 – Alterações: {data['alteracoes']}")
else:
    print(f"❌ Erro: {resp.status_code} – {resp.text}")

# ============================================================
# 4. VERIFICAR HISTÓRICO GERAL
# ============================================================
print("\n4. Verificando histórico geral...")
resp = requests.get(f"{BASE_URL}/metadata/admin/historico")
if resp.status_code == 200:
    data = resp.json()
    print(f"✅ Status 200 – Total: {data['meta']['total']}")
    if data['data']:
        hist = data['data'][0]
        print(f"   Exemplo: {hist['campo_label']} | {hist['acao']} | {hist['alterado_por']} | {hist['alterado_em']}")
    else:
        print("   Nenhum histórico encontrado")
else:
    print(f"❌ Erro: {resp.status_code} – {resp.text}")

# ============================================================
# 5. HISTÓRICO POR CARACTERÍSTICA
# ============================================================
print(f"\n5. Histórico da característica {campo_id}...")
resp = requests.get(f"{BASE_URL}/metadata/admin/campos/{campo_id}/historico")
if resp.status_code == 200:
    data = resp.json()
    print(f"✅ Status 200 – Total: {data['meta']['total']}")
else:
    print(f"❌ Erro: {resp.status_code} – {resp.text}")

# ============================================================
# 6. FILTROS NO HISTÓRICO
# ============================================================
print("\n6. Testando filtros no histórico (sistema_alvo=s2)...")
resp = requests.get(f"{BASE_URL}/metadata/admin/historico?sistema_alvo=s2")
if resp.status_code == 200:
    data = resp.json()
    print(f"✅ Status 200 – Total com s2: {data['meta']['total']}")
else:
    print(f"❌ Erro: {resp.status_code} – {resp.text}")

print("\n" + "="*60)
print("✅ Testes S1-BACK-11 concluídos!")
print("="*60)