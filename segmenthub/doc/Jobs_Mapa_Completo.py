# Databricks notebook source
# DBTITLE 1,SegmentHub (S1) — Mapa Completo de Jobs
# MAGIC %md
# MAGIC # SegmentHub (S1) — Mapa Completo de Jobs
# MAGIC
# MAGIC > Referência técnica: cada Job/Notebook com descrição, tabelas/campos que lê e escreve, parâmetros de entrada e saída.
# MAGIC >
# MAGIC > **Arquitetura:** Job-per-Segment · **Catálogo:** `plataforma` · **Compute:** Serverless
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## Visão Geral
# MAGIC
# MAGIC | Tipo | Qtd | Padrão de Nome | Schedule |
# MAGIC |------|-----|----------------|----------|
# MAGIC | **Per-Segment** (dinâmicos) | ~1.000 | `S1-SEG-{seg_codigo}` | Cron individual por seg |
# MAGIC | **Infraestrutura** (fixo) | 1 | `S1-INFRA-SAUDE-CONSOLIDADOR` | `0 0 */6 * * ?` (6h) |
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## Índice
# MAGIC 1. [seg_exec — Execução de Segmentação Individual](#seg-exec)
# MAGIC 2. [seg_saude_consolidador — Consolidação de Saúde](#saude-consolidador)
# MAGIC 3. [Matriz: Tabelas x Jobs](#matriz)
# MAGIC 4. [Ciclo de Vida → Ação no Job](#ciclo-vida)

# COMMAND ----------

# DBTITLE 1,1. seg_exec — Execução de Segmentação Individual
# MAGIC %md
# MAGIC ## 1. `seg_exec` — Execução de Segmentação Individual <a id="seg-exec"></a>
# MAGIC
# MAGIC **Job Name:** `S1-SEG-{seg_codigo}` (1 job por segmentação ativa) 
# MAGIC **Notebook:** `/databricks/jobs/s1_segmenthub/seg_exec` 
# MAGIC **Schedule:** Cron individual (campo `agendamento_cron` de cada seg) 
# MAGIC **Timeout:** 3600s (1h) · **Retries:** 2 · **Max concurrent:** 1
# MAGIC
# MAGIC ### Parâmetros de Entrada
# MAGIC
# MAGIC | Parâmetro | Tipo | Origem | Descrição |
# MAGIC |-----------|------|--------|----------|
# MAGIC | `seg_id` | STRING | `base_parameters` do Job | ID da segmentação a executar |
# MAGIC | `origem_execucao` | STRING | `base_parameters` | `agendada` / `manual` / `reativacao` |
# MAGIC | `exec_id` | STRING (opcional) | Propagado pelo service (execução manual) | Se vazio, o notebook gera um novo |
# MAGIC
# MAGIC ### Saída (`dbutils.notebook.exit`)
# MAGIC
# MAGIC ```json
# MAGIC {
# MAGIC   "status": "sucesso" | "erro",
# MAGIC   "seg_id": "seg_abc123",
# MAGIC   "exec_id": "exec_seg_abc123_20260824_120000",
# MAGIC   "qtd_clientes": 14832,
# MAGIC   "tempo_exec_seg": 12.5,
# MAGIC   "health_status": "verde" | "amarelo" | "vermelho",
# MAGIC   "versao": 3
# MAGIC }
# MAGIC ```
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### Fluxo Step-by-Step
# MAGIC
# MAGIC | Step | Descrição | Tabelas Lê | Campos Lidos | Tabelas Escreve | Campos Escritos |
# MAGIC |------|-----------|------------|--------------|-----------------|----------------|
# MAGIC | **1** | Carrega definição da seg + valida status/vigência | `segmentacao.seg_definicao` | `seg_id`, `nome`, `regras_json`, `versao_atual`, `status`, `publico_base_id`, `vigencia_inicio`, `vigencia_fim`, `agendamento_cron` | — | — |
# MAGIC | **2** | Monta SQL dinâmico (resolve campos físicos via catálogo) | `metadata.catalogo_caracteristicas` | `caracteristica_id`, `tabela_fisica`, `campo_fisico`, `join_key`, `tipo_dado` | — | — |
# MAGIC | | Resolve público-base | `metadata.catalogo_publicos` | `publico_id`, `tabela_fisica`, `join_key` | — | — |
# MAGIC | **3** | Executa query do público (approx_count ou count exato) | `publico.pub_*` (dinâmico) | `cpf_cnpj` + campos das regras | — | — |
# MAGIC | | | `caracteristicas.customer_features_wide` | campos físicos mapeados | | |
# MAGIC | **4a** | MERGE resultado corrente (snapshot atual) | `segmentacao.seg_resultado_corrente` | `seg_id`, `cpf_cnpj` (match key) | `segmentacao.seg_resultado_corrente` | `seg_id`, `cpf_cnpj`, `exec_id`, `entrou_em` |
# MAGIC | **4b** | INSERT resultado histórico (append-only) | — | — | `segmentacao.seg_resultado_historico` | `exec_id`, `seg_id`, `versao_usada`, `cpf_cnpj`, `snapshot_em` |
# MAGIC | **5** | Registra execução (INSERT ou UPDATE conforme IS_PREREGISTERED) | — | — | `segmentacao.seg_execucao` | `exec_id`, `seg_id`, `versao_usada`, `origem_execucao`, `executado_em`, `qtd_clientes`, `status`, `job_id`, `run_id`, `job_run_url` |
# MAGIC | **6** | Calcula e atualiza saúde individual | `segmentacao.seg_execucao` | `qtd_clientes` (exec anterior, para variação %) | `segmentacao.seg_saude` | `seg_id`, `health_status`, `ultima_verificacao`, `variacao_publico_pct`, `taxa_sucesso_exec`, `tempo_medio_exec_seg`, `publico_atual` |
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### Mecanismos de Segurança
# MAGIC
# MAGIC | Mecanismo | Descrição |
# MAGIC |-----------|----------|
# MAGIC | Whitelist de operadores | `OPS_VALIDOS` — impede SQL injection via regras corrompidas |
# MAGIC | Queries parametrizadas | Spark 3.4+ named params (`:seg_id`, `:p0`, `:p1`...) |
# MAGIC | Validação de vigência | Segs expiradas não executam |
# MAGIC | Validação de status | Apenas `ativa` e `aprovada` executam |
# MAGIC | INSERT com colunas explícitas | Imune a ALTER TABLE ADD COLUMN |
# MAGIC | NULLIF | job_id/run_id vazios → NULL (não string vazia) |

