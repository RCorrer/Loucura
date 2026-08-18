# Fluxos do Sistema — SegmentHub (S1)

> Documentação técnica de cada fluxo end-to-end do sistema, da interação do usuário até a persistência final.

---

## F1 — Criação de Segmentação

O analista monta regras no Builder e salva. O sistema persiste a definição com status `rascunho`.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  BuilderSegmentacao.jsx                                                        │
│    │                                                                          │
│    ├─ TemaMenu: seleciona campo → `{ campo_id: caracteristica_id, op, value }` │
│    ├─ RuleNode.jsx renderiza árvore recursiva (AND/OR aninhado)                │
│    ├─ Conector interativo entre pares: ao clicar chip entre regras,             │
│    │    splitAtConnector() reestrutura árvore + flattenTree() normaliza        │
│    ├─ handleSalvar:                                                            │
│    │     1. cleanTree(regrasInclusao) — remove folhas inválidas recursivamente  │
│    │     2. coerceValue() — "18"→number, "SP,RJ"→["SP","RJ"], "true"→bool    │
│    │     3. temFolhaValida() — verifica se restou ao menos 1 folha             │
│    │     4. Monta payload: { nome, regras_json: { publico_base, inclusao, exclusao } }
│    │                                                                          │
│    └─ POST /api/segmentacoes                                                   │
└────────────────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  Backend (segmentacao.py → SegmentacaoService)                                  │
│    │                                                                          │
│    ├─ Pydantic valida: SegmentacaoCreateDTO + RegrasJson + RegraNo recursivo   │
│    ├─ RegraValidator.validar_regras():                                         │
│    │     • Verifica publico_base existe no catalogo_publicos                    │
│    │     • Percorre árvore recursivamente                                      │
│    │     • Valida campo_id no catálogo (ativo=true)                             │
│    │     • Valida operador permitido para o campo                               │
│    │     • Valida tipo do valor (numeric, categorical, boolean, date)           │
│    ├─ Gera seg_id (uuid), seg_codigo (SEG-NOME-HASH), seg_slug                  │
│    ├─ INSERT seg_definicao (status='rascunho', versao_atual=1)                  │
│    └─ INSERT seg_versao (versao=1, regras_json, motivo="Versão inicial")        │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

**Estrutura do `regras_json` salvo:**

```json
{
  "publico_base": "pub_pf_ativo",
  "inclusao": {
    "operator": "AND",
    "rules": [
      { "campo_id": "caract_idade", "op": ">", "value": 18 },
      {
        "operator": "OR",
        "rules": [
          { "campo_id": "caract_uf", "op": "in", "value": ["SP", "RJ"] },
          { "campo_id": "caract_renda", "op": ">=", "value": 5000 }
        ]
      }
    ]
  },
  "exclusao": {
    "operator": "AND",
    "rules": [
      { "campo_id": "caract_inadimplente", "op": "=", "value": true }
    ]
  }
}
```

---

## F2 — Estimativa de Público em Tempo Real

