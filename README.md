# Plataforma CDP ("Loucura")

Plataforma de Customer Data Platform composta por 4 sistemas independentes (Databricks Apps).

---

## Aplicações

| App | Pasta | Função |
|-----|-------|--------|
| **S1 - SegmentHub** | `segmenthub/` | Gestão de segmentações: criação, aprovação, execução, saúde, overlap |
| **S2 - ClientView 360** | `clientview360/` | Visão unificada do cliente + OBO/RLS |
| **S3 - EngagementHub** | `engagementhub/` | Campanhas, jornadas, disparos |
| **S4 - CompassHub** | `compasshub/` | Analytics, KPIs, OKRs, relatórios |

---

## Estrutura do Repositório

```
Loucura/
├── README.md                          ← este arquivo
├── databricks/
│   ├── ddl/
│   │   ├── s0_comum/                  ← DDL compartilhada (RBAC, configurações)
│   │   ├── s1_segmenthub/             ← DDL do SegmentHub
│   │   │   ├── 01_metadata.sql        ← catalogo_caracteristicas, catalogo_publicos
│   │   │   ├── 02_segmentacao.sql     ← seg_definicao, seg_execucao, seg_resultado_*, seg_overlap, etc.
│   │   │   ├── 03_dataset_sintetico.sql
│   │   │   ├── 04_segmentacao_history.sql
│   │   │   ├── 05_governanca_hist.sql
│   │   │   └── 06_job_manager.sql     ← ALTER TABLE + seg_job_log (auditoria)
│   │   ├── s2_clientview360/
│   │   ├── s3_engagement/
│   │   └── s4_analytics/
│   ├── jobs/
│   │   └── s1_segmenthub/
│   │       ├── JOBS_MANIFEST.md        ← ⭐ Convenções de nome, configs, lifecycle
│   │       ├── seg_exec.py             ← Notebook core (1 por segmento)
│   │       └── seg_saude_consolidador.py ← Infra: saúde periódica
│   └── seed/                           ← Dados seed para desenvolvimento
├── segmenthub/
│   ├── app.yaml                        ← Config do Databricks App
│   ├── requirements.txt
│   ├── src/                            ← Backend (FastAPI)
│   │   ├── main.py
│   │   ├── api/                        ← Routers (endpoints)
│   │   │   ├── segmentacao.py
│   │   │   ├── estimativa.py
│   │   │   ├── metadata.py
│   │   │   ├── metadata_admin.py
│   │   │   ├── saude.py
│   │   │   ├── chat.py
│   │   │   └── comentario.py
│   │   ├── services/                   ← Lógica de negócio
│   │   │   ├── segmentacao_service.py
│   │   │   ├── job_manager_service.py  ← ⭐ Gerencia Databricks Jobs (SDK)
│   │   │   ├── estimativa_service.py
│   │   │   ├── saude_service.py
│   │   │   ├── metadata_admin_service.py
│   │   │   ├── comentario_service.py
│   │   │   └── chat_service.py
│   │   ├── core/                       ← Infraestrutura
│   │   │   ├── query_engine.py
│   │   │   ├── validator.py
│   │   │   └── security.py
│   │   ├── models/                     ← Pydantic models
│   │   │   ├── regras.py               ← RegrasJson, RegraNo, RegraFolha
│   │   │   ├── responses.py
│   │   │   ├── chat.py
│   │   │   └── dto/
│   │   └── repositories/               ← Acesso a dados (SQL)
│   └── frontend/
│       └── src/
│           ├── App.jsx                 ← Router principal
│           ├── api/                    ← Hooks de API (useSegmentacoesApi, etc.)
│           ├── pages/                  ← Páginas React
│           ├── components/             ← Componentes reutilizáveis
│           └── shared-ui/              ← Design system compartilhado (@shared)
├── engagementhub/
├── clientview360/
└── compasshub/
```

---

## S1 - SegmentHub: Arquitetura de Jobs

### Conceito: Job-per-Segment

Cada segmentação ativa possui seu **próprio Databricks Job** com schedule individual.
O `JobManagerService` (backend) cria/pausa/deleta jobs automaticamente conforme o ciclo de vida.

### Notebooks

| Notebook | Função | Disparado por |
|----------|--------|---------------|
| `seg_exec.py` | Executa 1 segmentação (query, resultado, saúde, overlap incremental) | Job individual com cron |
| `seg_saude_consolidador.py` | Detecta atrasos, marca health vermelho, gera notificações | Job infra (6/6h) |

### Naming de Jobs

| Tipo | Padrão | Exemplo |
|------|--------|----------|
| Per-segment | `S1-SEG-{seg_codigo}` | `S1-SEG-ALTA-RENDA-3F2A` |
| Infraestrutura | `S1-INFRA-SAUDE-CONSOLIDADOR` | (fixo) |

### Lifecycle → Jobs

| Ação no Frontend | Endpoint | Efeito no Databricks Jobs |
|------------------|----------|---------------------------|
| Ativar | `POST /ativar` | `jobs.create()` com schedule |
| Pausar | `POST /pausar` | `jobs.update(schedule=None)` |
| Reativar | `POST /reativar` | `jobs.update(schedule=cron)` |
| Encerrar | `POST /encerrar` | `jobs.delete()` |
| Executar agora | `POST /executar` | `jobs.run_now()` |
| Alterar vigência | `PUT /vigencia` | `jobs.update(schedule=novo_cron)` |

---

## S1 - SegmentHub: Backend API

### Endpoints Principais