# COMMAND ----------

# DBTITLE 1,2. seg_saude_consolidador — Consolidação de Saúde
# MAGIC %md
# MAGIC ## 2. `seg_saude_consolidador` — Consolidação de Saúde <a id="saude-consolidador"></a>
# MAGIC
# MAGIC **Job Name:** `S1-INFRA-SAUDE-CONSOLIDADOR` 
# MAGIC **Notebook:** `/databricks/jobs/s1_segmenthub/seg_saude_consolidador` 
# MAGIC **Schedule:** `0 0 */6 * * ?` (a cada 6 horas) 
# MAGIC **Timeout:** 900s (15min) · **Retries:** 1
# MAGIC
# MAGIC ### Parâmetros de Entrada
# MAGIC
# MAGIC Nenhum (job de infra sem parâmetros).
# MAGIC
# MAGIC ### Saída (`dbutils.notebook.exit`)
# MAGIC
# MAGIC ```json
# MAGIC {
# MAGIC   "status": "sucesso",
# MAGIC   "segmentacoes_verificadas": 1042,
# MAGIC   "alertas_gerados": 3,
# MAGIC   "saude_atualizada": 5,
# MAGIC   "execucoes_travadas": 1
# MAGIC }
# MAGIC ```
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### Fluxo Step-by-Step
# MAGIC
# MAGIC | Step | Descrição | Tabelas Lê | Campos Lidos | Tabelas Escreve | Campos Escritos |
# MAGIC |------|-----------|------------|--------------|-----------------|----------------|
# MAGIC | **1** | Identifica segs ativas + detecta atrasos (SQL puro, sem .collect() de todas) | `segmentacao.seg_definicao` | `seg_id`, `nome`, `owner`, `recorrencia`, `status`, `habilitado` | — | — |
# MAGIC | | LEFT JOIN com saúde e última execução | `segmentacao.seg_saude` | `ultima_verificacao` | | |
# MAGIC | | | `segmentacao.seg_execucao` | MAX(`executado_em`) WHERE status='sucesso' | | |
# MAGIC | | **Regras de atraso:** | | | | |
# MAGIC | | • Diário: sem sucesso > 26h | | | | |
# MAGIC | | • Semanal: sem sucesso > 8 dias | | | | |
# MAGIC | | • Nunca executou: > 3 dias desde criação | | | | |
# MAGIC | **2** | Detecta execuções travadas (>2h em `em_execucao`) | `segmentacao.seg_execucao` | `seg_id`, `exec_id`, `status`, `executado_em` | `segmentacao.seg_execucao` | `status` → `'falha_timeout'` (MERGE bulk) |
# MAGIC | **4** | Atualiza saúde das segs problemáticas (MERGE bulk — 1 commit Delta) | — | — | `segmentacao.seg_saude` | `seg_id`, `health_status` → `'vermelho'`, `ultima_verificacao`, `alertas_json` |
# MAGIC | **5** | Gera notificações para owners de segs com health vermelho | — | — | `segmentacao.seg_notificacao` | `notif_id`, `destinatario` (=owner), `tipo`='alerta_saude', `seg_id`, `titulo`, `mensagem`, `lida`=false, `criado_em` |
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### Performance (RF-06)
# MAGIC
# MAGIC | Antes (v1) | Depois (v2) |
# MAGIC |------------|-------------|
# MAGIC | `.collect()` de TODAS as segs ativas (1000+) → loop Python | SQL puro retorna só problemáticas (dezenas) |
# MAGIC | N MERGEs individuais (N commits Delta) | 1 MERGE bulk (1 commit) |
# MAGIC | OOM risco com 100K+ segs | Escala infinita (SQL pushdown) |

