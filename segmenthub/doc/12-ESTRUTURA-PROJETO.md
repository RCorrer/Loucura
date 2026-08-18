# Estrutura do Projeto — Plataforma CDP

> **4 projetos independentes** — cada um é um Databricks App separado (deploy isolado).  
> **1 biblioteca de front compartilhada** (`shared-ui`) copiada via script de sync.  
> Base do design system: **MUI** + tokens de cor Bradesco.

---

## 1. Visão Geral da Plataforma

```
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │                           plataforma-cdp/                                         │
  │                                                                                   │
  │  ┌────────────┐   ┌────────────────┐  ┌───────────────┐  ┌─────────────┐   │
  │  │ shared-ui  │   │ segmenthub     │  │ engagementhub │  │ clientview  │   │
  │  │ (lib só    │   │ (S1 App)       │  │ (S3 App)      │  │ 360 (S2)    │   │
  │  │  copia p/  │   │                │  │               │  │             │   │
  │  │  os apps)  │   │  ┌──────────┐ │  │  ┌─────────┐ │  │  ┌─────────┐│   │
  │  └────────────┘   │  │ src/     │ │  │  │ src/    │ │  │  │ src/    ││   │
  │                    │  │ frontend/│ │  │  │ track/  │ │  │  │ OBO +   ││   │
  │  ┌────────────┐   │  │ static/  │ │  │  │ front/  │ │  │  │ RLS     ││   │
  │  │ compasshub │   │  └──────────┘ │  │  └─────────┘ │  │  └─────────┘│   │
  │  │ (S4 App)   │   └────────────────┘  └───────────────┘  └─────────────┘   │
  │  └────────────┘                                                               │
  │                                                                                   │
  │  ┌──────────────────────────────────────────────────────────────────────┐  │
  │  │ databricks/                                                                │  │
  │  │   ddl/  (29 DDLs organizados por sistema: s0_comum, s1, s2, s3, s4)       │  │
  │  │   jobs/ (notebooks de execução agendada)                                  │  │
  │  └──────────────────────────────────────────────────────────────────────┘  │
  │                                                                                   │
  │  ┌──────────────────────────────────────────────────────────────────────┐  │
  │  │ scripts/                                                                   │  │
  │  │   sync-shared-ui.sh  (copia shared-ui para dentro de cada app)             │  │
  │  └──────────────────────────────────────────────────────────────────────┘  │
  └─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. shared-ui (Biblioteca Compartilhada)

Fonte única do design system. **Nunca editar as cópias dentro dos apps** — editar aqui e rodar o sync.

```
  shared-ui/
  ├── package.json                 MUI, emotion
  ├── src/
  │   ├── index.js                 export central
  │   ├── theme/
  │   │   ├── tokens.js            cores Bradesco + funcionais + espaçamento/raio
  │   │   ├── palette.js           paleta MUI (primary=vermelho)
  │   │   ├── typography.js        tipografia corporativa
  │   │   └── theme.js             createTheme(...) final
  │   ├── components/
  │   │   ├── AppShell/            sidebar + topbar + área conteúdo
  │   │   ├── PageHeader/
  │   │   ├── DataTable/           wrapper do MUI DataGrid
  │   │   ├── StatusBadge/         verde/amarelo/vermelho
  │   │   ├── ConfirmDialog/
  │   │   ├── EmptyState/
  │   │   ├── LoadingState/
  │   │   ├── NotificationBell/
  │   │   ├── MetricCard/
  │   │   ├── FormField/
  │   │   └── ChatPanel/           painel de chat reutilizável (S1 e S2)
  │   ├── hooks/
  │   │   ├── useApi.js            fetch base /api + erro padrão
  │   │   ├── useNotifications.js
  │   │   └── useChat.js           estado de conversa (envia p/ /api/chat/mensagem)
  │   └── utils/
  │       ├── formatters.js        moeda/percentual/data pt-BR
  │       └── constants.js         enums (status, perfis, canais)
  └── README.md                    como usar + aviso "não editar cópias"