O badge de estimativa calcula quantos clientes seriam atingidos pelas regras ANTES de salvar.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  EstimativaBadge.jsx                                                  │
│    │                                                                  │
│    ├─ podEstimar(): percorre árvore verificando se há folhas válidas    │
│    ├─ Debounce 800ms + AbortController (cancela requests anteriores)   │
│    ├─ prepararRegras(): split vírgula, coerce numéricos/booleans       │
│    └─ POST /api/estimativa/preview  { publico_base, inclusao, exclusao }│
└──────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  Backend: estimativa.py → EstimativaService                            │
│    │                                                                  │
│    ├─ Pydantic valida RegrasJson                                       │
│    ├─ RegraValidator.validar_regras() — rejeita 422 se inválido         │
│    ├─ QueryEngine.generate_estimativa_query(regras):                    │
│    │     1. _carregar_catalogo() — cache de campos (WHERE ativo=true)   │
│    │     2. _carregar_publicos() — cache de públicos (WHERE ativo=true)  │
│    │     3. Resolve publico_base → tabela_fisica + join_key              │
│    │     4. _build_no(inclusao) recursivo:                               │
│    │          • _resolver_campo(campo_id) → tabela_fisica.campo_fisico   │
│    │          • Registra tabela em _tabelas_usadas (para JOINs)          │
│    │          • Gera condição parametrizada (?, ?, ...)                   │
│    │     5. _build_no(exclusao) → `AND NOT (...)`                       │
│    │     6. Monta JOINs dinâmicos para tabelas != tabela_base            │
│    │     7. SELECT approx_count_distinct(join_key) FROM ...              │
│    ├─ EstimativaRepository.executar_estimativa(sql, params)              │
│    └─ Retorna { estimativa: 15420, tempo_ms: 230 }                       │
└──────────────────────────────────────────────────────────────────────────┘
```

**Resolução de campos (campo_id → físico):**

```
{ campo_id: "caract_idade" }        catalogo_caracteristicas            SQL gerado
         │                    →  campo_fisico: "idade"         →  customer_features_wide.idade > ?
         │                       tabela_fisica: "...customer_features_wide"
         │                       join_key: "cpf_cnpj"
```

Se a regra usa campos de N tabelas distintas, o engine gera N-1 LEFT JOINs automaticamente.

---

## F3 — Execução Real (Job seg_exec)

Após ativação, o Databricks Job executa periodicamente via cron ou sob demanda.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  Databricks Job: S1-SEG-{seg_codigo}                                           │
│  Notebook: seg_exec.py  |  Parâmetro: seg_id                                  │
│    │                                                                         │
│    ├─ Cell 1: Lê seg_definicao (regras_json, publico_base_id)                  │
│    ├─ Cell 2: Carrega catálogo (WHERE ativo=true) e catalogo_publicos          │
│    ├─ Cell 3: Resolve publico_base → tabela_fisica + join_key                  │
│    ├─ Cell 4: build_condition() recursivo:                                    │
│    │     • Resolve campo_id → tabela_fisica.campo_fisico                       │
│    │     • sql_val(): bool→true/false, string→escape ', numeric→sem aspas    │
│    │     • extrair_tabelas() → set de (tabela_fisica, join_key)                │
│    │     • Monta LEFT JOINs dinâmicos                                         │
│    │     • Exclusão: AND NOT (...)                                             │
│    ├─ Cell 5: spark.sql(query) → DataFrame com cpf_cnpj                       │
│    ├─ Cell 6: MERGE INTO seg_resultado_corrente (upsert por seg_id+cpf_cnpj)  │
│    ├─ Cell 7: INSERT seg_execucao (status=sucesso, qtd_clientes)              │
│    ├─ Cell 8: INSERT seg_eventos (tipo=executada, processado=false)           │
│    └─ Cell 9: UPDATE seg_saude (publico_atual, ultima_verificacao)            │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Diferenças entre seg_exec (Spark) e query_engine (SQL Warehouse):**

| Aspecto | seg_exec | query_engine |
|---|---|---|
| Ambiente | Spark cluster (Job) | SQL Warehouse (serverless) |
| Parâmetros | Valores inline com `sql_val()` | Placeholders `?` posicionais |
| Resultado | MERGE em Delta | COUNT retornado ao frontend |
| Propósito | Produção: gera a base de clientes | Preview: estimativa rápida |

---

## F4 — Ciclo de Vida (Máquina de Estados)

Cada segmentação percorre um ciclo de estados controlado pelo `SegmentacaoService.transicionar_status()`.

```
                              ┌─────────────────┐
                              │    RASCUNHO    │
                              └────────┬────────┘
                                       │ enviar-aprovacao
                                       ▼
                              ┌─────────────────┐
                              │  EM_APROVACAO  │
                              └────────┬────────┘
                                       │ aprovar (admin + checklist)
                                       ▼
                              ┌─────────────────┐
                              │    APROVADA    │
                              └────────┬────────┘
                                       │ ativar (cria Job Databricks)
                                       ▼
                    ┌─────────┬─────────────────┬──────────┐
                    │         │      ATIVA      │          │
                    │         └─────────────────┘          │
                    ▼                                        ▼
          ┌─────────────────┐                    ┌─────────────────┐
          │     PAUSADA     │                    │    ENCERRADA   │
          └─────────┬───────┘                    └───────┬─────────┘
                    │  reativar                          │ reativar
                    └────────── → ATIVA ← ───────────┘

                              ┌─────────────────┐
                    ────────▶│    ARQUIVADA   │  (estado terminal)
                              └─────────────────┘
          (de qualquer estado exceto já arquivada)
