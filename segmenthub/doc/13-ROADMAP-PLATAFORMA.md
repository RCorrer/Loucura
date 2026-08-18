# Roadmap da Plataforma CDP

> Status consolidado das fases, cartões do S1 (reconciliados com implementação real),  
> índice de roadmaps pendentes e convenções globais.

---

## 1. Fases do Projeto

```
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │  PROGRESSO DAS FASES                                                         │
  │                                                                               │
  │  Fase A: DDLs (29 tabelas)                   ███████████████  COMPLETO   │
  │  Fase B: ESTRUTURA-PROJETO                   ███████████████  COMPLETO   │
  │  Fase C: CONTRATOS + MESTRE                  ███████████████  COMPLETO   │
  │  Fase D: ROADMAPs por sistema                                                │
  │    ├─ S1 (SegmentHub)                        ███████████████  COMPLETO   │
  │    ├─ S3 (EngagementHub)                     ░░░░░░░░░░░░░░░  PRÓXIMO    │
  │    ├─ S2 (ClientView 360)                    ░░░░░░░░░░░░░░░  PENDENTE   │
  │    └─ S4 (CompassHub)                        ░░░░░░░░░░░░░░░  PENDENTE   │
  │  Fase E: COMO-PROSSEGUIR                     ░░░░░░░░░░░░░░░  PENDENTE   │
  │                                                                               │
  └─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Roadmap S1 — SegmentHub (Reconciliado)

> **IMPORTANTE:** A implementação real evoluiu da proposta original (v1 → v2).  
> Este roadmap reflete a **realidade implementada**, não o plano inicial.

### Evoluções v1 → v2 (já aplicadas)

| Aspecto | Roadmap Original (v1) | Implementação Real (v2) |
|---|---|---|
| Jobs | 4 jobs centrais parametrizados | **Job-per-segment** (1 job por seg. ativa) |
| Vigência | Job `seg_guardiao` separado | Schedule nativo do Databricks Jobs |
| Saúde | Job `seg_saude` separado | `seg_saude_consolidador` (infra) + saúde inline no `seg_exec` |
| Overlap | Job `seg_overlap` O(n²) | **Removido** (inviável com ~1000 segs) |
| Arquitetura back | Monolítico `core/` | Camadas `api/ → services/ → repositories/ → db/` |
| Job management | Chamada direta nos endpoints | `JobManagerService` (SDK: create/pause/delete jobs) |

### Cartões BACK (12 implementados)

```
  ╔══════════════════════════════════════════════════════════════════════╗
  ║  S1-BACK-01  Fundação (db/security/main)                  ✓ IMPLEMENTADO  ║
  ║  S1-BACK-02  Metadata Service                              ✓ IMPLEMENTADO  ║
  ║  S1-BACK-03  Query Engine + Validator (NÚCLEO)             ✓ IMPLEMENTADO  ║
  ║  S1-BACK-04  Estimativa (HyperLogLog)                      ✓ IMPLEMENTADO  ║
  ║  S1-BACK-05  Segmentação CRUD + Ciclo de vida             ✓ IMPLEMENTADO  ║
  ║  S1-BACK-06  Versões / Histórico / Timeline               ✓ IMPLEMENTADO  ║
  ║  S1-BACK-07  Destino / Vigência                            ✓ IMPLEMENTADO  ║
  ║  S1-BACK-08  Comentários / Notificações                   ✓ IMPLEMENTADO  ║
  ║  S1-BACK-09  Saúde (leitura)                               ✓ IMPLEMENTADO  ║
  ║  S1-BACK-10  Chatbot (MCP + Agent Framework + VS)          ✓ IMPLEMENTADO  ║
  ║  S1-BACK-11  Governança de Catálogo (admin) + Histórico   ✓ IMPLEMENTADO  ║
  ║  S1-BACK-12  Ajuste Metadata público (flags fora)          ✓ IMPLEMENTADO  ║
  ╚══════════════════════════════════════════════════════════════════════╝
