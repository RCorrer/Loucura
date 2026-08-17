# SegmentHub (S1) — Documentação Técnica

> **Sistema de Segmentação No-Code** | Plataforma CDP Bradesco  
> Versão: 2.0 | Última atualização: Agosto 2026

---

## 1. Visão Executiva

O **SegmentHub** é o motor de segmentação da Plataforma CDP. Permite que analistas de CRM criem, gerenciem e executem segmentações de clientes sem contato direto com dados sensíveis — operando exclusivamente via regras visuais (no-code) ou chatbot com IA.

### Proposta de Valor

| Capacidade | Descrição |
|---|---|
| Segmentação No-Code | Builder visual com árvore AND/OR aninhada |
| Chatbot IA | Criação de segmentações via linguagem natural (Agent Framework + MCP) |
| Governança | Controle de acesso a características por sistema (S2/S3) com histórico auditável |
| Execução Automatizada | Arquitetura job-per-segment com schedule individual |
| Monitoramento | Health checks automáticos, overlap detection, alertas proativos |

---

## 2. Arquitetura de Alto Nível

```
  ┌─────────────────────────────────────────────────────────────────────────────────┐
  │                        ARQUITETURA DE ALTO NÍVEL                                │
  └─────────────────────────────────────────────────────────────────────────────────┘

  ╔═══════════════════════════╗       ╔═══════════════════════════════════════════╗
  ║   FRONTEND (React + MUI) ║       ║            AI STACK                       ║
  ║                           ║       ║                                           ║
  ║  • Builder No-Code        ║       ║  • Foundation Model                      ║
  ║  • ChatBot Panel          ║       ║  • Vector Search (RAG)                   ║
  ║  • Dashboard Saúde        ║       ║  • MCP Tools                             ║
  ╚═════════════╤═════════════╝       ╚═══════════════════╤═══════════════════════╝
                │                                         │
                ▼                                         │
  ╔═══════════════════════════════════════════════════════════════════════════════╗
  ║   BACKEND (FastAPI)                                                          ║
  ║                                                                              ║
  ║   ┌───────────┐   ┌───────────────┐   ┌────────────────┐   ┌─────────────┐  ║
  ║   │ API Layer │──▶│ Service Layer │──▶│ Repository Lyr │──▶│  DB Client  │  ║
  ║   │  /api/*   │   │ (negócio)     │   │ (SQL param.)   │   │  (SDK)      │  ║
  ║   └───────────┘   └───────┬───────┘   └────────────────┘   └──────┬──────┘  ║
  ║                           │                                        │         ║
  ║                    ┌──────┴──────┐                                 │         ║
  ║                    │    CORE     │                                 │         ║
  ║                    │ QueryEngine │                                 │         ║
  ║                    │ Validator   │             ┌───────────────┐   │         ║
  ║                    │ Security    │             │ JobManager    │   │         ║
  ║                    └─────────────┘             │ (Databricks   │   │         ║
  ║                                                │  SDK)         │   │         ║
  ║                                                └───────┬───────┘   │         ║
  ╚════════════════════════════════════════════════════════╪═══════════╪═════════╝
                                                           │           │
                          ┌────────────────────────────────┘           │
                          ▼                                            ▼
  ╔═══════════════════════════════════╗    ╔══════════════════════════════════════╗
  ║     DATABRICKS JOBS               ║    ║    DATABRICKS — UNITY CATALOG        ║
  ║                                   ║    ║                                      ║
  ║  • S1-SEG-{codigo} (1 por seg.)   ║───▶║  metadata │ segmentacao │ publico    ║
  ║  • S1-INFRA-SAUDE-CONSOLIDADOR    ║    ║  caracteristicas │ eventos │ gov.    ║
  ╚═══════════════════════════════════╝    ╚══════════════════════════════════════╝
```

---

## 3. Stack Tecnológica

| Camada | Tecnologia | Versão/Detalhe |
|---|---|---|
| **Runtime** | Databricks App | uvicorn, porta 8000 |
| **Backend** | FastAPI + Pydantic v2 | Python 3.11+ |
| **Frontend** | React + Vite + MUI | Design system shared-ui (paleta Bradesco) |
| **Dados** | Delta Lake + Unity Catalog | Catálogo `plataforma` |
| **Compute** | SQL Warehouse Serverless + Photon | Queries parametrizadas |
| **Jobs** | Databricks Jobs (SDK) | Arquitetura job-per-segment |
| **IA/Chat** | Agent Framework + MCP + Vector Search | Foundation Model do workspace |
| **Autenticação** | OBO (Databricks Apps) | Header `X-Forwarded-Email` |
| **Autorização** | RBAC via `governanca.usuarios_perfil` | Perfis: admin, analista |