| Método | Rota | Função |
|--------|------|--------|
| POST | `/api/segmentacoes` | Criar segmentação |
| GET | `/api/segmentacoes` | Listar com filtros e paginação |
| GET | `/api/segmentacoes/{id}` | Detalhe |
| PUT | `/api/segmentacoes/{id}` | Atualizar |
| DELETE | `/api/segmentacoes/{id}` | Arquivar |
| POST | `/api/segmentacoes/{id}/validar` | Validar regras |
| POST | `/api/segmentacoes/{id}/enviar-aprovacao` | Enviar para aprovação |
| POST | `/api/segmentacoes/{id}/aprovar` | Aprovar com checklist |
| POST | `/api/segmentacoes/{id}/ativar` | Ativar (cria job) |
| POST | `/api/segmentacoes/{id}/pausar` | Pausar (pausa job) |
| POST | `/api/segmentacoes/{id}/reativar` | Reativar (reativa job) |
| POST | `/api/segmentacoes/{id}/encerrar` | Encerrar (deleta job) |
| POST | `/api/segmentacoes/{id}/executar` | Execução manual (run_now) |
| POST | `/api/segmentacoes/{id}/clonar` | Clonar |
| GET/PUT | `/api/segmentacoes/{id}/destinos` | Destinos (sistema2/sistema3) |
| PUT | `/api/segmentacoes/{id}/vigencia` | Vigência e cron |
| GET | `/api/segmentacoes/{id}/versoes` | Histórico de versões |
| GET | `/api/segmentacoes/{id}/execucoes` | Histórico de execuções |
| GET | `/api/segmentacoes/{id}/timeline` | Timeline de eventos |
| GET/POST | `/api/segmentacoes/{id}/comentarios` | Comentários |
| GET | `/api/saude` | Dashboard de saúde |
| GET | `/api/saude/{id}/overlap` | Overlap do segmento |
| POST | `/api/estimativa/preview` | Preview de público |
| POST | `/api/chat/mensagem` | Chat IA assistente |
| GET/PUT | `/api/metadata/admin/campos` | Admin catálogo |
| GET | `/api/notificacoes` | Notificações |

---

## S1 - SegmentHub: Frontend

### Páginas

| Rota | Componente | Função |
|------|------------|--------|
| `/segmentacoes` | ListaSegmentacoes | Lista com filtros |
| `/segmentacoes/nova` | BuilderSegmentacao | Builder de regras |
| `/segmentacoes/:id` | DetalheSegmentacao | Detalhe + ações de ciclo |
| `/segmentacoes/:id/editar` | BuilderSegmentacao | Edição |
| `/segmentacoes/:id/timeline` | TimelineSegmentacao | Timeline + comentários |
| `/segmentacoes/:id/documentacao` | DocumentacaoSegmentacao | Destinos + vigência |
| `/saude` | DashboardSaude | Dashboard de saúde global |
| `/admin/catalogo` | AdminCatalogo | Governança de campos |
| `/chat` | ChatSegmentacao | Chat IA |

### Convenções Frontend

- Import shared: `@shared` → `frontend/src/shared-ui/`
- Hook pattern: `useApi` + `useCallback`
- Cor primária: `#CC092F`
- Estados obrigatórios: loading, erro, vazio
- Sem lógica de negócio no frontend

---

## Banco de Dados (Unity Catalog)

**Catálogo:** `plataforma`

| Schema | Tabelas |
|--------|---------|
| `metadata` | `catalogo_caracteristicas`, `catalogo_publicos`, `catalogo_governanca_hist` |
| `segmentacao` | `seg_definicao`, `seg_execucao`, `seg_resultado_corrente`, `seg_resultado_historico`, `seg_overlap`, `seg_saude`, `seg_comentario`, `seg_notificacao`, `seg_job_log` |

---

## Setup

### Pré-requisitos

- Databricks Workspace com Unity Catalog
- Python 3.10+
- Node.js 18+ (frontend)
- `databricks-sdk` >= 0.20.0

### Passos

1. **DDL**: Execute os scripts em `databricks/ddl/s1_segmenthub/` (01 ao 06) no SQL Editor
2. **Seed**: Execute `databricks/seed/` para dados de desenvolvimento
3. **Backend**: `cd segmenthub && pip install -r requirements.txt`
4. **Frontend**: `cd segmenthub/frontend && npm install && npm run build`
5. **Deploy**: Configure via `app.yaml` e deploy como Databricks App
6. **Job Infra**: Crie manualmente o job `S1-INFRA-SAUDE-CONSOLIDADOR` (ver `JOBS_MANIFEST.md`)

### Variáveis de Ambiente

| Variável | Default | Descrição |
|----------|---------|----------|
| `SEG_EXEC_NOTEBOOK_PATH` | `/Workspace/.../seg_exec` | Path do notebook de execução |

---

## Git

- **Branch principal**: `main`
- **Branch atual (dev)**: `S1-FRONT-10`
- **Convenção de branches**: `S{N}-FRONT-{seq}` para frontend, `S{N}-BACK-{seq}` para backend
- **Commits**: conventional commits (`feat:`, `fix:`, `chore:`)

---

## Roadmap S1 (Frontend)

| Sprint | Scope | Status |
|--------|-------|--------|
| S1-FRONT-01 | Shell + Lista | ✅ |
| S1-FRONT-02 | Builder de regras | ✅ |
| S1-FRONT-03 | Estimativa | ✅ |
| S1-FRONT-04 | Documentação + Destinos + Vigência | ✅ |
| S1-FRONT-05 | Validação + Detalhe | ✅ |
| S1-FRONT-06 | Timeline + Comentários | ✅ |
| S1-FRONT-07 | Dashboard Saúde | ✅ |
| S1-FRONT-08 | Notificações | ✅ |
| S1-FRONT-09 | Chat IA | ✅ |
| S1-FRONT-10 | Admin Catálogo + Validação + Jobs | ✅ |
