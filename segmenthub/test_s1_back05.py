#!/usr/bin/env python3
"""
Teste completo dos endpoints do S1-BACK-05 (CRUD + ciclo de vida).
Executa em sequência e exibe os resultados.
"""

import requests
import json
import time
import sys

BASE_URL = "http://localhost:8000/api"

# ============================================================
# 1. CRIAR SEGMENTAÇÃO
# ============================================================
print("\n" + "="*60)
print("1. Criando segmentação...")
print("="*60)

payload = {
    "nome": "Alta Renda Varejo",
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
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    print(f"✅ Criada: {data}")
    seg_id = data.get("seg_id")
    seg_codigo = data.get("seg_codigo")
else:
    print(f"❌ Erro: {resp.text}")
    sys.exit(1)

# ============================================================
# 2. LISTAR SEGMENTAÇÕES
# ============================================================
print("\n" + "="*60)
print("2. Listando segmentações...")
print("="*60)

resp = requests.get(f"{BASE_URL}/segmentacoes")
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    print(f"✅ Total: {data.get('meta', {}).get('total', 0)}")
    for item in data.get("data", [])[:3]:
        print(f"   - {item['seg_codigo']} | {item['nome']} | {item['status']}")
else:
    print(f"❌ Erro: {resp.text}")

# ============================================================
# 3. BUSCAR DETALHE DA SEGMENTAÇÃO CRIADA
# ============================================================
print("\n" + "="*60)
print(f"3. Buscando detalhe de {seg_id}...")
print("="*60)

resp = requests.get(f"{BASE_URL}/segmentacoes/{seg_id}")
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    print(f"✅ Nome: {data.get('nome')}")
    print(f"   Status: {data.get('status')}")
    print(f"   Versão: {data.get('versao_atual')}")
    print(f"   Público base: {data.get('publico_base_id')}")
else:
    print(f"❌ Erro: {resp.text}")

# ============================================================
# 4. ATUALIZAR SEGMENTAÇÃO
# ============================================================
print("\n" + "="*60)
print("4. Atualizando segmentação...")
print("="*60)

payload_update = {
    "descricao": "Segmentação de alta renda para ofertas exclusivas",
    "seg_tags": ["alta-renda", "varejo", "cross-sell"],
}
resp = requests.put(f"{BASE_URL}/segmentacoes/{seg_id}", json=payload_update)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    print("✅ Atualizada com sucesso")
else:
    print(f"❌ Erro: {resp.text}")

# ============================================================
# 5. VALIDAR SEGMENTAÇÃO
# ============================================================
print("\n" + "="*60)
print("5. Validando segmentação...")
print("="*60)

resp = requests.post(f"{BASE_URL}/segmentacoes/{seg_id}/validar")
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    print(f"✅ Válido: {data.get('valido')}")
    if data.get('erros'):
        print(f"   Erros: {data['erros']}")
else:
    print(f"❌ Erro: {resp.text}")

# ============================================================
# 5.5 ENVIAR PARA APROVAÇÃO
# ============================================================
print("\n" + "="*60)
print("5.5 Enviando para aprovação...")
print("="*60)

resp = requests.post(f"{BASE_URL}/segmentacoes/{seg_id}/enviar-aprovacao")
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    print("✅ Enviado para aprovação")
else:
    print(f"❌ Erro: {resp.text}")
    # Se falhar, não adianta continuar
    sys.exit(1)

# ============================================================
# 6. APROVAR SEGMENTAÇÃO (admin)
# ============================================================
print("\n" + "="*60)
print("6. Aprovando segmentação (admin)...")
print("="*60)

checklist = {"aprovado": True, "comentario": "Tudo ok"}
resp = requests.post(f"{BASE_URL}/segmentacoes/{seg_id}/aprovar", json=checklist)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    print("✅ Aprovada com sucesso")
else:
    print(f"❌ Erro: {resp.text}")
    sys.exit(1)

# ============================================================
# 7. ATIVAR SEGMENTAÇÃO
# ============================================================
print("\n" + "="*60)
print("7. Ativando segmentação...")
print("="*60)

resp = requests.post(f"{BASE_URL}/segmentacoes/{seg_id}/ativar")
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    print("✅ Ativada com sucesso")
else:
    print(f"❌ Erro: {resp.text}")
    sys.exit(1)

# ============================================================
# 8. EXECUTAR SEGMENTAÇÃO (manual)
# ============================================================
print("\n" + "="*60)
print("8. Executando segmentação manualmente...")
print("="*60)

resp = requests.post(f"{BASE_URL}/segmentacoes/{seg_id}/executar")
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    print(f"✅ Exec_id: {data.get('exec_id')}")
else:
    print(f"❌ Erro: {resp.text}")

# ============================================================
# 9. PAUSAR SEGMENTAÇÃO
# ============================================================
print("\n" + "="*60)
print("9. Pausando segmentação...")
print("="*60)

resp = requests.post(f"{BASE_URL}/segmentacoes/{seg_id}/pausar")
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    print("✅ Pausada com sucesso")
else:
    print(f"❌ Erro: {resp.text}")

# ============================================================
# 10. REATIVAR SEGMENTAÇÃO
# ============================================================
print("\n" + "="*60)
print("10. Reativando segmentação...")
print("="*60)

resp = requests.post(f"{BASE_URL}/segmentacoes/{seg_id}/reativar")
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    print("✅ Reativada com sucesso")
else:
    print(f"❌ Erro: {resp.text}")

# ============================================================
# 11. ENCERRAR SEGMENTAÇÃO
# ============================================================
print("\n" + "="*60)
print("11. Encerrando segmentação...")
print("="*60)

resp = requests.post(f"{BASE_URL}/segmentacoes/{seg_id}/encerrar")
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    print("✅ Encerrada com sucesso")
else:
    print(f"❌ Erro: {resp.text}")

# ============================================================
# 12. CLONAR SEGMENTAÇÃO
# ============================================================
print("\n" + "="*60)
print("12. Clonando segmentação...")
print("="*60)

clone_data = {
    "nome": "Alta Renda Varejo (Clone)",
    "owner": "admin"
}
resp = requests.post(f"{BASE_URL}/segmentacoes/{seg_id}/clonar", json=clone_data)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    print(f"✅ Clone criado: {data.get('seg_id')}")
    clone_id = data.get("seg_id")
else:
    print(f"❌ Erro: {resp.text}")
    clone_id = None

# ============================================================
# 13. DESTINOS
# ============================================================
print("\n" + "="*60)
print("13. Configurando destinos...")
print("="*60)

destinos = [
    {"destino": "sistema2", "habilitado": True},
    {"destino": "sistema3", "habilitado": True},
]
resp = requests.put(f"{BASE_URL}/segmentacoes/{seg_id}/destinos", json=destinos)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    print("✅ Destinos configurados")
else:
    print(f"❌ Erro: {resp.text}")

# ============================================================
# 14. ARQUIVAR SEGMENTAÇÃO (soft delete)
# ============================================================
print("\n" + "="*60)
print("14. Arquivando segmentação...")
print("="*60)

resp = requests.delete(f"{BASE_URL}/segmentacoes/{seg_id}")
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    print("✅ Arquivada com sucesso")
else:
    print(f"❌ Erro: {resp.text}")

# ============================================================
# 15. LIMPEZA (opcional) - deletar clone
# ============================================================
if clone_id:
    print("\n" + "="*60)
    print("15. Removendo clone (limpeza)...")
    print("="*60)
    resp = requests.delete(f"{BASE_URL}/segmentacoes/{clone_id}")
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        print("✅ Clone removido")
    else:
        print(f"❌ Erro: {resp.text}")

print("\n" + "="*60)
print("✅ Testes concluídos!")
print("="*60)