# Jobs e Execução — SegmentHub

> Arquitetura job-per-segment, notebooks de execução e monitoramento.

---

## 1. Arquitetura Job-per-Segment

Cada segmentação ativa possui **seu próprio Databricks Job**. Não existe um job central que processa todas — o isolamento é total.

```
  ┌───────────────────────────────────────────────────────────────────────────────┐
  │                                                                               │
  │  BACKEND (FastAPI)                            DATABRICKS JOBS (dinâmicos)      │
  │  ┌──────────────────┐                    ┌──────────────────────────────────┐  │
  │  │ JobManagerService│  criar/pausar/   │ S1-SEG-ALTA-RENDA-3F2A (6h)      │  │
  │  │ (Databricks SDK) │────deletar─────▶ │ S1-SEG-CHURN-DIGITAL-A1B2 (12h)  │  │
  │  └──────────────────┘                    │ S1-SEG-CARTAO-PLAT-9D4E (seg.)   │  │
  │                                          │ ... (~1.000 jobs)                │  │
  │                                          └────────────────┬─────────────────┘  │
  │                                                           │                    │
  │  JOB DE INFRA (fixo)                                      ▼                    │
  │  ┌───────────────────────────────┐       NOTEBOOKS                    │
  │  │ S1-INFRA-SAUDE-CONSOLIDADOR │       ┌────────────────────────┐  │
  │  │ cron: 0 0 */6 * * ?         │──────▶│ seg_saude_consolidador │  │
  │  └───────────────────────────────┘       ├────────────────────────┤  │
  │                                          │ seg_exec               │  │
  │                                          └────────────────────────┘  │
  │                                                                               │
  └───────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Convenção de Nomenclatura

| Tipo | Padrão | Exemplo |
|---|---|---|
| Job per-segment | `S1-SEG-{seg_codigo}` | `S1-SEG-ALTA-RENDA-3F2A` |
| Job infra | `S1-INFRA-{funcao}` | `S1-INFRA-SAUDE-CONSOLIDADOR` |

**Formato de `seg_codigo`:** `SEG-{NOME_LIMPO_20CHARS}-{HEX_4CHARS}`

---

## 3. Notebook: `seg_exec` (execução individual)

Notebook parametrizado que executa **1 segmentação**.

### Parâmetros

| Parâmetro | Tipo | Descrição |
|---|---|---|
| `seg_id` | STRING | ID da segmentação a executar |
| `origem_execucao` | STRING | `agendada` / `manual` / `reativacao` |

### Fluxo de Execução (6 Steps)

```
  ┌──────────────────────────────────────────────────────────────────────────┐
  │  STEP 1 ─ Carregar definição                                                │
  │    ├─ Status != ativa/aprovada?  → EXIT (ignorado)                          │
  │    ├─ Vigência expirada?          → EXIT (expirado)                          │
  │    └─ OK → continua                                                          │
  │                                                                              │
  │  STEP 2 ─ Montar query SQL                                                   │
  │    ① Resolve campos físicos via catalogo_caracteristicas                      │
  │    ② Build WHERE recursivo (AND/OR aninhado)                                 │
  │    ③ Resolve JOINs necessários                                               │
  │                                                                              │
  │  STEP 3 ─ Executar query                                                     │
  │    df_resultado = spark.sql(query)                                           │
  │    qtd_clientes = df_resultado.count()                                       │
  │                                                                              │
  │  STEP 4 ─ Persistir resultado                                                │
  │    ① MERGE seg_resultado_corrente (NOT MATCHED→INSERT; BY SOURCE→DELETE)    │
  │    ② INSERT seg_resultado_historico (snapshot completo)                       │
  │                                                                              │
  │  STEP 5 ─ Registrar execução                                                  │
  │    INSERT seg_execucao (exec_id, qtd, status, job_run_url)                   │
  │                                                                              │
  │  STEP 6 ─ Atualizar saúde individual                                          │
  │    ① Calcula variação % vs. execução anterior                                │
  │    ② Taxa de sucesso (últimas 10 execuções)                                  │
  │    ③ MERGE seg_saude (health: verde/amarelo/vermelho)                        │
  │                                                                              │
  │  STEP 7 ─ Overlap incremental                                                │
  │    Para cada outro segmento ativo:                                           │
  │      INNER JOIN → clientes_em_comum → MERGE seg_overlap                      │
  │                                                                              │
  │  EXIT: sucesso ✅                                                             │
  └──────────────────────────────────────────────────────────────────────────┘
