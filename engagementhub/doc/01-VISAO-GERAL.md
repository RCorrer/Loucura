# EngagementHub (S3) — Documentação Técnica

> **Marketing Cloud No-Code** | Plataforma CDP Bradesco
> Versão: 1.0 | Última atualização: Agosto 2026

---

## 1. Visão Executiva

O **EngagementHub** é o motor de campanhas digitais da Plataforma CDP. Permite que analistas de CRM criem campanhas multicanal (email + WhatsApp), desenhem jornadas visuais, personalizem peças e disparem comunicações — tudo com governança automática (capping, consentimento, waterfall) e otimização MAB (Multi-Armed Bandit).

### Proposta de Valor

| Capacidade | Descrição |
|---|---|
| Campanhas Multicanal | Email (GrapesJS+MJML) + WhatsApp (templates Meta HSM) |
| Jornadas Visuais | Editor React Flow com 7 tipos de nó |
| Governança Automática | Waterfall, frequency capping, consentimento, janela de envio |
| Otimização A/B | Thompson Sampling (MAB) com convergência automática |
| Tracking Completo | Funil enviado→entregue→aberto→clicou→converteu |
| Disparável Avulso (DAV) | Envios standalone com mesma governança |
| Operação | Dashboard operacional + alertas proativos |

---

## 2. Arquitetura de Alto Nível

```
  ┌─────────────────────────────────────────────────────────────────────────────────┐
  │                        ARQUITETURA S3 — ENGAGEMENTHUB                          │
  └─────────────────────────────────────────────────────────────────────────────────┘

  ╔═══════════════════════════╗       ╔═══════════════════════════════════════════╗
  ║   FRONTEND (React + MUI) ║       ║       PROVIDERS (pluggáveis)               ║
  ║                           ║       ║                                           ║
  ║  • Campanhas              ║       ║  • EmailProvider (SMTP / Mailtrap)       ║
  ║  • Peças (GrapesJS+MJML)  ║       ║  • WhatsAppProvider (Meta Cloud API)    ║
  ║  • Jornadas (React Flow)  ║       ║  • (+) novos canais via interface        ║
  ║  • Disparos + Avulso      ║       ╗═══════════════════════════════════════════╝
  ║  • Otimização MAB        ║                         │
  ║  • Operação + Admin       ║                         │
  ╚═════════════╖═════════════╝                         │
                │                                         │
                ▼                                         ▼
  ╔═══════════════════════════════════════════════════════════════════════════╗
  ║   BACKEND (FastAPI)                                                          ║
  ║                                                                              ║
  ║   ┌───────────┐   ┌───────────────┐   ┌────────────────┐   ┌─────────────┐  ║
  ║   │ API Layer │──▶│ Service Layer │──▶│ CORE            │   │ Providers   │  ║
  ║   │  /api/*   │   │               │   │ • Orquestrador  │   │ email/wpp   │  ║
  ║   └───────────┘   └───────────────┘   │ • Motor Jornada│   └─────────────┘  ║
  ║   ┌───────────┐                       │ • Motor Disparo│                      ║
  ║   │ Track     │                       │ • Render Engine│                      ║
  ║   │/track/*   │                       │ • MAB (Thompson)│                     ║
  ║   │/webhook/* │                       └────────────────┘                      ║
  ║   └───────────┘                                                              ║
  ╚═══════════════════════════════════════════════════════════════════════════╝
                           │                                 │
                           ▼                                 ▼
  ╔═══════════════════════════════════╗    ╔══════════════════════════════════════╗
  ║     DATABRICKS JOBS               ║    ║    DATABRICKS — UNITY CATALOG        ║
  ║                                   ║    ║                                      ║
  ║  • engagement_orquestrador        ║───▶║  engagement │ tracking │ operacao   ║
  ║  • motor_jornada (∼5min)          ║    ║  + consome S1: seg_resultado_corrente║
  ║  • motor_disparo (∼5min)          ║    ║  + consome S0: consentimento         ║
  ║  • otimizador_mab (diário)        ║    ║  + produz: disparo_eventos           ║
  ║  • guardiao_campanha              ║    ║  + contratos: segmento_campanha_map  ║
  ║  • saude_operacional              ║    ║               cliente_jornada_status  ║
  ║  • consumidor_conversao           ║    ║                                      ║
  ╚═══════════════════════════════════╝    ╚══════════════════════════════════════╝
```

