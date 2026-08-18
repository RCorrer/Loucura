# S1 - SegmentHub

API de gestão de segmentações (FastAPI + React).

---

## Pré-requisitos

| Ferramenta | Versão mínima |
|------------|---------------|
| Python | 3.10+ |
| Node.js | 18+ |
| npm | 9+ |

---

## Execução Local (sem Databricks)

O projeto suporta um **banco SQLite fake** que simula todas as tabelas do Unity Catalog.
Você não precisa de acesso ao Databricks para desenvolver localmente.

### 1. Clone e entre na pasta

```bash
cd segmenthub
```

### 2. Crie o ambiente virtual

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou
.venv\Scripts\activate     # Windows
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Configure o `.env`

```bash
cp .env.example .env
```

Para rodar **local**, a única variável obrigatória é:

```env
ENV=local
```

Isso faz o sistema usar SQLite em vez do Databricks SQL Warehouse.

### 5. (Opcional) Gere/resete o banco fake manualmente

O banco é criado automaticamente no primeiro request, mas você pode forçar a criação:

```bash
python -m src.db.seed
```

Isso cria `src/db/local.db` com dados fictícios alinhados.

### 6. Suba o backend

```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

A API estará disponível em: `http://localhost:8000`

### 7. (Opcional) Suba o frontend em modo dev

```bash
cd frontend
npm install
npm run dev
```

O frontend roda em `http://localhost:5173` e faz proxy para a API na porta 8000.

---

## Execução no Databricks (Produção)

Para rodar conectado ao Databricks SQL Warehouse:

### `.env` para produção

```env
ENV=production
DATABRICKS_HOST=adb-xxxx.azuredatabricks.net
DATABRICKS_WAREHOUSE_ID=seu_warehouse_id
UC_CATALOG=plataforma
UC_SCHEMA=default
LOG_LEVEL=INFO
```

A autenticação é feita via `databricks-sdk Config()` (OAuth/token automático no Databricks Apps).

### Deploy como Databricks App

O deploy é configurado via `app.yaml`. As variáveis de ambiente são definidas lá.

---

## Como funciona o Fake DB

### Arquitetura

```
src/db/
├── databricks_client.py   ← Client real + get_client() router
├── fake_client.py         ← SQLite client (mesma interface)
├── seed.py                ← Script de criação + dados fictícios
└── local.db               ← Banco SQLite (gitignored, criado auto)
```

### Roteamento automático

A função `get_client()` decide qual client usar:

```python
if os.getenv("ENV") == "local":
    return FakeSQLiteClient()   # SQLite
else:
    return DatabricksSQLClient() # Databricks
```

**Nenhum código de repository, service ou API precisa mudar.**

### Normalização de SQL

O `FakeSQLiteClient` normaliza automaticamente:

| Databricks SQL | SQLite equivalente |
|----------------|-------------------|
| `plataforma.segmentacao.tabela` | `tabela` |
| `plataforma.metadata.tabela` | `tabela` |
| `current_timestamp()` | `datetime('now')` |
| `approx_count_distinct(x)` | `COUNT(DISTINCT x)` |

### Dados seed

O script `seed.py` cria dados **consistentes entre si**:

| Tabela | Dados |
|--------|-------|
| `catalogo_caracteristicas` | 14 campos (idade, renda, uf, score...) |
| `catalogo_publicos` | 2 públicos (PF Geral, PJ Geral) |
| `customer_features_wide` | 20 PFs + 5 PJs com features aleatórias |
| `pf_geral` / `pj_geral` | CPFs/CNPJs que batem com features |
| `seg_definicao` | 3 segmentações (ativa, ativa, rascunho) |
| `seg_saude` | Saúde das 3 segmentações (verde, amarelo, vermelho) |
| `seg_comentario` | 3 comentários |
| `seg_notificacao` | 2 notificações |
| `seg_execucao` | 4 execuções (histórico) |
| `seg_job_log` | 3 logs de job |

**Alinhamento chave:**
- `catalogo_publicos.publico_id` = nome da tabela em `publico.*` = `seg_definicao.publico_base_id`
- `catalogo_caracteristicas.caracteristica_id` = colunas de `customer_features_wide` = `campo_id` nas regras JSON
- `customer_features_wide.cpf_cnpj` = `pf_geral.cpf_cnpj` (JOIN funciona)

---

## Resetar o banco local

Se quiser recomeçar do zero:

```bash
rm src/db/local.db
python -m src.db.seed
```

Ou simplesmente delete o arquivo — ele será recriado no próximo request.

---

## Endpoints úteis para debug

| Rota | Função |
|------|--------|
| `GET /health` | Health check |
| `GET /api/test-db` | Testa conexão com o banco |
| `GET /api/me` | Retorna usuário atual |
| `GET /api/debug-headers` | Mostra headers da requisição |

---

## Limitações do modo local

| Feature | Status no modo local |
|---------|---------------------|
| CRUD segmentações | ✅ Funciona |
| Estimativa de público | ✅ Funciona (COUNT DISTINCT) |
| Catálogo/metadata | ✅ Funciona |
| Comentários/notificações | ✅ Funciona |
| Saúde | ✅ Funciona (dados seed) |
| Jobs (criar/pausar/ativar) | ❌ Requer Databricks SDK |
| Chat IA | ❌ Requer LLM endpoint |
| Security (OBO) | ❌ Headers não presentes |

Para testar endpoints protegidos localmente, você pode desabilitar o middleware de segurança ou mockar os headers.

---

## Estrutura de pastas

```
segmenthub/
├── .env.example           ← Template de variáveis
├── .env                   ← Seu .env local (gitignored)
├── app.yaml               ← Config Databricks App
├── requirements.txt
├── src/
│   ├── main.py            ← FastAPI app
│   ├── api/               ← Routers (endpoints)
│   ├── services/          ← Lógica de negócio
│   ├── core/              ← Infra (config, security, query_engine)
│   ├── models/            ← Pydantic models
│   ├── repositories/      ← Acesso a dados
│   ├── db/
│   │   ├── databricks_client.py  ← Client real + router
│   │   ├── fake_client.py        ← Client SQLite
│   │   ├── seed.py               ← Dados fictícios
│   │   └── local.db              ← Banco (auto-criado)
│   └── exceptions/
└── frontend/
    └── src/
```

---

## Troubleshooting

### Erro: `DATABRICKS_WAREHOUSE_ID não definido`

Você está rodando sem `ENV=local`. Adicione `ENV=local` no `.env`.

### Erro: `no such table: seg_definicao`

O banco não foi criado. Execute:
```bash
python -m src.db.seed
```

### Erro: `no such function: approx_count_distinct`

O `FakeSQLiteClient` já converte `approx_count_distinct()` para `COUNT(DISTINCT)`. Se você ver esse erro, pode ser uma query que não está passando pelo `fake_client`. Verifique se está usando `get_client()` e não instanciando `DatabricksSQLClient` diretamente.

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
