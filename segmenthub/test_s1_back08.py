#!/usr/bin/env python3
"""
Teste dos endpoints do S1-BACK-08 (Comentários / Notificações).
Cria uma segmentação, adiciona comentários com menções, valida listagem, edição e notificações.
"""

import requests
import json
import time
import sys

BASE_URL = "http://localhost:8000/api"

print("\n" + "="*60)
print(" TESTE S1-BACK-08 – COMENTÁRIOS / NOTIFICAÇÕES")
print("="*60)

# ============================================================
# 1. CRIAR SEGMENTAÇÃO
# ============================================================
print("\n1. Criando segmentação para teste...")
payload = {
    "nome": "Teste Comentários",
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
# 2. CRIAR COMENTÁRIOS
# ============================================================
print("\n2. Criando comentários...")

# 2.1 Primeiro comentário
comentario1 = {
    "texto": "Este é um comentário inicial sobre a segmentação.",
    "tipo": "geral"
}
resp = requests.post(f"{BASE_URL}/segmentacoes/{seg_id}/comentarios", json=comentario1)
if resp.status_code != 200:
    print(f"❌ Falha ao criar comentário 1: {resp.text}")
    sys.exit(1)
com1 = resp.json()
com1_id = com1.get("comentario_id")
print(f"   ✅ Comentário 1 criado: {com1_id}")

# 2.2 Segundo comentário (com menção)
comentario2 = {
    "texto": "@admin, precisamos revisar essa regra de renda.",
    "tipo": "geral",
    "mencoes": ["admin"]
}
resp = requests.post(f"{BASE_URL}/segmentacoes/{seg_id}/comentarios", json=comentario2)
if resp.status_code != 200:
    print(f"❌ Falha ao criar comentário 2: {resp.text}")
    sys.exit(1)
com2 = resp.json()
com2_id = com2.get("comentario_id")
print(f"   ✅ Comentário 2 criado (com menção): {com2_id}")

# 2.3 Resposta a um comentário (thread)
comentario3 = {
    "texto": "Concordo, vamos ajustar o valor mínimo para 15000.",
    "tipo": "resposta",
    "respondendo_a": com1_id
}
resp = requests.post(f"{BASE_URL}/segmentacoes/{seg_id}/comentarios", json=comentario3)
if resp.status_code != 200:
    print(f"❌ Falha ao criar comentário 3: {resp.text}")
    sys.exit(1)
com3 = resp.json()
com3_id = com3.get("comentario_id")
print(f"   ✅ Comentário 3 criado (resposta ao 1): {com3_id}")

# ============================================================
# 3. LISTAR COMENTÁRIOS (thread aninhada)
# ============================================================
print("\n3. Listando comentários (thread)...")
resp = requests.get(f"{BASE_URL}/segmentacoes/{seg_id}/comentarios")
if resp.status_code == 200:
    data = resp.json()
    print(f"✅ Status 200 – {len(data)} comentários")
    for c in data:
        respostas_count = len(c.get("respostas", []))
        print(f"   - {c.get('comentario_id')} | {c.get('texto')[:40]}... | respostas: {respostas_count}")
else:
    print(f"❌ Erro: {resp.status_code} – {resp.text}")

# ============================================================
# 4. EDITAR COMENTÁRIO (texto)
# ============================================================
print("\n4. Editando texto do comentário...")
payload_edit_texto = {
    "texto": "Este é um comentário inicial sobre a segmentação (editado)."
}
resp = requests.put(f"{BASE_URL}/comentarios/{com1_id}", json=payload_edit_texto)
if resp.status_code == 200:
    print(f"✅ Texto do comentário {com1_id} editado com sucesso")
else:
    print(f"❌ Erro ao editar texto: {resp.status_code} – {resp.text}")

# ============================================================
# 5. MARCAR COMENTÁRIO COMO RESOLVIDO
# ============================================================
print("\n5. Marcando comentário como resolvido...")
payload_resolve = {"resolvido": True}
resp = requests.put(f"{BASE_URL}/comentarios/{com1_id}", json=payload_resolve)
if resp.status_code == 200:
    print(f"✅ Comentário {com1_id} marcado como resolvido")
else:
    print(f"❌ Erro ao marcar resolvido: {resp.status_code} – {resp.text}")

# ============================================================
# 6. LISTAR NOTIFICAÇÕES (todas)
# ============================================================
print("\n6. Listando notificações...")
resp = requests.get(f"{BASE_URL}/notificacoes")
if resp.status_code == 200:
    data = resp.json()
    print(f"✅ Status 200 – {len(data)} notificações")
    for n in data[:5]:
        print(f"   - {n.get('notif_id')} | {n.get('titulo')} | lida: {n.get('lida')}")
else:
    print(f"❌ Erro: {resp.status_code} – {resp.text}")

# ============================================================
# 7. MARCAR NOTIFICAÇÃO COMO LIDA
# ============================================================
print("\n7. Marcando notificação como lida...")
resp_notif = requests.get(f"{BASE_URL}/notificacoes")
if resp_notif.status_code == 200:
    notifs = resp_notif.json()
    if notifs:
        notif_id = notifs[0].get("notif_id")
        resp = requests.put(f"{BASE_URL}/notificacoes/{notif_id}/lida")
        if resp.status_code == 200:
            print(f"✅ Notificação {notif_id} marcada como lida")
        else:
            print(f"❌ Erro ao marcar como lida: {resp.text}")
    else:
        print("   ℹ️ Nenhuma notificação para marcar")
else:
    print(f"❌ Erro ao listar notificações: {resp_notif.text}")

# ============================================================
# 8. VERIFICAR NOTIFICAÇÕES NÃO LIDAS
# ============================================================
print("\n8. Verificando notificações não lidas...")
resp = requests.get(f"{BASE_URL}/notificacoes?lida=false")
if resp.status_code == 200:
    data = resp.json()
    print(f"✅ Status 200 – {len(data)} notificações não lidas")
else:
    print(f"❌ Erro: {resp.status_code} – {resp.text}")

# ============================================================
# 9. LIMPEZA (arquivar segmentação)
# ============================================================
print("\n" + "="*60)
print("9. Limpeza – arquivando segmentação...")
resp = requests.delete(f"{BASE_URL}/segmentacoes/{seg_id}")
if resp.status_code == 200:
    print("✅ Arquivada")
else:
    print(f"❌ Erro: {resp.text}")

print("\n" + "="*60)
print("✅ Testes S1-BACK-08 concluídos!")
print("="*60)