---

## 3. Hierarquia de Entidades

```
  Campanha (1) ──▶ (N) Jornada ──▶ (N) Peça
       │                  │
       │                  └──▶ (1) Segmento Entrada (S1)
       │
       └──▶ Vigencia + Limite Envios

  Jornada ─▶ Grafo (React Flow) ─▶ Nós:
    entrada | enviar_peca | esperar | condicao/split |
    ab_split | acao | saida | (loops com limite)

  Disparo Avulso (DAV): standalone ou vinculado a campanha
```

---

## 4. Stack Tecnológica

| Camada | Tecnologia | Detalhe |
|---|---|---|
| **Runtime** | Databricks App | uvicorn, porta 8000 |
| **Backend** | FastAPI + Pydantic v2 | Python 3.11+ |
| **Frontend** | React + Vite + MUI | shared-ui (paleta Bradesco) |
| **Editor Email** | GrapesJS + MJML | Drag-drop, HTML responsivo |
| **Editor Jornada** | React Flow | Canvas visual com 7 tipos de nó |
| **Dados** | Delta Lake + Unity Catalog | Catálogo `plataforma`, schema `engagement` |
| **Compute** | SQL Warehouse Serverless | Queries parametrizadas |
| **Jobs** | Databricks Jobs | 7 jobs (orquestrador, motores, MAB, saúde) |
| **Providers** | SMTP + Meta Cloud API | Email real + WhatsApp (templates HSM) |
| **Otimização** | Thompson Sampling | stdlib random.betavariate (Beta distribution) |
| **Autenticação** | Service Principal + RBAC | `governanca.usuarios_perfil` (sistema=engagement) |

---

## 5. Contratos Consumidos (de outros sistemas)

| Contrato | Origem | Uso no S3 |
|---|---|---|
| `seg_resultado_corrente` | S1 (SegmentHub) | Público elegível para campanhas |
| `seg_definicao` | S1 | Metadata do segmento (nome) |
| `seg_destino` | S1 | Flag `destino_sistema3` |
| `governanca.consentimento` | S0 | Opt-out por canal |
| `customer_features_wide` | S1 (metadata) | Variáveis de personalização |
| `golden_record` | S0 (core_cliente) | Email/telefone para disparo |
| `eventos.retorno_atendimento` | S2 (futuro) | Conversão real (desfecho_oferta) |

## 6. Contratos Produzidos (para outros sistemas)

| Contrato | Consumidor | Descrição |
|---|---|---|
| `segmento_campanha_map` (view) | S2 | Mapeia seg_id → campanha(s) digitais |
| `cliente_jornada_status` (view) | S2 | Posição do cliente na jornada |
| `tracking_disparo` | S2, S4 | Funil completo (enviado→converteu) |
| `disparo_eventos` | S2, S4 | Barramento de eventos |

---

## 7. Schemas do Unity Catalog

| Schema | Papel no S3 | Acesso |
|---|---|---|
| `plataforma.engagement` | Produção (campanhas, jornadas, peças, disparo, tracking, otimização) | Leitura + Escrita |
| `plataforma.segmentacao` | Consumo (seg_resultado_corrente, seg_destino) | Leitura (GRANT SELECT) |
| `plataforma.metadata` | Consumo (catalogo_caracteristicas → variáveis) | Leitura |
| `plataforma.governanca` | Consumo (consentimento, usuarios_perfil) | Leitura |
| `plataforma.core_cliente` | Consumo (golden_record → email/telefone) | Leitura |
| `plataforma.eventos` | Escrita (disparo_eventos) + Leitura (retorno_atendimento) | R/W |

