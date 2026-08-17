# Arquitetura Backend — SegmentHub

> Padrões, camadas e módulos core do backend FastAPI.

---

## 1. Arquitetura em Camadas

```
  ┌───────────────┐    ┌──────────────────┐    ┌──────────────────┐    ┌─────────────────┐
  │  API LAYER    │    │  SERVICE LAYER   │    │  REPOSITORY LYR  │    │  DATA           │
  │               │    │                  │    │                  │    │                 │
  │ metadata      │    │ MetadataService  │    │ metadata_repo    │    │ DatabricksSQL-  │
  │ segmentacao   │───▶│ SegmentacaoSvc   │───▶│ segmentacao_repo │───▶│ Client          │
  │ estimativa    │    │ EstimativaService│    │ estimativa_repo  │    │                 │
  │ comentario    │    │ ComentarioSvc    │    │ comentario_repo  │    │ WorkspaceClient │
  │ saude         │    │ SaudeService     │    │ saude_repo       │    │ (Jobs SDK)      │
  │ metadata_admin│    │ MetadataAdminSvc │    │ metadata_admin   │    │                 │
  │ chat          │    │ ChatService      │    └──────────────────┘    └─────────────────┘
  └───────────────┘    │ JobManagerSvc    │
                        │                  │
                        └─────────┬────────┘
                                 │
                        ┌────────┴───────┐
                        │    CORE         │
                        │                 │
                        │ security.py     │
                        │ query_engine.py │
                        │ validator.py    │
                        │ config.py       │
                        │ llm_client.py   │
                        └─────────────────┘
```

---

## 2. Responsabilidades por Camada

| Camada | Responsabilidade | Padrão |
|---|---|---|
| **API** | Roteamento, validação HTTP, serialização, RBAC | FastAPI Router + Depends |
| **Service** | Lógica de negócio, orquestração, regras de transição | Classes Python |
| **Repository** | SQL parametrizado, mapeamento dados → dicts | DatabricksSQLClient |
| **Core** | Módulos transversais (security, engine, validator) | Utilitários injetados |
| **Models** | Schemas Pydantic v2 (request/response/interno) | BaseModel, DTOs |
| **DB** | Conexão ao SQL Warehouse via SDK | Singleton pattern |

---

## 3. Módulo Core: QueryEngine

Converte `regras_json` (estrutura em árvore) em SQL parametrizado.

```
  RegrasJson (entrada)
       │
       ▼
  ┌─────────────────────────────┐
  │ Parse inclusao / exclusao  │
  └─────────────┬───────────────┘
              │
       ┌──────┴──────┐
       ▼              ▼
  Build Árvore     Build Árvore
  Inclusão         Exclusão
       │              │
       ▼              ▼
  WHERE (incl.)   AND (excl.)
       │              │
       └──────┬───────┘
              ▼
  SELECT cpf_cnpj
  FROM publico.{base}
  JOIN features_wide
  WHERE {inclusao} AND {exclusao}
       │
       ▼
  Saída: (sql: str, params: list)
```

**Princípios:**
* Nunca interpola valores — usa `?` como placeholder posicional
* Recursivo: suporta AND/OR aninhados em qualquer profundidade
* Gera variante para estimativa (approx_count_distinct)

**Schema da árvore:**
```
RegrasJson:
  publico_base: str        → tabela do schema publico
  inclusao: RegraNo        → árvore de inclusão
  exclusao: RegraNo | null → árvore de exclusão (opcional)

RegraNo:
  operator: "AND" | "OR"
  rules: [RegraFolha | RegraNo]  → recursão

RegraFolha:
  campo_id: str
  op: str    (=, !=, >, <, >=, <=, between, in, not_in, is_null, is_not_null)
  value: any
```

---

## 4. Módulo Core: Validator

Valida `regras_json` contra o catálogo de características antes de executar.

```
  RegrasJson
       │
       ▼
  ① Público base existe e ativo?
       ├── NÃO ─▶ Erro: "público inválido"
       ▼
  ② Para cada folha (recursivo):
       │
       ├── Campo existe e ativo?
       │      ├── NÃO ─▶ Erro: "campo não encontrado"
       │      ▼
       ├── Operador permitido?
       │      ├── NÃO ─▶ Erro: "operador inválido"
       │      ▼
       ├── Tipo do valor compatível?
       │      ├── NÃO ─▶ Erro: "tipo incompatível"
       │      ▼
       ├── Valor dentro do domínio?
       │      ├── NÃO ─▶ Erro: "valor fora do domínio"
       │      ▼
       └── ✅ VÁLIDO
```