```

### Paleta Bradesco (tokens.js)

```
  ┌─────────────────────────────────────────────────────────────────────────┐
  │  CORES                                                                     │
  │                                                                            │
  │  MARCA      #CC092F (primary)  #900F15 (dark)  #E00B39 (alt)               │
  │  NEUTRO     #000000 ─ #808285 ─ #EDEDED ─ #FFFFFF                          │
  │  SURFACE    #F8F6F0 (canvas)  #FFFFFF (paper)  #ECE7DE─#CFC9C1 (warm)      │
  │  FEEDBACK   #2E7D32 (success) #B26A00 (warning) #1565C0 (info) #B00020 (err)│
  │                                                                            │
  │  ⚠️  Vermelho de marca (#CC092F) = ações/destaque                            │
  │      Vermelho de erro (#B00020) = mensagens de erro                         │
  │      NUNCA confundir os dois!                                               │
  └─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Estrutura do S1 — SegmentHub (Modelo de Referência)

Estrutura real implementada (fonte de verdade):

```
  segmenthub/
  ├── app.yaml                      Config Databricks App (uvicorn)
  ├── requirements.txt              Dependências Python
  │
  ├── src/                          BACKEND (FastAPI)
  │   ├── main.py                   FastAPI app + routers + SPA fallback
  │   ├── api/                      Endpoints REST
  │   │   ├── metadata.py           Catálogo público (temas/campos)
  │   │   ├── metadata_admin.py     Governança de catálogo (admin)
  │   │   ├── segmentacao.py        CRUD + ciclo de vida
  │   │   ├── estimativa.py         Estimativa de público
  │   │   ├── comentario.py         Comentários + notificações
  │   │   ├── saude.py              Dashboard de saúde
  │   │   └── chat.py               Chatbot endpoint
  │   ├── services/                 Lógica de negócio
  │   │   ├── segmentacao_service.py
  │   │   ├── metadata_service.py
  │   │   ├── metadata_admin_service.py
  │   │   ├── estimativa_service.py
  │   │   ├── comentario_service.py
  │   │   ├── saude_service.py
  │   │   ├── chat_service.py
  │   │   └── job_manager_service.py   Databricks SDK — CRUD de Jobs
  │   ├── repositories/             Acesso a dados (SQL)
  │   ├── core/                     Módulos transversais
  │   │   ├── security.py           OBO + RBAC
  │   │   ├── query_engine.py       JSON → SQL parametrizado
  │   │   ├── validator.py          Validação contra catálogo
  │   │   ├── config.py             Configurações
  │   │   └── llm_client.py         Cliente LLM
  │   ├── models/                   Pydantic schemas
  │   ├── db/                       Cliente SQL
  │   │   └── databricks_client.py  Conexão via SDK + credentials_provider
  │   └── exceptions/               Exceções customizadas
  │
  ├── frontend/                     FRONTEND (React + Vite + MUI)
  │   └── src/
  │       ├── pages/                Telas (1 por rota)
  │       ├── components/           Componentes específicos
  │       ├── api/                  Clients HTTP
  │       └── shared-ui/            Cópia sincronizada (NÃO editar)
  │
  ├── static/                       Build React (servido por FastAPI)
  │   ├── index.html
  │   └── assets/
  │
  └── doc/                          Documentação técnica (este repo)
```

### app.yaml (base dos 4 apps)

```yaml
command: ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 4. Diferenças entre os Sistemas

### S3 — EngagementHub (o maior)

| Aspecto | Diferença do S1 |
|---|---|
| Chatbot | Não tem |
| Rotas extras | `/track/*` (pixel/redirect) + `/webhook/*` |
| Backend | `src/track/`, `src/providers/` (canais), `src/core/orquestrador.py` |
| Front extra | React Flow (jornadas), GrapesJS+MJML (peças) |
| Deps extras | `requests`, `numpy`, `scipy`, `jinja2`, `reactflow`, `grapesjs` |

### S2 — ClientView 360

| Aspecto | Diferença do S1 |
|---|---|
| Autenticação | **OBO** (não Service Principal) — responde pela carteira do usuário |
| RLS | `src/core/rls_context.py` — filtra por vinculo_cliente_responsavel |
| Chatbot | Sim (tools sob OBO — respeita RLS) |
| Motor Visão 360 | `src/core/visao360_engine.py` — blocos dinâmicos |

### S4 — CompassHub

| Aspecto | Diferença do S1 |
|---|---|
| Chatbot | Não tem |
| RLS | Não tem |
| Dashboards | Embeds de AI/BI Dashboards nativos |
| Extra | `pdf_generator.py` (relatórios), `reportlab` |
| Natureza | Híbrido App + AI/BI + PDF |

---

## 5. Padrão do Chatbot (S1 e S2)

```
  ┌───────────────────────────────────────────────────────────────────────────┐
  │  FLUXO DO CHATBOT                                                             │
  │                                                                               │
  │  Front: ChatPanel (shared-ui) + useChat  ──▶  POST /api/chat/mensagem        │
  │                                                       │                        │
  │  Back: api/chat.py recebe ─▶ chama chat_service ─▶ agente                     │
  │                                                       │                        │
  │  Agente (Agent Framework):                            │                        │
  │    ├─ Resolve Foundation Model do workspace           │                        │
  │    ├─ Decide chamar tools (MCP)                       │                        │
  │    ├─ Usa Vector Search (RAG) para contexto           │                        │
  │    └─ Retorna resposta (+ no S1, o regras_json)       │                        │
  │                                                       │                        │
  │  [S2] Tools executam sob OBO → respeitam RLS           │                        │
  │  [S1] Tools reutilizam lógica existente                │                        │
  └───────────────────────────────────────────────────────────────────────────┘
```

**Tools MCP do S1:** `listar_temas`, `listar_campos`, `descrever_campo`, `estimar_publico`, `criar_segmentacao`, `consultar_insights`

**Tools MCP do S2:** `minha_carteira`, `resumo_cliente`, `campanhas_do_cliente`, `engajamento_cliente`, `sugerir_abordagem`, `priorizar_carteira`, `registrar_interacao`

---

## 6. DDLs — Organização por Sistema

```
  databricks/ddl/
  ├── s0_comum/                     Infraestrutura compartilhada
  │   ├── 01_catalog_schemas.sql    Cria catlogo + schemas
  │   ├── 02_governanca.sql         usuarios_perfil, consentimento
  │   ├── 03_eventos.sql            Tabelas de eventos (3)
  │   └── 04_core_cliente.sql       golden_record, vínculos
  │
  ├── s1_segmenthub/                Motor de segmentação
  │   ├── 01_metadata.sql           catalogo_caracteristicas, catalogo_publicos
  │   ├── 02_segmentacao.sql        seg_definicao, seg_versao, seg_destino...
  │   ├── 03_dataset_sintetico.sql  customer_features_wide (dados fake)
  │   ├── 04_segmentacao_history.sql seg_historico_estado
  │   ├── 05_governanca_hist.sql    catalogo_governanca_hist
  │   └── 06_job_manager.sql        job_id_databricks (ALTER TABLE)
  │
  ├── s2_clientview360/             Visão 360 + atendimento
  │   ├── 01_analitico.sql          Métricas, priorizacao
  │   ├── 02_rls.sql                Row-Level Security
  │   ├── 03_config.sql             Configurações admin
  │   ├── 04_atendimento.sql        Interações, follow-ups
  │   └── 05_visao360.sql           Blocos dinâmicos
  │
  ├── s3_engagement/                Campanhas + disparos
  │   ├── 01_campanha.sql           Campanhas, config
  │   ├── 02_waterfall_capping.sql  Regras de fadiga
  │   ├── 03_canais.sql             Configuração de canais
  │   ├── 04_pecas.sql              Peças de comunicação
  │   ├── 05_jornadas.sql           Definição de jornadas
  │   ├── 06_disparo.sql            Filas de disparo
  │   ├── 07_tracking.sql           Tracking de eventos
  │   ├── 08_otimizacao.sql         MAB/A-B testing
  │   ├── 09_operacao.sql           Operações (monitoring)
  │   └── 10_contratos_saida.sql    Views-contrato (segmento_campanha_map...)
  │
  └── s4_analytics/                 KPIs, OKRs, insights
```

---

## 7. Jobs — Organização por Sistema

### S1 — Arquitetura Job-per-Segment (v2)

```
  ┌──────────────────────────────────────────────────────────────────────┐
  │  databricks/jobs/s1_segmenthub/                                            │
  │                                                                            │
  │  ┌────────────────────────────────────────────────────────────────┐    │
  │  │  seg_exec             Notebook parametrizado                      │    │
  │  │                        Executa 1 segmentação (seg_id)              │    │
  │  │                        ~1000 Jobs dinâmicos (1 por seg. ativa)     │    │
  │  └────────────────────────────────────────────────────────────────┘    │
  │  ┌────────────────────────────────────────────────────────────────┐    │
  │  │  seg_saude_consolidador   Job fixo (6h em 6h)                     │    │
  │  │                            Detecta atrasos, gera alertas           │    │
  │  │                            Limpa execuções travadas                │    │
  │  └────────────────────────────────────────────────────────────────┘    │
  │  ┌────────────────────────────────────────────────────────────────┐    │
  │  │  JOBS_MANIFEST.md       Documentação de referência                │    │
  │  └────────────────────────────────────────────────────────────────┘    │
  └──────────────────────────────────────────────────────────────────────┘
```

> **Nota:** A arquitetura evoluiu de 4 jobs centralizados (v1) para job-per-segment (v2). Ver [05-JOBS-EXECUCAO.md](./05-JOBS-EXECUCAO.md) para detalhes.

---

## 8. Build e Deploy (por App)

```
  ┌──────────────────────────────────────────────────────────────────────┐
  │  PIPELINE DE BUILD                                                        │
  │                                                                            │
  │  ① (ao mudar design)  ./scripts/sync-shared-ui.sh                         │
  │       │                                                                    │
  │       ▼                                                                    │
  │  ② cd <app>/frontend && npm install && npm run build                      │
  │       │                         └─▶ gera ../static/                       │
  │       ▼                                                                    │
  │  ③ Deploy no Databricks Apps (empacota src/ + static/)                     │
  │                                                                            │
  │  [opcional dev local]  uvicorn src.main:app --reload  +  vite dev          │
  └──────────────────────────────────────────────────────────────────────┘
```

### Script de Sync (gambiarra controlada)

| Regra | Detalhe |
|---|---|
| Verdade | `shared-ui/` é a fonte única |
| Cópias | São descartáveis (regeneradas pelo sync) |
| .gitignore | Ignora `*/frontend/src/shared-ui/` |
| Workflow | Alterou lib → sync → rebuild |
| Migração futura | Monorepo troca a cópia por workspace sem mudar imports |

---

## 9. Requisitos por Sistema

| Sistema | requirements.txt (além do base) | frontend extras |
|---|---|---|
| S1 | `databricks-agents`, `databricks-vectorsearch`, `mlflow` | — |
| S2 | `databricks-agents`, `databricks-vectorsearch`, `mlflow` | — |
| S3 | `requests`, `numpy`, `scipy`, `jinja2` | `reactflow`, `grapesjs`, `grapesjs-mjml` |
| S4 | `reportlab` | — |

**Base comum:** `fastapi`, `uvicorn`, `pydantic`, `databricks-sql-connector`, `databricks-sdk`, `python-multipart`

---

*Referência cruzada: para estrutura detalhada do S1, ver [01-VISAO-GERAL.md §4](./01-VISAO-GERAL.md).*