---

## 8. Fluxo Principal (End-to-End)

```
  ┌────────────────────────── FLUXO END-TO-END S3 ──────────────────────────┐
  │                                                                            │
  │  FASE 1: CRIAÇÃO (analista no frontend)                                     │
  │  Campanha → Peças (editor visual) → Jornada (React Flow) → Aprovação       │
  │                                                                            │
  │  FASE 2: ATIVAÇÃO                                                           │
  │  Campanha ativa → Guardião valida vigência → Orquestrador seleciona entrada  │
  │                                                                            │
  │  FASE 3: ORQUESTRAÇÃO (Job periódico)                                       │
  │  seg_resultado_corrente → Consentimento → Waterfall → Capping → Fila        │
  │                                                                            │
  │  FASE 4: JORNADA (Job ~5min)                                               │
  │  Novos entram → Motor percorre grafo → enviar_peca → esperar → condição    │
  │  → fila_disparo                                                            │
  │                                                                            │
  │  FASE 5: DISPARO (Job ~5min)                                               │
  │  Fila → Re-valida governança → Renderiza → Provider (email/wpp) → Tracking  │
  │                                                                            │
  │  FASE 6: TRACKING + CONVERSÃO                                              │
  │  Pixel/webhook → aberto/clicou → retorno_atendimento (S2) → converteu      │
  │  MAB recalcula pesos → próximo ciclo usa pesos atualizados                  │
  │                                                                            │
  └────────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Estrutura de Diretórios

```
engagementhub/
├── app.yaml                     # Config Databricks App
├── requirements.txt             # Dependências Python
├── package.json / vite.config   # Config frontend
│
├── src/                         # BACKEND
│   ├── main.py                  # FastAPI + routers + /track/* + /webhook/*
│   ├── api/                     # Endpoints REST
│   │   ├── campanha.py          # CRUD + ciclo de vida
│   │   ├── peca.py              # Peças + aprovação + assets
│   │   ├── jornada.py           # CRUD + grafo + validação + preview
│   │   ├── disparo.py           # Fila de disparo
│   │   ├── avulso.py            # Disparo avulso (DAV)
│   │   ├── operacao.py          # Dashboard + alertas
│   │   └── admin.py             # Waterfall, capping, canais, janela, retry, etc
│   ├── core/                    # Lógica de negócio (chamada pelos Jobs)
│   │   ├── orquestrador.py      # 6 etapas (consentimento→waterfall→capping)
│   │   ├── motor_jornada.py     # Percorre grafo por cliente
│   │   ├── motor_disparo.py     # Consome fila, renderiza, dispara
│   │   ├── render_engine.py     # Resolve variáveis + MJML/template
│   │   ├── mab.py               # Thompson Sampling (numpy/scipy)
│   │   └── security.py          # OBO + RBAC
│   ├── providers/               # Conectores de canal (pluggáveis)
│   │   ├── base.py              # ABC: validar/renderizar/disparar/status
│   │   ├── email_provider.py    # SMTP (Mailtrap/Gmail)
│   │   └── whatsapp_provider.py # Meta Cloud API + HSM
│   ├── track/                   # Endpoints de rastreio (públicos)
│   │   ├── open.py              # Pixel 1x1
│   │   ├── click.py             # Redirect + tracking
│   │   └── webhooks.py          # Callbacks (Meta/email provider)
│   ├── models/                  # Pydantic schemas
│   └── db/                      # Cliente SQL (SDK)
│
├── frontend/                    # FRONTEND (React)
│   └── src/
│       ├── pages/               # 9 telas (Campanhas, Peças, Jornadas...)
│       ├── components/          # GrapesJS editor, React Flow canvas, etc
│       ├── api/                 # Clients HTTP
│       └── shared-ui/           # Cópia sincronizada do design system
│
└── (jobs em /databricks/jobs/s3_engagement/)
    ├── engagement_orquestrador   # Waterfall + capping + entrada
    ├── motor_jornada             # Percorre grafos (~5min)
    ├── motor_disparo             # Envia da fila (~5min)
    ├── otimizador_mab            # Recalcula pesos (diário)
    ├── guardiao_campanha         # Vigência (ativa/conclui por data)
    ├── saude_operacional         # Health checks
    └── consumidor_conversao      # Fecha conversão real (S2→S3)
