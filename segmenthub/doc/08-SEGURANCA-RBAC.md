# Segurança e RBAC — SegmentHub

> Autenticação, autorização, anti-injection e proteção de dados.

---

## 1. Modelo de Segurança

```
  ┌────────────────────────┐   ┌──────────────────────┐   ┌──────────────────────────────┐
  │  AUTENTICAÇÃO          │   │  AUTORIZAÇÃO          │   │  PROTEÇÃO DE DADOS            │
  │                        │   │                      │   │                              │
  │  Databricks Apps OBO   │   │  RBAC via            │   │  • SQL parametrizado          │
  │  X-Forwarded-Email     │──▶│  governanca.         │──▶│    (nunca interpola)        │
  │                        │   │  usuarios_perfil     │   │  • Validator (campo/op/tipo)  │
  │                        │   │                      │   │  • Zero acesso direto         │
  │                        │   │                      │   │    (só contagens)            │
  └────────────────────────┘   └──────────────────────┘   └──────────────────────────────┘
```

---

## 2. Autenticação (OBO)

| Aspecto | Detalhe |
|---|---|
| Mecanismo | Databricks Apps injeta `X-Forwarded-Email` |
| Header | `X-Forwarded-Email: usuario@email.com` |
| Fallback (dev) | Variável `DEV_USER` (só se `ENV != production`) |
| Produção | Sem fallback — sem header = 401 |

```
  Browser             Databricks Apps           FastAPI
  ───────              ───────────────           ───────
     │                       │                      │
     ├─ Request (SSO) ────▶  │                      │
     │                       ├─ Autentica Azure AD   │
     │                       │                      │
     │                       ├─ Request + ────────▶  │
     │                       │   X-Forwarded-Email   ├─ get_current_user()
     │                       │                      ├─ Busca perfil em
     │                       │                      │   usuarios_perfil
     ▼                       ▼                      ▼
```

---

## 3. Autorização (RBAC)

### Perfis no SegmentHub

| Perfil | Pode fazer | Não pode |
|---|---|---|
| `analista` | Criar, editar, listar, executar, pausar, reativar segmentações; estimar; comentar | Aprovar; admin de catálogo |
| `admin` | Tudo do analista + aprovar + governança de catálogo + admin flags | — |

### Mecanismo

```python
# Dependência FastAPI (factory pattern)
@router.post("/{seg_id}/aprovar")
async def aprovar(
    seg_id: str,
    user: dict = Depends(require_perfil(["admin"]))  # Só admin
):
    ...
```

**Tabela de controle:** `plataforma.governanca.usuarios_perfil`
```sql
SELECT perfil
FROM plataforma.governanca.usuarios_perfil
WHERE usuario_id = ?
  AND sistema = 'segmenthub'
  AND ativo = true
```

---

## 4. Matriz de Permissões

| Operação | analista | admin |
|---|:---:|:---:|
| Criar segmentação | ✅ | ✅ |
| Editar segmentação | ✅ | ✅ |
| Listar / visualizar | ✅ | ✅ |
| Estimar público | ✅ | ✅ |
| Enviar para aprovação | ✅ | ✅ |
| **Aprovar** | ❌ | ✅ |
| Pausar / reativar / encerrar | ✅ | ✅ |
| Executar manualmente | ✅ | ✅ |
| Clonar | ✅ | ✅ |
| Comentar / mencionar | ✅ | ✅ |
| Ver saúde | ✅ | ✅ |
| **Admin catálogo (flags)** | ❌ | ✅ |
| **Admin histórico governança** | ❌ | ✅ |
| Usar chatbot | ✅ | ✅ |

---

## 5. Anti-Injection

### Backend (QueryEngine)

```
  regras_json ─▶ Validator ─▶ QueryEngine ─▶ execute_query ─▶ SQL Warehouse
                 (campo        (gera SQL      (sql, params)    (parametrizado)
                  existe?        com ?)
                  op válido?)
```

**Princípios:**
* `campo_id` validado contra catálogo (whitelist) — não aceita campo arbitrário
* Operadores validados contra lista fixa por campo
* Valores passados como parâmetros posicionais (`?`) — nunca interpolados
* Tipo do valor verificado antes de executar

### Jobs (seg_exec)

O notebook `seg_exec` resolve campos físicos via catálogo em runtime:
* `campo_id` → lookup em `catalogo_caracteristicas` → `tabela_fisica.campo_fisico`
* Valores são escapados para strings, convertidos para números quando numérico
* JOINs são montados dinamicamente a partir das tabelas referenciadas

---

## 6. Proteção de Dados

| Princípio | Implementação |
|---|---|
| Analista nunca vê dados individuais | API retorna só contagens (approx_count_distinct) |
| CPFs nunca expostos via API | Endpoint de estimativa retorna apenas número |
| Acesso ao warehouse via Service Principal | Analista não tem credencial direta |
| Chatbot respeita as mesmas regras | Tools retornam só contagens e metadados |
| Campos sensíveis marcados | `sensibilidade = 'lgpd'` no catálogo |

---

## 7. Acesso ao Banco

```
  Databricks App ─▶ SQL Warehouse Serverless ─▶ Unity Catalog (plataforma.*)
    (Service Principal                          (queries parametrizadas
     via credentials_provider)                    passam pelo UC)
```

| Aspecto | Detalhe |
|---|---|
| Método | `databricks-sql-connector` + `databricks.sdk.core.Config` |
| Auth | `credentials_provider` (auto via contexto do App) |
| Warehouse | Definido por `DATABRICKS_WAREHOUSE_ID` (env) |
| Isolation | Connection pooling via singleton `get_client()` |

---

## 8. Governança de Catálogo (Auditoria)

```
  Admin altera flag
       │
       ▼
  Flag realmente mudou?
    ├─ SIM ─▶ INSERT catalogo_governanca_hist
    │           (quem, quando, de→para, motivo)
    │              │
    │              ▼
    │         Trilha auditável (append-only)
    │
    └─ NÃO ─▶ Nenhuma gravação
```

**Campos auditados:** `usavel_em_visao360`, `usavel_em_peca`, `bloco_visao360`, `ativo`  
**Identificação:** `alterado_por` = usuário autenticado (nunca do body)  
**Política:** Append-only (tabela nunca recebe UPDATE ou DELETE)

---

## 9. Configuração de Ambiente

| Variável | Uso | Produção |
|---|---|---|
| `DATABRICKS_WAREHOUSE_ID` | SQL Warehouse | Via `sql-warehouse` (App) |
| `DATABRICKS_HOST` | Hostname | `dbc-*.cloud.databricks.com` |
| `UC_CATALOG` | Catálogo | `plataforma` |
| `ENV` | Ambiente | `production` (desativa fallbacks) |
| `DEV_USER` | Usuário dev (só dev) | Não definido em prod |
| `SEG_EXEC_NOTEBOOK_PATH` | Path do notebook seg_exec | Path no workspace |

---

*Baseado no código real de `security.py`, `query_engine.py`, `validator.py` e `app.yaml`.*