```

**Mapa de transições (código-fonte):**

```python
transicoes = {
    "rascunho":     ["em_aprovacao", "arquivada"],
    "em_aprovacao": ["aprovada", "rascunho", "arquivada"],
    "aprovada":     ["ativa", "arquivada"],
    "ativa":        ["pausada", "encerrada", "arquivada"],
    "pausada":      ["ativa", "encerrada", "arquivada"],
    "encerrada":    ["ativa", "arquivada"],
}
```

**Integração com Jobs (pós-transição):**

| Transição | Ação no Databricks Jobs |
|---|---|
| → `ativa` (de aprovada/pausada/encerrada) | Cria job (se não existe) ou restaura schedule |
| → `pausada` | Remove schedule do job (job continua existindo) |
| → `encerrada` / `arquivada` | Deleta o job completamente |

---

## F5 — Aprovação (ValidationModal)

Admin valida e aprova uma segmentação em aprovação. Separação intencional: aprovar ≠ ativar.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  DetalheSegmentacao.jsx (status = 'em_aprovacao')                      │
│    │                                                                  │
│    └─ Botão "Validar e Aprovar" → abre ValidationModal                  │
└──────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  ValidationModal.jsx                                                  │
│    │                                                                  │
│    ├─ Ao abrir: POST /segmentacoes/:id/validar                          │
│    │     • Valida regras + gera resumo legível                           │
│    │     • Exibe: regras, destino, vigência, estimativa                  │
│    ├─ Checklist obrigatório (5 itens):                                   │
│    │     • Regras revisadas    • Destino definido    • Vigência ok       │
│    │     • Documentação ok     • Público validado                        │
│    ├─ Botão "Aprovar" (só habilitado se tudo checkado + valido):         │
│    │     → POST /segmentacoes/:id/aprovar (body: checklist)             │
│    │     → Status muda: em_aprovacao → aprovada                        │
│    │     → Grava aprovado_por + aprovado_em + checklist_validacao_json   │
│    └─ onAprovado() → reload página                                      │
└──────────────────────────────────────────────────────────────────────────┘
         │
         ▼  (reload mostra status 'aprovada')
┌──────────────────────────────────────────────────────────────────────────┐
│  DetalheSegmentacao.jsx (status = 'aprovada')                          │
│    │                                                                  │
│    ├─ Botão "Ativar" → POST /segmentacoes/:id/ativar                    │
│    │     → Cria Databricks Job com schedule                            │
│    │     → Status: aprovada → ativa                                   │
│    └─ Botão "Arquivar" → soft-delete                                    │
└──────────────────────────────────────────────────────────────────────────┘
```

**Por que separar aprovada de ativa?** O admin pode aprovar a lógica hoje e agendar a ativação para uma data futura. A criação do Job só acontece na ativação.

---

## F6 — Gerenciamento de Jobs (JobManagerService)

Cada segmentação ativa possui 1 Databricks Job dedicado (arquitetura job-per-segment).