```

### Cartões JOBS (2 implementados — arquitetura v2)

```
  ╔══════════════════════════════════════════════════════════════════════╗
  ║  seg_exec                  Executa 1 seg (6 steps + MERGE)  ✓ IMPLEMENTADO  ║
  ║  seg_saude_consolidador    Infra: health checks periódicos  ✓ IMPLEMENTADO  ║
  ║                                                                            ║
  ║  ~~seg_guardiao~~          REMOVIDO (schedule nativo)       ✘ DESCONTINUADO ║
  ║  ~~seg_overlap~~           REMOVIDO (O(n²) inviável)        ✘ DESCONTINUADO ║
  ╚══════════════════════════════════════════════════════════════════════╝
```

### Cartões FRONT (10 implementados)

```
  ╔══════════════════════════════════════════════════════════════════════╗
  ║  S1-FRONT-01  Shell + Lista de Segmentações                ✓ IMPLEMENTADO  ║
  ║  S1-FRONT-02  Builder (núcleo no-code)                     ✓ IMPLEMENTADO  ║
  ║  S1-FRONT-03  Estimativa em tempo real                     ✓ IMPLEMENTADO  ║
  ║  S1-FRONT-04  Documentação + Destino + Vigência            ✓ IMPLEMENTADO  ║
  ║  S1-FRONT-05  Validação/Aprovação + Detalhe                ✓ IMPLEMENTADO  ║
  ║  S1-FRONT-06  Timeline + Comentários                       ✓ IMPLEMENTADO  ║
  ║  S1-FRONT-07  Dashboard de Saúde                           ✓ IMPLEMENTADO  ║
  ║  S1-FRONT-08  Notificações (global)                        ✓ IMPLEMENTADO  ║
  ║  S1-FRONT-09  ChatBot (MCP)                                ✓ IMPLEMENTADO  ║
  ║  S1-FRONT-10  Admin de Catálogo + Histórico Governança     ✓ IMPLEMENTADO  ║
  ╚══════════════════════════════════════════════════════════════════════╝
