# S1 - SegmentHub

API de gestão de segmentações (FastAPI + React). Roda como **Databricks App** conectado ao SQL Warehouse via Unity Catalog.

---

## Pré-requisitos

| Ferramenta | Versão mínima |
|------------|---------------|
| Python | 3.10+ |
| Node.js | 18+ |
| npm | 9+ |
| Databricks SQL Warehouse | Serverless + Photon |

---

## Configuração

### Variáveis de ambiente (`.env` ou `app.yaml`)

```env
DATABRICKS_HOST=adb-xxxx.azuredatabricks.net
DATABRICKS_WAREHOUSE_ID=seu_warehouse_id
UC_CATALOG=plataforma
UC_SCHEMA=default
LOG_LEVEL=INFO
```

A autenticação é feita via `databricks-sdk Config()` (OAuth/token automático no Databricks Apps).

---

## Deploy como Databricks App

```bash
cd segmenthub
pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

O deploy é configurado via `app.yaml`. As variáveis de ambiente são definidas lá.

---

## Endpoints úteis para debug

| Rota | Função |
|------|--------|
| `GET /health` | Health check |
| `GET /api/test-db` | Testa conexão com o warehouse |
| `GET /api/me` | Retorna usuário atual |
| `GET /api/debug-headers` | Mostra headers da requisição |

---

## Estrutura de pastas

```
segmenthub/
├── app.yaml               ← Config Databricks App
├── requirements.txt
├── src/
│   ├── main.py            ← FastAPI app + routers + SPA fallback
│   ├── api/               ← Routers (endpoints)
│   ├── services/          ← Lógica de negócio
│   ├── core/              ← Infra (config, security, query_engine)
│   ├── models/            ← Pydantic models
│   ├── repositories/      ← Acesso a dados (SQL parametrizado)
│   ├── db/
│   │   └── databricks_client.py  ← SQL Warehouse client (SDK)
│   └── exceptions/
└── frontend/
    └── src/
```

---

## Troubleshooting

### Erro: `DATABRICKS_WAREHOUSE_ID não definido`

Configure a variável de ambiente no `app.yaml` ou `.env`.

### Frontend não conecta na API

Verifique o `vite.config.js` — o proxy deve apontar para `http://localhost:8000`.

---

## 📚 Documentação Completa

A documentação técnica completa está em `/doc/`:

1. **[01-VISAO-GERAL.md](./doc/01-VISAO-GERAL.md)** — Conceitos, objetivos e arquitetura geral
2. **[02-SCHEMAS-TABELAS.md](./doc/02-SCHEMAS-TABELAS.md)** — Estrutura das tabelas do Unity Catalog
3. **[03-ARQUITETURA-BACKEND.md](./doc/03-ARQUITETURA-BACKEND.md)** — Camadas, serviços e validações
4. **[04-CICLO-VIDA-ESTADOS.md](./doc/04-CICLO-VIDA-ESTADOS.md)** — Estados de segmentação (rascunho → aprovada → ativa)
5. **[05-JOBS-EXECUCAO.md](./doc/05-JOBS-EXECUCAO.md)** — Processamento Spark e materialização
6. **[06-API-ENDPOINTS.md](./doc/06-API-ENDPOINTS.md)** — Referência completa da API REST
7. **[07-INTEGRACAO-CONTRATOS.md](./doc/07-INTEGRACAO-CONTRATOS.md)** — Engines (seg_exec vs query_engine)
8. **[08-SEGURANCA-RBAC.md](./doc/08-SEGURANCA-RBAC.md)** — Autenticação e autorização
9. **[09-FLUXOS-SISTEMA.md](./doc/09-FLUXOS-SISTEMA.md)** — Workflows completos ponta-a-ponta
10. **[10-OPERADORES-SISTEMA.md](./doc/10-OPERADORES-SISTEMA.md)** — **NOVO!** Sistema de operadores (17 operadores, case-insensitive)

### 🆕 Novidades v1.2.0

**Sistema de Operadores Expandido:**
* **17 operadores disponíveis** (vs 11 anteriormente)
* **Case-insensitive** para campos string ("paulo" encontra "Paulo", "PAULO", "São Paulo")
* **Novos operadores de texto:** `ends_with`, `not_contains`, `not_starts_with`, `not_ends_with`
* **Documentação completa:** [10-OPERADORES-SISTEMA.md](./doc/10-OPERADORES-SISTEMA.md)

**Operadores por categoria:**
* Comparação numérica: `=`, `!=`, `>`, `<`, `>=`, `<=`
* Ranges e listas: `between`, `in`, `not_in`
* Texto: `contains`, `not_contains`, `starts_with`, `ends_with`, `not_starts_with`, `not_ends_with`
* Nulidade: `is_null`, `is_not_null`