```

---

## 10. Princípios de Design

```
  ┌─────────────────────────┐   ┌─────────────────────────┐
  │ GOVERNANÇA AUTOMÁTICA      │   │ PLUGABILIDADE             │
  │                         │   │                         │
  │ • Consentimento obrigat. │   │ • Novo canal = 1 provider │
  │ • Capping anti-fadiga    │   │   + 1 linha no catálogo  │
  │ • Waterfall (prioridade) │   │ • Interface ChannelProvider│
  │ • Janela de envio        │   │ • Zero mudança no core    │
  │ • Supressão logada       │   │                         │
  └─────────────────────────┘   └─────────────────────────┘

  ┌─────────────────────────┐   ┌─────────────────────────┐
  │ OTIMIZAÇÃO INTELIGENTE    │   │ RASTREABILIDADE           │
  │                         │   │                         │
  │ • MAB (Thompson Sampling)│   │ • Funil completo por envio│
  │ • Convergência automática│   │ • Supressão auditada      │
  │ • Tráfego mínimo garante │   │ • Tentativas registradas  │
  │   exploração            │   │ • Idempotência (envio_id) │
  │ • Fixar vencedora manual │   │ • Conversão real (S2)     │
  └─────────────────────────┘   └─────────────────────────┘
```

---

## 11. Índice da Documentação

| # | Documento | Conteúdo |
|---|---|---|
| 01 | **Este arquivo** | Visão geral, arquitetura, stack |
| 02 | [Schemas e Tabelas](02-SCHEMAS-TABELAS.md) | DDLs completas, colunas, relacionamentos |
| 03 | [Roadmap](ROADMAP-S3-ENGAGEMENTHUB.md) | 29 cartões (13 BACK + 7 JOBS + 9 FRONT) |

---

## 12. Status de Implementação (Agosto/2026)

| Módulo | Status | Endpoints | Detalhe |
|---|---|---|---|
| BACK-01 Fundação | ✅ | — | main.py, security, config, fake_client, seed (40 tabelas) |
| BACK-02 Campanha | ✅ | 9 | CRUD + ciclo (7 estados) + versionamento + guards |
| BACK-03 Peças | ✅ | 10 | CRUD + aprovação multi-etapa + render Jinja2 + variáveis |
| BACK-04 Canais | ✅ | 6 | CRUD + health check + providers Email/WhatsApp |
| BACK-05 Jornada | ✅ | 10 | CRUD + grafo_validator (8 etapas) + preview engine + ciclo |
| BACK-06 a 13 | ⏳ | — | Próximo: Orquestrador (Waterfall + Capping) |
| JOBS (7) | ⏳ | — | Aguarda BACK-06+ |
| FRONT (9) | ⏳ | — | Aguarda BACK completo |

**Total: 35 endpoints implementados** | 5/29 cards completos (17%)

### Endpoints por Módulo

```
/api/campanhas (9):
  GET, GET/{id}, POST, PUT/{id}
  POST /{id}/aprovar, /ativar, /pausar, /encerrar
  PUT /{id}/limite

/api/pecas (10):
  GET /variaveis, GET, GET/{id}, POST, PUT/{id}
  POST /{id}/submeter, /aprovar, /reprovar, /preview
  POST /assets (placeholder)

/api/canais (6):
  GET /providers, GET, GET/{id}, POST, PUT/{id}
  POST /{id}/health

/api/jornadas (10):
  GET, GET/{id}, POST, PUT/{id}
  POST /{id}/validar, /preview, /aprovar, /ativar, /pausar, /encerrar
```

---

*Documentação gerada a partir dos DDLs e roadmap validados em Agosto/2026.*
