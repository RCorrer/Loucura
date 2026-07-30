#!/usr/bin/env python3
"""
Teste dos endpoints do S1-BACK-06 (Versões, Histórico, Timeline).
Cria uma segmentação, gera histórico e valida os endpoints.
"""

import requests
import json
import time
import sys

BASE_URL = "http://localhost:8000/api"

print("\n" + "="*60)
print(" TESTE S1-BACK-06 – VERSÕES / HISTÓRICO / TIMELINE")
print("="*60)

# ============================================================
# 1. CRIAR SEGMENTAÇÃO
# ============================================================
print("\n1. Criando segmentação para teste...")
payload = {
    "nome": "Teste Timeline",
    "objetivo": "AQUISICAO",
    "owner": "admin",
    "publico_base_id": "pub_varejo",
    "regras_json": {
        "publico_base": "pub_varejo",
        "inclusao": {
            "operator": "AND",
            "rules": [
                {"campo_id": "renda_mensal", "op": ">", "value": 10000}
            ]
        }
    }
}
resp = requests.post(f"{BASE_URL}/segmentacoes", json=payload)
if resp.status_code != 200:
    print(f"❌ Falha ao criar: {resp.text}")
    sys.exit(1)
data = resp.json()
seg_id = data["seg_id"]
print(f"✅ Criada: {seg_id}")

# ============================================================
# 2. ATUALIZAR (gera nova versão)
# ============================================================
print("\n2. Atualizando (gera versão 2)...")
payload_update = {"descricao": "Versão atualizada para teste"}
resp = requests.put(f"{BASE_URL}/segmentacoes/{seg_id}", json=payload_update)
if resp.status_code != 200:
    print(f"❌ Falha ao atualizar: {resp.text}")
    sys.exit(1)
print("✅ Atualizada")

# ============================================================
# 3. CICLO DE VIDA (gera estados e execuções)
# ============================================================
print("\n3. Executando ciclo de vida...")

# Enviar para aprovação
resp = requests.post(f"{BASE_URL}/segmentacoes/{seg_id}/enviar-aprovacao")
if resp.status_code != 200:
    print(f"❌ Falha ao enviar para aprovação: {resp.text}")
    sys.exit(1)
print("   ✅ Enviado para aprovação")

# Aprovar
resp = requests.post(f"{BASE_URL}/segmentacoes/{seg_id}/aprovar", json={"aprovado": True})
if resp.status_code != 200:
    print(f"❌ Falha ao aprovar: {resp.text}")
    sys.exit(1)
print("   ✅ Aprovada")

# Ativar
resp = requests.post(f"{BASE_URL}/segmentacoes/{seg_id}/ativar")
if resp.status_code != 200:
    print(f"❌ Falha ao ativar: {resp.text}")
    sys.exit(1)
print("   ✅ Ativada")

# Executar (gerar execução)
resp = requests.post(f"{BASE_URL}/segmentacoes/{seg_id}/executar")
if resp.status_code != 200:
    print(f"❌ Falha ao executar: {resp.text}")
    sys.exit(1)
print("   ✅ Executada (1)")

# Executar novamente (gerar outra execução)
resp = requests.post(f"{BASE_URL}/segmentacoes/{seg_id}/executar")
if resp.status_code != 200:
    print(f"❌ Falha ao executar: {resp.text}")
    sys.exit(1)
print("   ✅ Executada (2)")

# Pausar (gera estado)
resp = requests.post(f"{BASE_URL}/segmentacoes/{seg_id}/pausar")
if resp.status_code != 200:
    print(f"❌ Falha ao pausar: {resp.text}")
    sys.exit(1)
print("   ✅ Pausada")

# Reativar (gera estado)
resp = requests.post(f"{BASE_URL}/segmentacoes/{seg_id}/reativar")
if resp.status_code != 200:
    print(f"❌ Falha ao reativar: {resp.text}")
    sys.exit(1)
print("   ✅ Reativada")

# Encerrar (gera estado)
resp = requests.post(f"{BASE_URL}/segmentacoes/{seg_id}/encerrar")
if resp.status_code != 200:
    print(f"❌ Falha ao encerrar: {resp.text}")
    sys.exit(1)
print("   ✅ Encerrada")

print("✅ Ciclo concluído.")

# ============================================================
# 4. TESTAR ENDPOINTS
# ============================================================

print("\n" + "="*60)
print("4. Testando endpoints do S1-BACK-06...")
print("="*60)

# 4.1 Versões
print("\n[4.1] GET /segmentacoes/{seg_id}/versoes")
resp = requests.get(f"{BASE_URL}/segmentacoes/{seg_id}/versoes")
if resp.status_code == 200:
    data = resp.json()
    print(f"✅ Status 200 – {len(data)} versões")
    for v in data[:3]:
        print(f"   - Versão {v.get('versao')} | {v.get('motivo')} | {v.get('alterado_por')}")
else:
    print(f"❌ Erro: {resp.status_code} – {resp.text}")

# 4.2 Versão específica
print("\n[4.2] GET /segmentacoes/{seg_id}/versoes/{versao}")
versao = 1
resp = requests.get(f"{BASE_URL}/segmentacoes/{seg_id}/versoes/{versao}")
if resp.status_code == 200:
    data = resp.json()
    print(f"✅ Versão {versao} – regras_json presente: {'regras_json' in data}")
else:
    print(f"❌ Erro: {resp.status_code} – {resp.text}")

# 4.3 Execuções
print("\n[4.3] GET /segmentacoes/{seg_id}/execucoes")
resp = requests.get(f"{BASE_URL}/segmentacoes/{seg_id}/execucoes")
if resp.status_code == 200:
    data = resp.json()
    print(f"✅ Status 200 – {len(data)} execuções")
    for e in data[:3]:
        print(f"   - {e.get('exec_id')} | {e.get('status')} | {e.get('qtd_clientes')}")
else:
    print(f"❌ Erro: {resp.status_code} – {resp.text}")

# 4.4 Estados (histórico de transições)
print("\n[4.4] GET /segmentacoes/{seg_id}/estados")
resp = requests.get(f"{BASE_URL}/segmentacoes/{seg_id}/estados")
if resp.status_code == 200:
    data = resp.json()
    print(f"✅ Status 200 – {len(data)} transições")
    for e in data[:5]:
        print(f"   - {e.get('estado_anterior')} → {e.get('estado_novo')} | {e.get('motivo')}")
else:
    print(f"❌ Erro: {resp.status_code} – {resp.text}")

# 4.5 Timeline (unificada)
print("\n[4.5] GET /segmentacoes/{seg_id}/timeline")
resp = requests.get(f"{BASE_URL}/segmentacoes/{seg_id}/timeline")
if resp.status_code == 200:
    data = resp.json()
    print(f"✅ Status 200 – {len(data)} eventos na timeline")
    for item in data[:5]:
        print(f"   - {item.get('data')} | {item.get('tipo')} | {item.get('descricao')}")
else:
    print(f"❌ Erro: {resp.status_code} – {resp.text}")

# ============================================================
# 5. LIMPEZA (opcional)
# ============================================================
print("\n" + "="*60)
print("5. Limpeza – arquivando segmentação...")
resp = requests.delete(f"{BASE_URL}/segmentacoes/{seg_id}")
if resp.status_code == 200:
    print("✅ Arquivada")
else:
    print(f"❌ Erro: {resp.text}")

print("\n" + "="*60)
print("✅ Testes S1-BACK-06 concluídos!")
print("="*60)