```
┌──────────────────────────────────────────────────────────────────────────┐
│  JobManagerService (databricks-sdk)                                    │
│                                                                      │
│  criar_job(seg_id, seg_codigo, cron):                                 │
│    • Nome: S1-SEG-{seg_codigo}                                        │
│    • Task: NotebookTask(seg_exec, params={seg_id, origem=agendada})   │
│    • Schedule: CronSchedule(quartz, timezone=America/Sao_Paulo)       │
│    • max_concurrent_runs: 1  |  queue: enabled                        │
│    • Tags: {plataforma, seg_id, area, owner}                          │
│    • Notifications: on_failure → email_contato                        │
│                                                                      │
│  pausar_job(job_id):     jobs.update(schedule=None)                   │
│  reativar_job(job_id):   jobs.update(schedule=CronSchedule(...))      │
│  deletar_job(job_id):    jobs.delete(job_id)                          │
│  executar_agora(job_id): jobs.run_now(params={seg_id, origem=manual}) │
│  atualizar_schedule():   jobs.update(schedule=novo_cron)              │
└──────────────────────────────────────────────────────────────────────────┘
```

**Resiliência:** Se o JobManager falha (ex: API Databricks fora), a transição de status NÃO é revertida. O consolidador de saúde detectará a inconsistência (status=ativa mas sem job rodando).

---

## F7 — Governança de Catálogo (Admin → Flags → S2/S3)

Admin controla 3 flags independentes por campo, diretamente na tabela inline.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  AdminCatalogo.jsx                                                    │
│                                                                      │
│  ┌──────────┬──────┬────┬────┐                                        │
│  │  Campo   │ Ativo │ S2 │ S3 │  ← Switches editáveis inline          │
│  ├──────────┼──────┼────┼────┤                                        │
│  │ Idade    │  ⬤   │ ⬤  │ ⬤  │                                        │
│  │ Renda    │  ⬤   │ ○  │ ⬤  │  ← visível em S3 mas não S2           │
│  │ Score    │  ○   │ ○  │ ○  │  ← desativado globalmente              │
│  └──────────┴──────┴────┴────┘                                        │
│                                                                      │
│  handleToggleFlag(campo, 'usavel_em_peca'):                           │
│    → PUT /api/metadata/admin/campos/{id}/flags                        │
│    → Body: { "usavel_em_peca": true }  (update parcial)               │
└──────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  MetadataAdminService                                                 │
│    │                                                                  │
│    ├─ buscar_campo_por_id() — lê estado atual do campo                  │
│    ├─ Compara estado anterior vs novo (detecta o que mudou)             │
│    ├─ Repository.atualizar_flags(id, set_params):                       │
│    │     UPDATE catalogo_caracteristicas SET flag = ? WHERE id = ?      │
│    │     (params: SET values PRIMEIRO, WHERE id POR ÚLTIMO)             │
│    └─ _gravar_historico() per-flag alterada:                             │
│         INSERT governanca_hist (acao, sistema_alvo, valor_anterior...)  │
└──────────────────────────────────────────────────────────────────────────┘
```

**Independência das flags:**
- `ativo` → controla S1 (TemaMenu + engines SQL)
- `usavel_em_visao360` → controla S2 (lido via GRANT SELECT)
- `usavel_em_peca` → controla S3 (lido via GRANT SELECT)
- Toggle de uma NÃO afeta as outras

---

## F8 — Segurança e RBAC

Autenticação via header OBO do Databricks Apps; autorização por perfil.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Request HTTP                                                         │
│    │                                                                  │
│    ├─ Header: X-Forwarded-Email (injetado pelo Databricks Apps proxy)  │
│    │  (ou DEV_USER em desenvolvimento)                                 │
│    │                                                                  │
│    └─ Depends(require_perfil(["admin", "analista"]))                    │
└──────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  security.py: get_current_user()                                      │
│    │                                                                  │
│    ├─ Extrai email do header X-Forwarded-Email                         │
│    ├─ SELECT perfil FROM governanca.usuarios_perfil                    │
│    │   WHERE usuario_id = ? AND sistema = 'segmenthub' AND ativo = true│
│    ├─ Retorna: { usuario_id, perfil }                                  │
│    └─ Fallback DEV: assume 'admin' (só fora de produção)               │
└──────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  require_perfil(["admin"]):                                            │
│    • user.perfil IN perfis_permitidos? → 200                          │
│    • Não? → 403 "Acesso negado. Perfil X não permitido"               │
│    • Sem user? → 401 "Não autenticado"                                 │
└──────────────────────────────────────────────────────────────────────────┘
```