```

### Critérios de Health Status

| Condição | Status |
|---|---|
| Variação > 50% OU taxa sucesso < 70% | `vermelho` |
| Variação > 30% OU taxa < 80% OU exec > 5min | `amarelo` |
| Nenhum alerta | `verde` |

### MERGE em `seg_resultado_corrente`

```sql
MERGE INTO seg_resultado_corrente AS target
USING (SELECT seg_id, cpf_cnpj FROM resultado_novo) AS source
ON target.seg_id = source.seg_id AND target.cpf_cnpj = source.cpf_cnpj
WHEN NOT MATCHED THEN INSERT (seg_id, cpf_cnpj, exec_id, entrou_em)
  VALUES (...)
WHEN NOT MATCHED BY SOURCE AND target.seg_id = '{SEG_ID}' THEN DELETE
```

**Crítico:** A cláusula `AND target.seg_id = '{SEG_ID}'` garante que só linhas do segmento corrente são afetadas.

---

## 4. Notebook: `seg_saude_consolidador` (infra)

Job periódico (6 em 6h) que monitora **todas** as segmentações.

### Funções

```
  ① Listar segmentações ativas
       │
       ▼
  ② Verificar última execução com sucesso de cada
       │
       ├── Atrasada? (sem exec no prazo)
       │     ├─ SIM ─▶ MERGE seg_saude → vermelho
       │     │            └─▶ INSERT seg_notificacao (owner)
       │     └─ NÃO ─▶ OK
       │
       ├── Execução 'rodando' > 2h?
       │     └─ SIM ─▶ UPDATE status → falha_timeout
       │
       └── FIM
```

| Check | Tolerância | Ação |
|---|---|---|
| Recorrência diária sem executar | 26h | Alerta vermelho |
| Recorrência semanal sem executar | 8 dias | Alerta vermelho |
| Sem nenhuma execução | 3 dias | Alerta crítico |
| Status "rodando" > 2h | 2h | Marca `falha_timeout` |

---

## 5. Mapeamento Ciclo de Vida → Ação no Job

| Evento no Backend | Ação no Databricks Jobs | SDK |
|---|---|---|
| `ativar(seg_id)` | Cria job com schedule | `w.jobs.create(...)` |
| `pausar(seg_id)` | Remove schedule (job existe) | `w.jobs.update(schedule=None)` |
| `reativar(seg_id)` | Restaura schedule | `w.jobs.update(schedule=cron)` |
| `encerrar(seg_id)` | Deleta job | `w.jobs.delete(job_id)` |
| `arquivar(seg_id)` | Deleta job | `w.jobs.delete(job_id)` |
| `executar(seg_id)` manual | Dispara run | `w.jobs.run_now(job_id)` |
| Atualizar cron | Atualiza schedule | `w.jobs.update(schedule=novo)` |

---

## 6. Configuração Padrão do Job

| Parâmetro | Valor |
|---|---|
| Timeout | 3600s (1h) |
| Max retries | 2 |
| Max concurrent runs | 1 |
| Queue | Enabled |
| Timezone | America/Sao_Paulo |
| Notifications | on_failure → email_contato |
| Tags | plataforma, seg_id, area, owner |

---

## 7. Estimativa de Escala

| Métrica | Valor (produção) |
|---|---|
| Segmentações ativas | ~1.000 |
| Jobs criados | ~1.000 (1:1) |
| Execuções/dia | ~800 (mix diário + semanal) |
| Overlap: pares/execução | ~999 (incremental, não 500K) |
| Tempo médio por execução | 30-120s (serverless) |

---

## 8. Estrutura de Arquivos

```
/databricks/jobs/s1_segmenthub/
├── JOBS_MANIFEST.md              ← este documento de referência
├── seg_exec                      ← notebook: executa 1 segmentação
└── seg_saude_consolidador        ← notebook: health checks periódicos
```

---

## 9. Evolução (v1 → v2)

A arquitetura atual (v2) substituiu o modelo anterior:

| Antigo (v1) | Problema | Atual (v2) |
|---|---|---|
| 1 job central (seg_exec) | Gargalo de concorrência com 1000 segs | Jobs individuais `S1-SEG-{codigo}` |
| seg_guardiao (vigência) | Redundante | Schedule nativo do Databricks Jobs |
| seg_saude (tudo) | Monolítico | `seg_saude_consolidador` (infra) + saúde inline no `seg_exec` |
| seg_overlap (O(n²)) | Inviável com 1000 segs | Overlap incremental dentro de `seg_exec` (Step 7) |

---

*Baseado nos notebooks reais e no `JOBS_MANIFEST.md` em `/databricks/jobs/s1_segmenthub/`.*