---

## 4. Estrutura de Diretórios

```
segmenthub/
├── app.yaml                     # Config Databricks App (uvicorn)
├── requirements.txt             # Dependências Python
├── package.json / vite.config   # Config do frontend
│
├── src/                         # BACKEND
│   ├── main.py                  # FastAPI app + routers + SPA fallback
│   ├── api/                     # Endpoints REST
│   │   ├── metadata.py          # Catálogo público (temas/campos)
│   │   ├── metadata_admin.py    # Governança de catálogo (admin)
│   │   ├── segmentacao.py       # CRUD + ciclo de vida
│   │   ├── estimativa.py        # Estimativa de público
│   │   ├── comentario.py        # Comentários + notificações
│   │   ├── saude.py             # Dashboard de saúde
│   │   └── chat.py              # Chatbot endpoint
│   ├── services/                # Lógica de negócio
│   │   ├── segmentacao_service.py
│   │   ├── metadata_service.py
│   │   ├── metadata_admin_service.py
│   │   ├── estimativa_service.py
│   │   ├── comentario_service.py
│   │   ├── saude_service.py
│   │   ├── chat_service.py
│   │   └── job_manager_service.py  # Databricks SDK — CRUD de Jobs
│   ├── repositories/            # Acesso a dados (SQL)
│   │   ├── segmentacao_repository.py
│   │   ├── metadata_repository.py
│   │   ├── metadata_admin_repository.py
│   │   ├── estimativa_repository.py
│   │   ├── comentario_repository.py
│   │   └── saude_repository.py
│   ├── core/                    # Módulos transversais
│   │   ├── security.py          # OBO + RBAC
│   │   ├── query_engine.py      # JSON → SQL parametrizado
│   │   ├── validator.py         # Validação contra catálogo
│   │   ├── config.py            # Configurações
│   │   └── llm_client.py        # Cliente LLM
│   ├── models/                  # Pydantic schemas
│   │   ├── regras.py            # RegraFolha, RegraNo, RegrasJson
│   │   ├── chat.py
│   │   ├── responses.py
│   │   └── dto/                 # Data Transfer Objects
│   ├── db/                      # Cliente SQL
│   │   └── databricks_client.py # Conexão via SDK + credentials_provider
│   └── exceptions/              # Exceções customizadas
│
├── frontend/                    # FRONTEND (React)
│   └── src/
│       ├── pages/               # Telas (1 por rota)
│       ├── components/          # Componentes específicos
│       ├── api/                 # Clients HTTP
│       └── shared-ui/           # Cópia sincronizada do design system
│
├── static/                      # Build React (servido por FastAPI)
│   ├── index.html
│   └── assets/
│
└── (jobs em /databricks/jobs/s1_segmenthub/)
    ├── seg_exec                 # Notebook: executa 1 segmentação
    └── seg_saude_consolidador   # Notebook: health checks periódicos
```

---

## 5. Princípios de Design

```
  ┌─────────────────────────┐   ┌─────────────────────────┐
  │ 🔒 SEGURANÇA            │   │ 🔗 DESACOPLAMENTO       │
  │                         │   │                         │
  │ • Zero acesso direto    │   │ • Contratos via GRANT   │
  │   a dados               │   │   SELECT                │
  │ • SQL parametrizado     │   │ • Eventos assíncronos   │
  │   (nunca interpola)     │   │ • Flags de outros       │
  │ • RBAC por perfil       │   │   sistemas: administra, │
  │ • Anti-injection via    │   │   não consome           │
  │   validador             │   │                         │
  └─────────────────────────┘   └─────────────────────────┘

  ┌─────────────────────────┐   ┌─────────────────────────┐
  │ 📈 ESCALABILIDADE       │   │ 👁 OBSERVABILIDADE      │
  │                         │   │                         │
  │ • Job-per-segment (1:1) │   │ • Health status auto    │
  │ • HyperLogLog para      │   │ • Notificações          │
  │   estimativas           │   │   proativas             │
  │ • Overlap incremental   │   │ • Auditoria completa    │
  │ • Delta MERGE atômico   │   │   (histórico estados)   │
  │                         │   │ • Job run URLs          │
  │                         │   │   rastreáveis           │
  └─────────────────────────┘   └─────────────────────────┘
```