**Permissões por endpoint:**

| Endpoint | Perfis permitidos |
|---|---|
| POST /segmentacoes (criar) | admin, analista |
| POST /:id/aprovar | **admin** |
| POST /:id/ativar, pausar, reativar, encerrar, executar | admin, analista |
| PUT /metadata/admin/campos/:id/flags | **admin** |
| GET /metadata/* (leitura catálogo) | admin, analista |

---

## F9 — Edição de Segmentação Existente

Lógica difere conforme status: rascunho edita inline; ativa cria nova versão draft.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  PUT /segmentacoes/:id                                                 │
│    │                                                                  │
│    ├─ Se status IN (rascunho, em_aprovacao):                            │
│    │     • Valida regras novas                                         │
│    │     • UPDATE seg_definicao.regras_json direto                      │
│    │     • Atualiza seg_versao (mesma versão)                            │
│    │                                                                  │
│    ├─ Se status == ativa:                                              │
│    │     • Valida regras novas                                         │
│    │     • INSERT seg_versao (versao+1, status=draft)                   │
│    │     • NÃO altera versao_atual nem status                           │
│    │     • Produção continua rodando com versão anterior                │
│    │     • Nova versão só entra quando aprovada                        │
│    │                                                                  │
│    └─ Campos não-regras (nome, descricao, tags):                        │
│         • Atualiza direto independente do status                        │
└──────────────────────────────────────────────────────────────────────────┘
```

**Versionamento:** O sistema mantém histórico completo de todas as versões em `seg_versao`. Cada versão registra: quem alterou, quando, motivo, e snapshot completo do `regras_json`.

---

## F10 — Destinos e Vigência

Definem para ONDE o público vai e QUANDO a segmentação executa.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  DestinoSelector.jsx                                                  │
│                                                                      │
│    Switch "Sistema 2 (Humano)"   ── habilitado: true/false             │
│    Switch "Sistema 3 (Digital)"  ── habilitado: true/false             │
│                                                                      │
│    → PUT /segmentacoes/:id/destinos                                  │
│    → Body: [{ destino: "sistema2", habilitado: true },               │
│              { destino: "sistema3", habilitado: false }]              │
└──────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  Backend                                                              │
│    • Valida destino IN ["sistema2", "sistema3"]                        │
│    • UPSERT seg_destino (merge por seg_id + destino)                   │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│  Vigência (PUT /segmentacoes/:id/vigencia)                             │
│                                                                      │
│    Body: { vigencia_inicio, vigencia_fim, agendamento_cron }          │
│                                                                      │
│    Se cron mudou E segmentação está ativa:                            │
│      → JobManager.atualizar_schedule(job_id, novo_cron)               │
│      → Atualiza schedule do job no Databricks em real-time            │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## F11 — Saúde (Consolidador + Dashboard)

Job separado (`seg_saude_consolidador`) roda periodicamente e calcula métricas de saúde.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  seg_saude_consolidador (Notebook Job)                                 │
│    │                                                                  │
│    ├─ Para cada segmentação ativa:                                      │
│    │     • COUNT resultado_corrente → publico_atual                     │
│    │     • Compara com publico_anterior → variacao_publico_pct          │
│    │     • Conta execuções últimos 7d → taxa_sucesso_exec (0-100)       │
│    │     • Deriva health_status: healthy / warning / critical           │
│    └─ MERGE INTO seg_saude                                             │
└──────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  DashboardSaude.jsx                                                   │
│    │                                                                  │
│    ├─ GET /api/saude → lista com health per-segmentação                 │
│    ├─ Cards: total ativas, healthy, warning, critical                  │
│    ├─ Tabela com filtros e ordenação                                    │
│    └─ Link para DetalheSegmentacao por item                             │
└──────────────────────────────────────────────────────────────────────────┘
```

**Regras de health_status:**

| Condição | Status |
|---|---|
| taxa_sucesso >= 90% E variação < 30% | `healthy` |
| taxa_sucesso < 90% OU variação >= 30% | `warning` |
| taxa_sucesso < 50% OU 3+ falhas consecutivas | `critical` |

---

## F12 — Timeline e Auditoria

Mescla 3 fontes em uma única timeline ordenada por data.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  GET /segmentacoes/:id/timeline                                       │
│                                                                      │
│  Fontes:                                                             │
│    • seg_versao  → tipo: "versao"   (quem editou, quando, motivo)     │
│    • seg_execucao → tipo: "execucao" (quando, status, qtd_clientes)   │
│    • seg_historico_estado → tipo: "estado" (de → para, quem, motivo)  │
│                                                                      │
│  Merge + sort DESC por data → timeline unificada                     │
└──────────────────────────────────────────────────────────────────────────┘
```

**Exemplo de timeline renderizada:**

```
15/07 14:30  🟢 Execução #12 — 15.420 clientes (sucesso)
15/07 09:00  🟢 Execução #11 — 15.380 clientes (sucesso)
14/07 11:15  🟡 Estado: aprovada → ativa (por admin@bradesco.com.br)
14/07 10:00  🟡 Estado: em_aprovacao → aprovada (por admin@bradesco.com.br)
13/07 16:45  📝 Versão 2 — "Ajuste no filtro de renda" (por analista@bradesco.com.br)
12/07 09:30  📝 Versão 1 — "Versão inicial" (por analista@bradesco.com.br)
```

---

## F13 — Clonagem

Permite duplicar uma segmentação existente como ponto de partida.

```
POST /segmentacoes/:id/clonar  { nome?, descricao?, owner?, area_responsavel? }
     │
     ▼
  SegmentacaoService.clonar():
    1. Busca original completo
    2. Protege regras_json (se list/None → {})
    3. Cria SegmentacaoCreateDTO com dados do original + overrides
    4. Chama self.criar() → novo seg_id, status=rascunho
    5. Clone herda: regras, objetivo, tags, público_base, documentação
    6. Clone NÃO herda: status (sempre rascunho), job, execuções, histórico
```

---

## F14 — Eventos para S3 (Integração Assíncrona)

Comunicação entre S1 e S3 via tabela de eventos (pull-based, não push).

```
┌──────────────┐     ┌────────────────────────────┐     ┌──────────────┐
│  S1 (produz)  │ ──▶ │  seg_eventos (Delta)         │ ──▶ │  S3 (consome) │
└──────────────┘     └────────────────────────────┘     └──────────────┘

S1 insere:                        S3 lê:
  tipo_evento = 'executada'         WHERE processado = false
  processado = false                  AND destino = 'sistema3'
  payload_json = {...}              Marca processado = true após consumir
```

**Contrato de evento:**

```json
{
  "seg_id": "seg_abc123",
  "seg_codigo": "SEG-ALTA-RENDA-3F2A",
  "tipo_evento": "executada",
  "versao_usada": 2,
  "qtd_clientes": 15000,
  "destino": "sistema3",
  "processado": false,
  "criado_em": "2025-07-15T14:30:00Z"
}
```

**Tipos de evento:**

| Evento | Quem consome | Significado |
|---|---|---|
| `executada` | S3 | Público atualizado — pode disparar campanha |
| `publicada` | S3 | Segmentação nova disponível |
| `pausada` / `encerrada` | S4 | Acompanhamento (não exige ação) |
| `reativada` | S4 | Acompanhamento |

---

*Gerado em 2025-07. Branch `feature/frontend-ux-gaps`. Baseado em auditoria de código-fonte.*