# COMMAND ----------

# DBTITLE 1,3. Matriz: Tabelas x Jobs
# MAGIC %md
# MAGIC ## 3. Matriz: Tabelas x Jobs <a id="matriz"></a>
# MAGIC
# MAGIC | Tabela | `seg_exec` Lê | `seg_exec` Escreve | `saude_consolidador` Lê | `saude_consolidador` Escreve |
# MAGIC |--------|:---:|:---:|:---:|:---:|
# MAGIC | `segmentacao.seg_definicao` | ✅ | — | ✅ | — |
# MAGIC | `segmentacao.seg_execucao` | ✅ (Step 6) | ✅ (Step 5) | ✅ | ✅ (marca travadas) |
# MAGIC | `segmentacao.seg_resultado_corrente` | ✅ (MERGE) | ✅ (MERGE) | — | — |
# MAGIC | `segmentacao.seg_resultado_historico` | — | ✅ (INSERT) | — | — |
# MAGIC | `segmentacao.seg_saude` | — | ✅ (MERGE) | ✅ | ✅ (MERGE bulk) |
# MAGIC | `segmentacao.seg_notificacao` | — | — | — | ✅ (INSERT) |
# MAGIC | `metadata.catalogo_caracteristicas` | ✅ | — | — | — |
# MAGIC | `metadata.catalogo_publicos` | ✅ | — | — | — |
# MAGIC | `publico.pub_*` | ✅ | — | — | — |
# MAGIC | `caracteristicas.customer_features_wide` | ✅ | — | — | — |
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### Comparação: API vs Jobs (quem toca o quê)
# MAGIC
# MAGIC | Tabela | API REST (backend) | Jobs (notebooks) | Observação |
# MAGIC |--------|:---:|:---:|---|
# MAGIC | `seg_resultado_corrente` | ❌ nunca | ✅ MERGE | CPFs só via Job (segurança) |
# MAGIC | `seg_resultado_historico` | ❌ nunca | ✅ INSERT | Append-only via Job |
# MAGIC | `seg_saude` | ✅ leitura | ✅ escrita | API só lê, Jobs escrevem |
# MAGIC | `seg_execucao` | ✅ INSERT inicial | ✅ UPDATE final | Service pre-registra, Job finaliza |
# MAGIC | `seg_definicao` | ✅ CRUD completo | ✅ leitura | Jobs nunca alteram definições |
# MAGIC | `seg_notificacao` | ✅ comentários | ✅ alertas saúde | Ambos escrevem (contextos diferentes) |