**Validações realizadas:**
* Público-base existe em `catalogo_publicos` (ativo=true)
* Cada `campo_id` existe em `catalogo_caracteristicas` (ativo=true)
* Operador pertence à lista `operadores` do campo
* Tipo do `value` compatível com `tipo_dado` (numeric, categorical, date, boolean)
* Se categórico: valor dentro de `valores_dominio`
* Operadores de lista (in, not_in): todos os elementos validados
* Operadores de range (between): exatamente 2 valores

---

## 5. Módulo Core: Security

```
  Request (header: X-Forwarded-Email)
       │
       ▼
  ┌─────────────────────────────────────────────────────────┐
  │ security.py: get_current_user()                       │
  │                                                       │
  │  Header presente?                                     │
  │    ├─ SIM ─▶ SELECT perfil FROM usuarios_perfil        │
  │    │          WHERE usuario_id=? AND ativo=true        │
  │    │              │                                     │
  │    │              ▼                                     │
  │    │          Retorna {usuario_id, perfil}             │
  │    │                                                   │
  │    └─ NÃO ─▶ ENV != production?                         │
  │                 ├─ SIM ─▶ Fallback: DEV_USER (dev)     │
  │                 └─ NÃO ─▶ return None → 401            │
  └─────────────────────────────────────────────────────────┘

  require_perfil(["admin"]) → 403 se perfil não bate
```

**Mecanismo:**
* Autenticação via OBO (Databricks Apps injeta `X-Forwarded-Email`)
* Autorização via tabela `governanca.usuarios_perfil`
* Factory `require_perfil([...])` gera dependência FastAPI
* Em produção: sem fallback (acesso negado se sem header)

---

## 6. DatabricksSQLClient

Singleton que gerencia conexão ao SQL Warehouse.

| Método | Retorno | Uso |
|---|---|---|
| `execute_query(sql, params)` | `list[list]` | Queries gerais |
| `fetch_one(sql, params)` | `list \| None` | 1 registro |
| `fetch_all(sql, params)` | `list[list]` | Todos os registros |
| `execute_insert(sql, params)` | `int` (rowcount) | INSERTs/UPDATEs |

**Configuração (via env):**
* `DATABRICKS_WAREHOUSE_ID` → SQL Warehouse
* `UC_CATALOG` → Catálogo (default: `plataforma`)
* Autenticação via `Config()` + `credentials_provider` (SDK auto-auth)
* PyArrow para deserialização (evita erros com nulos)

---

## 7. JobManagerService

Gerencia Databricks Jobs via SDK (`databricks-sdk`).

```
  Ação Backend          SDK Call                      Resultado
  ───────────────────   ───────────────────────────   ────────────────────
  ativar(seg_id)       ─▶ w.jobs.create(...)        ─▶ Job com schedule
  pausar(seg_id)       ─▶ w.jobs.update(sched=None)  ─▶ Job existe, não roda
  reativar(seg_id)     ─▶ w.jobs.update(sched=cron)  ─▶ Schedule restaurado
  encerrar(seg_id)     ─▶ w.jobs.delete(job_id)      ─▶ Job removido
  executar(seg_id)     ─▶ w.jobs.run_now(job_id)     ─▶ Run disparado
```

**Operações:**
* `criar_job(seg_id, seg_codigo, cron, ...)` → cria job com notebook `seg_exec`
* `pausar_job(seg_id, job_id)` → remove schedule (job existe, não roda)
* `reativar_job(seg_id, job_id, cron)` → restaura schedule
* `deletar_job(seg_id, job_id)` → remove completamente
* `executar_agora(seg_id, job_id, origem)` → disparo sob demanda

**Auditoria:** Toda operação grava em `seg_job_log`.

---

## 8. Padrão de Resposta

| Tipo | Formato |
|---|---|
| Sucesso (objeto) | `{ campo1, campo2, ... }` |
| Sucesso (lista) | `{ "data": [...], "meta": { "page", "size", "total" } }` |
| Erro | `{ "detail": "mensagem" }` + HTTP status correto |
| Validação | 422 + lista de erros |

---

## 9. Deploy (app.yaml)

```yaml
command: ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
env:
  - DATABRICKS_WAREHOUSE_ID (via sql-warehouse)
  - DATABRICKS_HOST
  - UC_CATALOG: plataforma
  - ENV: production
```

O FastAPI serve a API em `/api/*` e o frontend buildado (React) via `StaticFiles` + SPA fallback.

---

*Baseado no código-fonte real em `/segmenthub/src/`.*