---

## 6. Schemas do Unity Catalog

O SegmentHub opera sobre o catálogo `plataforma` com os seguintes schemas:

| Schema | Papel no S1 | Acesso |
|---|---|---|
| `plataforma.metadata` | Catálogo no-code (temas, campos, públicos, governança) | Leitura + Escrita (admin) |
| `plataforma.segmentacao` | Produção de públicos (definição, execução, resultado, saúde) | Leitura + Escrita |
| `plataforma.caracteristicas` | Features de clientes (customer_features_wide) | Leitura |
| `plataforma.publico` | Públicos-base pré-definidos | Leitura |
| `plataforma.eventos` | Barramento de eventos (seg_eventos) | Escrita |
| `plataforma.governanca` | RBAC + consentimento | Leitura |
| `plataforma.core_cliente` | Golden Record (cadastro) | Leitura |

---

## 7. Fluxo Principal (End-to-End)

```
  ┌─────────────────────────────────── FLUXO END-TO-END ──────────────────────────────────┐
  │                                                                                        │
  │  FASE 1: ESTIMATIVA (tempo real)                                                       │
  │                                                                                        │
  │  Analista ─▶ Frontend ─▶ FastAPI ─▶ QueryEngine ─▶ SQL Warehouse                       │
  │    (monta      (POST /api/       (RegrasJson     (approx_count_                        │
  │     regras)     estimativa/        → SQL)          distinct)                            │
  │                 preview)                               │                                │
  │                                                        ▼                                │
  │  Analista ◀─ Frontend ◀─ FastAPI ◀─────────────── ~15.000 clientes                     │
  │                                                                                        │
  │  FASE 2: APROVAÇÃO (cria Job)                                                          │
  │                                                                                        │
  │  Analista ─▶ Frontend ─▶ FastAPI ─▶ JobManager ─▶ Databricks Jobs API                   │
  │    (aprova)    (POST /api/         (criar_job)    (jobs.create + cron)                  │
  │                 {id}/aprovar)                           │                                │
  │                             FastAPI ─▶ Delta: UPDATE status='ativa'                     │
  │                             FastAPI ─▶ Delta: INSERT seg_eventos                        │
  │                                                                                        │
  │  FASE 3: EXECUÇÃO (schedule automático via cron)                                       │
  │                                                                                        │
  │  Databricks Job ─▶ SQL Warehouse ─▶ Resultado (SET cpf_cnpj)                           │
  │    (cron dispara)   (query completa)      │                                            │
  │                                           ├─▶ MERGE seg_resultado_corrente             │
  │                                           ├─▶ INSERT seg_resultado_historico           │
  │                                           ├─▶ MERGE seg_saude                         │
  │                                           └─▶ MERGE seg_overlap                       │
  │                                                                                        │
  └────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Índice da Documentação

| # | Documento | Conteúdo |
|---|---|---|
| 01 | **Este arquivo** | Visão geral, arquitetura, stack, estrutura |
| 02 | [Schemas e Tabelas](02-SCHEMAS-TABELAS.md) | DDLs, colunas, índices, relacionamentos |
| 03 | [Arquitetura Backend](03-ARQUITETURA-BACKEND.md) | Camadas, padrões, módulos core |
| 04 | [Ciclo de Vida e Estados](04-CICLO-VIDA-ESTADOS.md) | State machine, transições, versionamento |
| 05 | [Jobs e Execução](05-JOBS-EXECUCAO.md) | Arquitetura job-per-segment, notebooks, fluxos |
| 06 | [API REST](06-API-ENDPOINTS.md) | Endpoints completos, request/response |
| 07 | [Integração e Contratos](07-INTEGRACAO-CONTRATOS.md) | Eventos, GRANT SELECT, dependências |
| 08 | [Segurança e RBAC](08-SEGURANCA-RBAC.md) | Autenticação, autorização, anti-injection |

---

*Documentação gerada a partir do código-fonte real do sistema em Agosto/2026.*