# COMMAND ----------

# DBTITLE 1,4. Ciclo de Vida → Ação no Job
# MAGIC %md
# MAGIC ## 4. Ciclo de Vida → Ação no Job <a id="ciclo-vida"></a>
# MAGIC
# MAGIC | Evento no Backend | Ação no Databricks Jobs | Tabelas Impactadas |
# MAGIC |-------------------|-------------------------|--------------------|
# MAGIC | `ativar(seg_id)` | `jobs.create(...)` — cria job com schedule | `seg_definicao` (W: job_id_databricks), `seg_job_log` (W: ação='criar') |
# MAGIC | `pausar(seg_id)` | `jobs.update(schedule=None)` — remove schedule | `seg_job_log` (W: ação='pausar') |
# MAGIC | `reativar(seg_id)` | `jobs.update(schedule=cron)` — reativa schedule | `seg_job_log` (W: ação='reativar') |
# MAGIC | `encerrar(seg_id)` | `jobs.delete(job_id)` — remove job | `seg_job_log` (W: ação='deletar') |
# MAGIC | `arquivar(seg_id)` | `jobs.delete(job_id)` — remove job | `seg_job_log` (W: ação='deletar') |
# MAGIC | `executar(seg_id)` manual | `jobs.run_now(job_id, params)` — disparo | `seg_execucao` (W: pre-registro), `seg_job_log` (W: ação='executar') |
# MAGIC | `atualizar_vigencia(seg_id, cron)` | `jobs.update(schedule=novo_cron)` | `seg_job_log` (W: ação='atualizar_schedule') |
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### Interação Service ↔ Job (execução manual)
# MAGIC
# MAGIC ```
# MAGIC   BACKEND (API)                                JOB (Notebook)
# MAGIC   ───────────────                                ───────────────
# MAGIC   1. Gera exec_id                              
# MAGIC   2. INSERT seg_execucao                       
# MAGIC      (status='em_execucao')                    
# MAGIC   3. jobs.run_now(seg_id,                      
# MAGIC      exec_id=exec_id)         ───────▶  4. Recebe exec_id via widget
# MAGIC                                                5. Executa segmentação
# MAGIC                                                6. UPDATE seg_execucao
# MAGIC                                                   (status='sucesso',
# MAGIC                                                    qtd_clientes, job_run_url)
# MAGIC ```
# MAGIC
# MAGIC ### Interação Job agendado (sem pre-registro)
# MAGIC
# MAGIC ```
# MAGIC   JOB (Notebook)
# MAGIC   ───────────────
# MAGIC   1. Widget exec_id vazio → gera novo
# MAGIC   2. Executa segmentação
# MAGIC   3. INSERT seg_execucao (registro completo)
# MAGIC ```
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 5. Jobs Removidos (Histórico)
# MAGIC
# MAGIC | Job Antigo | Motivo | Substituição |
# MAGIC |------------|--------|-------------|
# MAGIC | `S1-JOB-01 seg_exec` (centralizado) | Gargalo: 1 job p/ 1000 segs | Jobs individuais `S1-SEG-*` |
# MAGIC | `S1-JOB-02 seg_guardiao` | Schedule nativo do Databricks Jobs já faz isso | Removido |
# MAGIC | `S1-JOB-03 seg_saude` | Reformulado | `S1-INFRA-SAUDE-CONSOLIDADOR` |
# MAGIC | `S1-JOB-04 seg_overlap` | O(n²) inviável | Descontinuado (futuro Step 7 incremental) |
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC **Total: 2 notebooks** (1 dinâmico per-segment + 1 infra fixo) · **~1.001 jobs** em produção (1000 segs + 1 consolidador)
# MAGIC
# MAGIC ---
# MAGIC *Gerado a partir dos notebooks reais em `/databricks/jobs/s1_segmenthub/` + JOBS_MANIFEST.md — Ago/2026*
