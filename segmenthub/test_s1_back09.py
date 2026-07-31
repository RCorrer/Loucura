#!/usr/bin/env python3
"""
Teste dos endpoints do S1-BACK-09 (Saúde / Overlap).
Cria uma segmentação, executa ciclo e valida os endpoints.
"""

import requests
import sys

BASE_URL = "http://localhost:8000/api"

print("\n" + "="*60)
print(" TESTE S1-BACK-09 – SAÚDE / OVERLAP")
print("="*60)

# ============================================================
# 1. CRIAR SEGMENTAÇÃO (para gerar um seg_id)
# ============================================================
print("\n1. Criando segmentação para teste...")
payload = {
    "nome": "Teste Saúde",
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
# 2. TESTAR DASHBOARD
# ============================================================
print("\n2. Dashboard de saúde...")
resp = requests.get(f"{BASE_URL}/saude")
if resp.status_code == 200:
    data = resp.json()
    print(f"✅ Status 200")
    print(f"   Total: {data.get('total_segmentacoes')}")
    print(f"   Verde: {data.get('verde')} | Amarelo: {data.get('amarelo')} | Vermelho: {data.get('vermelho')} | Sem dados: {data.get('sem_dados')}")
    print(f"   Última atualização: {data.get('ultima_atualizacao')}")
else:
    print(f"❌ Erro: {resp.status_code} – {resp.text}")

# ============================================================
# 3. TESTAR SAÚDE POR SEGMENTO
# ============================================================
print(f"\n3. Saúde detalhada de {seg_id}...")
resp = requests.get(f"{BASE_URL}/saude/{seg_id}")
if resp.status_code == 200:
    data = resp.json()
    print(f"✅ Status 200")
    print(f"   Status: {data.get('health_status')}")
    print(f"   Público atual: {data.get('publico_atual')}")
    print(f"   Variação: {data.get('variacao_publico_pct')}")
    print(f"   Taxa sucesso: {data.get('taxa_sucesso_exec')}")
else:
    print(f"❌ Erro: {resp.status_code} – {resp.text}")
    # Se for 404, é esperado se não houver dados de saúde ainda

# ============================================================
# 4. TESTAR OVERLAP
# ============================================================
print(f"\n4. Overlaps de {seg_id}...")
resp = requests.get(f"{BASE_URL}/saude/{seg_id}/overlap")
if resp.status_code == 200:
    data = resp.json()
    print(f"✅ Status 200")
    print(f"   Segmento: {data.get('seg_id')}")
    print(f"   Qtd overlaps: {len(data.get('overlaps', []))}")
    for o in data.get('overlaps', [])[:3]:
        print(f"   - com {o.get('seg_id_b')} | em comum: {o.get('clientes_em_comum')}")
else:
    print(f"❌ Erro: {resp.status_code} – {resp.text}")

# ============================================================
# 5. TESTAR DASHBOARD NOVAMENTE (após possível inserção de dados)
# ============================================================
print("\n5. Verificando dashboard novamente...")
resp = requests.get(f"{BASE_URL}/saude")
if resp.status_code == 200:
    data = resp.json()
    print(f"✅ Status 200 – total: {data.get('total_segmentacoes')}")
else:
    print(f"❌ Erro: {resp.status_code} – {resp.text}")

# ============================================================
# 6. LIMPEZA (arquivar segmentação)
# ============================================================
print("\n" + "="*60)
print("6. Limpeza – arquivando segmentação...")
resp = requests.delete(f"{BASE_URL}/segmentacoes/{seg_id}")
if resp.status_code == 200:
    print("✅ Arquivada")
else:
    print(f"❌ Erro: {resp.text}")

print("\n" + "="*60)
print("✅ Testes S1-BACK-09 concluídos!")
print("="*60)