```

### Melhorias pós-roadmap (implementadas)

```
  ╔══════════════════════════════════════════════════════════════════════╗
  ║  S1-FIX-01   Conector AND/OR interativo entre pares        ✓ IMPLEMENTADO  ║
  ║              → splitAtConnector.js + RuleNode.jsx                           ║
  ║              → Reestruturação automática da árvore ao mudar                ║
  ║                operator entre regras adjacentes                             ║
  ║              → flattenTree() normaliza nós redundantes                     ║
  ║              → Backend/Job: 0 mudanças (já recursivo)                      ║
  ║                                                                            ║
  ║  S1-FIX-02   Paleta Bradesco nos componentes de regras     ✓ IMPLEMENTADO  ║
  ║              → RuleNode.jsx, ExclusaoBuilder.jsx, RuleGroup.jsx            ║
  ║              → Removidos hexcodes MUI hardcoded                            ║
  ║              → Import tokens from shared-ui/theme/tokens.js                ║
  ║              → AND: info (#1565C0), OR: warning (#B26A00)                  ║
  ║              → Exclusão: error (#B00020), Surface: canvas (#F8F6F0)        ║
  ╚══════════════════════════════════════════════════════════════════════╝
```

### Total S1: **24 cartões** (12 BACK + 2 JOBS + 10 FRONT) + **2 fixes**

---

## 3. Mapa Tela → API (S1)

| Tela | Rota | APIs Consumidas |
|---|---|---|
| Lista | `/segmentacoes` | GET /segmentacoes; POST /{id}/clonar |
| Builder | `/segmentacoes/nova`, `/:id/editar` | GET /metadata/*; POST/PUT /segmentacoes |
| Estimativa | (no builder) | POST /estimativa/preview |
| Documentação | `/:id/documentacao` | PUT /segmentacoes/{id} |
| Destino | (fluxo salvar) | GET/PUT /{id}/destinos |
| Vigência | (fluxo salvar) | PUT /{id}/vigencia |
| Validação | `/:id/validar` | POST /{id}/validar, /aprovar, /ativar... |
| Detalhe | `/:id` | GET /{id}; /{id}/execucoes; /{id}/destinos |
| Timeline | `/:id/timeline` | GET /{id}/timeline |
| Comentários | (aba detalhe) | GET/POST /{id}/comentarios |
| Saúde | `/saude` | GET /saude; /saude/{id} |
| Notificações | (sininho) | GET /notificacoes; PUT /{id}/lida |
| ChatBot | `/chat` | POST /chat/mensagem |
| Admin Catálogo | `/admin/catalogo` | GET/PUT /metadata/admin/* |
| Hist. Governança | `/admin/catalogo/historico` | GET /metadata/admin/historico |

---

## 4. Convenções Globais

### Padrões de Código

```
  ┌───────────────────────────────────────────────────────────────────────────┐
  │  CONVENÇÕES GLOBAIS                                                           │
  │                                                                               │
  │  Backend:                                                                     │
  │   • FastAPI + Pydantic v2                                                    │
  │   • Camadas: api/ → services/ → repositories/ → db/                          │
  │   • SQL sempre parametrizado (nunca interpola)                                │
  │   • RBAC via governanca.usuarios_perfil                                      │
  │   • Resposta padrão: {data, meta} ou {detail} para erros                     │
  │   • Pydantic valida; service executa; repository persiste                    │
  │                                                                               │
  │  Frontend:                                                                    │
  │   • React + Vite + MUI (design system: shared-ui)                            │
  │   • useApi (base /api + erro padrão)                                         │
  │   • Estados loading/erro/vazio obrigatórios                                  │
  │   • Cor de marca só em ação primária                                         │
  │   • Sem lógica de negócio no front                                           │
  │                                                                               │
  │  Jobs:                                                                        │
  │   • Notebooks parametrizados                                                 │
  │   • S1: job-per-segment (S1-SEG-{seg_codigo})                                │
  │   • Infra: S1-INFRA-{funcao}                                                 │
  │   • Timezone: America/Sao_Paulo                                              │
  │   • Eventos em eventos.seg_eventos (processado=false)                        │
  │                                                                               │
  │  Dados:                                                                       │
  │   • Unity Catalog: catálogo `plataforma`                                     │
  │   • Delta Lake com Liquid Clustering                                         │
  │   • Bloom Filter Index em PKs                                                │
  │   • Desacoplamento: GRANT SELECT entre sistemas                              │
  │                                                                               │
  └───────────────────────────────────────────────────────────────────────────┘
```

### Nomenclaturas

| Entidade | Formato | Exemplo |
|---|---|---|
| seg_id | UUID | `seg_abc123` |
| seg_codigo | `SEG-{NOME_20}-{HEX_4}` | `SEG-ALTA-RENDA-3F2A` |
| exec_id | `exec_{seg_id}_{YYYYMMDD_HHMMSS}` | `exec_seg_abc_20260815_103000` |
| hist_id | `hist_YYYYMMDD_HHMMSS_xxxx` | `hist_20260815_103000_a1b2` |
| Job per-seg | `S1-SEG-{seg_codigo}` | `S1-SEG-ALTA-RENDA-3F2A` |
| Job infra | `S1-INFRA-{funcao}` | `S1-INFRA-SAUDE-CONSOLIDADOR` |

---

## 5. Roadmaps Pendentes

### S3 — EngagementHub (PRÓXIMO)

Estimativa: ~13 BACK + ~7 JOBS + ~9 FRONT = **~29 cartões** (o maior sistema)

| Módulo | Scope |
|---|---|
| Campanhas | CRUD + configuração + canais |
| Jornadas | Editor visual (React Flow) + motor |
| Peças | Editor MJML (GrapesJS) + render engine |
| Disparos | Orquestrador + providers (email/whatsapp) |
| Tracking | Pixel/redirect + webhooks |
| Otimização | MAB (Multi-Armed Bandit) |
| Operação | Monitoring operacional |

### S2 — ClientView 360

Estimativa: ~10 BACK + ~3 JOBS + ~8 FRONT = **~21 cartões**

| Módulo | Scope |
|---|---|
| Carteira + RLS | OBO, encarteiramento, filtragem |
| Visão 360 | Blocos dinâmicos, config admin |
| Priorizacao | Engine configurável |
| Interações | Registro + desfecho + eventos |
| Chatbot | Tools sob OBO (RLS) |

### S4 — CompassHub

Estimativa: ~6 BACK + ~6 JOBS + ~6 FRONT = **~18 cartões**

| Módulo | Scope |
|---|---|
| KPIs/OKRs | Definição + cálculo automático |
| Insights | Engine de detecção automática |
| Relatórios | PDF + AI/BI Dashboards |
| Alertas | Regras configuráveis |
| Custos | Tracking de DBU/custo |

---

## 6. Ordem de Execução Recomendada

```
  ┌─────────────────────────────────────────────────────────────────────┐
  │  DENTRO DE CADA SISTEMA                                                   │
  │                                                                           │
  │  DDL → BACK (01→02→03→04→05→...) → JOBS → FRONT (01→02→...)            │
  │                                                                           │
  │  ENTRE SISTEMAS (deploy vertical)                                         │
  │                                                                           │
  │  S1 (COMPLETO) → S3 (próximo) → S2 (consome S1+S3) → S4 (consome todos)  │
  └─────────────────────────────────────────────────────────────────────┘
```

---

## 7. Índice da Documentação

| # | Arquivo | Escopo |
|---|---|---|
| 01 | `01-VISAO-GERAL.md` | Visão executiva, stack, estrutura S1 |
| 02 | `02-SCHEMAS-TABELAS.md` | Modelo de dados completo (ER + DDLs) |
| 03 | `03-ARQUITETURA-BACKEND.md` | Camadas, padrões, dependências |
| 04 | `04-CICLO-VIDA-ESTADOS.md` | Máquina de estados, versionamento |
| 05 | `05-JOBS-EXECUCAO.md` | Job-per-segment, notebooks, escala |
| 06 | `06-API-ENDPOINTS.md` | Referência completa da API REST |
| 07 | `07-INTEGRACAO-CONTRATOS.md` | Contratos produzidos/consumidos pelo S1 |
| 08 | `08-SEGURANCA-RBAC.md` | OBO, RBAC, anti-injection |
| 09 | `09-FLUXOS-SISTEMA.md` | Fluxos end-to-end do S1 |
| 10 | `10-OPERADORES-SISTEMA.md` | 17 operadores, case-insensitive |
| 11 | `11-CONTRATOS-DADOS-EVENTOS.md` | **Plataforma:** integração entre 4 sistemas |
| 12 | `12-ESTRUTURA-PROJETO.md` | **Plataforma:** árvore de diretórios |
| 13 | `13-ROADMAP-PLATAFORMA.md` | **Plataforma:** roadmap consolidado |

**Organização:**
* 01–10: Documentação técnica do S1 (fonte de verdade para implementação)
* 11–13: Documentação de plataforma (visão cross-system)

---

## 8. Definition of Done (Global)

| Camada | DoD |
|---|---|
| DDL | Tabela criada no Unity Catalog; Bloom Filter + Cluster By aplicados |
| BACK | Endpoint responde corretamente; RBAC valida perfil; SQL parametrizado |
| JOB | Roda sobre dado sintético; MERGE atômico; evento emitido; link job_run_url |
| FRONT | Tela funcional com dados reais; loading/erro/vazio; design system respeitado |

---

*Referências cruzadas: [11-CONTRATOS](./11-CONTRATOS-DADOS-EVENTOS.md) | [12-ESTRUTURA](./12-ESTRUTURA-PROJETO.md) | [05-JOBS](./05-JOBS-EXECUCAO.md) | [JOBS_MANIFEST](/databricks/jobs/s1_segmenthub/JOBS_MANIFEST.md)*