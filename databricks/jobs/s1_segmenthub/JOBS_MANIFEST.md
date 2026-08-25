# S1 SegmentHub — Jobs Manifest

> Última atualização: 2026-08-18 (auditoria completa + 8 bugs corrigidos)

## Arquitetura: Job-per-Segment

Cada segmentação ativa possui seu próprio Databricks Job.
O Job Manager Service (backend) cria/pausa/deleta jobs automaticamente
quando o ciclo de vida da segmentação muda.

**Princípios:**
- 1 segmentação = 1 Databricks Job (isolamento total)
- Schedule nativo do Databricks Jobs (sem orquestrador externo)
- Serverless compute (cold start ~5s, pay-per-use)
- Fail-fast: job falha → notificação → consolidador detecta atraso

---

## Jobs Per-Segment (dinâmicos)

| Padrão de Nome | Notebook | Parâmetros | Criado quando |
|---|---|---|---|
| `S1-SEG-{seg_codigo}` | `seg_exec.py` | `seg_id`, `origem_execucao=agendada` | `ativar(seg_id)` |

### Convenção de Nomenclatura

```
S1-SEG-{seg_codigo}
```

**Exemplos:**
- `S1-SEG-ALTA-RENDA-3F2A`
- `S1-SEG-CHURN-DIGITAL-A1B2`
- `S1-SEG-CARTAO-PLATINUM-9D4E`

O `seg_codigo` é gerado pelo backend em `segmentacao_service._gerar_seg_codigo(nome)` no formato:
`SEG-{NOME_LIMPO_20CHARS}-{HEX_4CHARS}`

### Configuração Padrão do Job

```json
{
  "name": "S1-SEG-{seg_codigo}",
  "tasks": [
    {
      "task_key": "executar_segmentacao",
      "notebook_task": {
        "notebook_path": "/Workspace/.../databricks/jobs/s1_segmenthub/seg_exec",
        "base_parameters": {
          "seg_id": "{seg_id}",
          "origem_execucao": "agendada"
        }
      },
      "timeout_seconds": 3600,
      "max_retries": 2,
      "retry_on_timeout": false
    }
  ],
  "schedule": {
    "quartz_cron_expression": "{agendamento_cron da segmentação}",
    "timezone_id": "America/Sao_Paulo"
  },
  "max_concurrent_runs": 1,
  "tags": {
    "plataforma": "segmenthub",
    "seg_id": "{seg_id}",
    "area": "{area_responsavel}",
    "owner": "{owner}"
  },
  "email_notifications": {
    "on_failure": ["{email_contato}"]
  },
  "queue": {
    "enabled": true
  }
}
```

### Ciclo de Vida → Ação no Job

| Evento Backend | Ação no Databricks Jobs |
|---|---|
| `ativar(seg_id)` | `jobs.create(...)` → cria job com schedule |
| `pausar(seg_id)` | `jobs.update(schedule=None)` → remove schedule (job existe mas não roda) |
| `reativar(seg_id)` | `jobs.update(schedule=cron)` → reativa schedule |
| `encerrar(seg_id)` | `jobs.delete(job_id)` → remove job completamente |
| `arquivar(seg_id)` | `jobs.delete(job_id)` → remove job completamente |
| `executar(seg_id)` manual | `jobs.run_now(job_id, params)` → disparo manual (origem='manual') |
| `atualizar_vigencia(seg_id, cron)` | `jobs.update(schedule=novo_cron)` → atualiza schedule |

### Mapeamento Backend → Jobs API

O backend armazena `job_id_databricks` na tabela `seg_definicao`
para permitir operações CRUD no job.

O `job_manager_service.py` encapsula todas interações com a Databricks SDK:
- Queries parametrizadas para auditoria (seg_job_log)
- Try/except com logging (operação principal não é revertida se log falha)
- Notebook path configurável via constante `NOTEBOOK_PATH`

---

## Jobs de Infraestrutura (fixos)

| Nome do Job | Notebook | Schedule | Função |
|---|---|---|---|
| `S1-INFRA-SAUDE-CONSOLIDADOR` | `seg_saude_consolidador.py` | `0 0 */6 * * ?` (6 em 6h) | Detecta segs atrasadas, marca health vermelho, gera notificações, limpa execuções travadas |

### Configuração do Job de Infra

```json
{
  "name": "S1-INFRA-SAUDE-CONSOLIDADOR",
  "tasks": [
    {
      "task_key": "consolidar_saude",
      "notebook_task": {
        "notebook_path": "/Workspace/.../databricks/jobs/s1_segmenthub/seg_saude_consolidador",
        "base_parameters": {}
      },
      "timeout_seconds": 900,
      "max_retries": 1
    }
  ],
  "schedule": {
    "quartz_cron_expression": "0 0 */6 * * ?",
    "timezone_id": "America/Sao_Paulo"
  },
  "tags": {
    "plataforma": "segmenthub",
    "tipo": "infraestrutura"
  },
  "email_notifications": {
    "on_failure": ["rafael.correr@bradesco.com.br"]
  }
}
```

---

## seg_exec.py — Fluxo Detalhado

Notebook parametrizado que executa UMA segmentação por run.

### Steps

| Cell | Step | Descrição | Tabelas |
|---|---|---|---|
| 2 | Setup | Widgets (`seg_id`, `origem_execucao`), imports, constantes | — |
| 3 | 1 | Carrega definição da seg, valida status (ativa/aprovada), valida vigência | `seg_definicao` (R) |
| 4 | 2 | Monta SQL dinâmico a partir das regras (build_condition + JOINs) | `catalogo_caracteristicas` (R), `catalogo_publicos` (R) |
| 5 | 3 | Executa query SQL, mede contagem e tempo | Tabelas do público base (R) |
| 6 | 4 | MERGE resultado em `seg_resultado_corrente` + INSERT em `seg_resultado_historico` | `seg_resultado_corrente` (W), `seg_resultado_historico` (W) |
| 7 | 5 | Registra execução com colunas explícitas + NULLIF para strings vazias | `seg_execucao` (W) |
| 8 | 6 | Calcula saúde individual (variação %, taxa sucesso, tempo) + MERGE | `seg_execucao` (R), `seg_saude` (W) |
| 9 | Fim | Retorna JSON com resultado via `dbutils.notebook.exit()` | — |

### Mecanismos de Segurança (v2.0)

- **Whitelist de operadores**: `OPS_VALIDOS` — impede operadores arbitrários no SQL
- **Dict lookup O(1)**: catálogo materializado em memória (`catalogo_dict`)
- **Validação de vigência**: segmentações expiradas não executam
- **Validação de status**: apenas `ativa` e `aprovada` executam
- **INSERT com colunas explícitas**: imune a ALTER TABLE ADD COLUMN
- **NULLIF**: job_id/run_id vazios → NULL no banco (não string vazia)

---

## seg_saude_consolidador.py — Fluxo Detalhado

Job de infraestrutura que roda a cada 6h para detectar problemas.

### Steps

| Cell | Step | Descrição | Tabelas |
|---|---|---|---|
| 2 | Setup | Imports, constantes | — |
| 3 | 1 | Busca todas segmentações ativas com LEFT JOIN em `seg_saude` | `seg_definicao` (R), `seg_saude` (R) |
| 4 | 2 | Busca última execução (sucesso) de cada seg | `seg_execucao` (R) |
| 5 | 3 | Detecta atrasos (diário > 26h, semanal > 8d, sem exec > 3d) | — |
| 6 | 4 | MERGE em `seg_saude` para segs problemáticas | `seg_saude` (W) |
| 7 | 5 | Gera notificações para owners (notif_id via UUID) | `seg_notificacao` (W) |
| 8 | 6 | Detecta execuções travadas (>2h rodando) → marca `falha_timeout` | `seg_execucao` (W) |
| 9 | Resumo | Retorna JSON com métricas via `dbutils.notebook.exit()` | — |

---

## Jobs Removidos (migração v1 → v2)

| Job Antigo | Motivo da Remoção | Substituição |
|---|---|---|
| ~~S1-JOB-01 seg_exec~~ | Gargalo de concorrência (1 job para 1000 segs) | Jobs individuais `S1-SEG-{codigo}` |
| ~~S1-JOB-02 seg_guardiao~~ | Schedule nativo do Databricks Jobs já faz isso | Removido — cada job tem seu próprio cron |
| ~~S1-JOB-03 seg_saude~~ | Reformulado para detectar atrasos e gerar alertas | `S1-INFRA-SAUDE-CONSOLIDADOR` |
| ~~S1-JOB-04 seg_overlap~~ | O(n²) inviável com 1000 segs | Overlap incremental dentro de `seg_exec.py` (futuro Step 7) |

---

## Alterações Backend (status: ✅ implementado)

### 1. Coluna `job_id_databricks` em `seg_definicao`

```sql
ALTER TABLE plataforma.segmentacao.seg_definicao
ADD COLUMN job_id_databricks STRING COMMENT 'ID do Databricks Job criado para esta segmentação';
```

### 2. Service: `job_manager_service.py` (✅ implementado)

Métodos implementados:
- `criar_job(seg_id)` → `w.jobs.create(...)` + registra log
- `pausar_job(seg_id)` → `w.jobs.update(job_id, schedule=None)`
- `reativar_job(seg_id, cron)` → `w.jobs.update(job_id, schedule=cron)`
- `deletar_job(seg_id)` → `w.jobs.delete(job_id)`
- `executar_agora(seg_id)` → `w.jobs.run_now(job_id, params)`
- `atualizar_schedule(seg_id, cron)` → `w.jobs.update(job_id, schedule=cron)`
- `_registrar_log()` → queries parametrizadas (sem f-string SQL)

### 3. Integração em `segmentacao_service.py` (✅ implementado)

```python
def ativar(self, seg_id, usuario):
    self.transicionar_status(seg_id, "ativa")
    job_id = self.job_manager.criar_job(seg_id)
    self.repository.atualizar(seg_id, {"job_id_databricks": job_id})

def pausar(self, seg_id, usuario):
    self.transicionar_status(seg_id, "pausada")
    self.job_manager.pausar_job(seg_id)

def reativar(self, seg_id, usuario):
    self.transicionar_status(seg_id, "ativa")
    self.job_manager.reativar_job(seg_id)

def encerrar(self, seg_id, usuario):
    self.transicionar_status(seg_id, "encerrada")
    self.job_manager.deletar_job(seg_id)
```

---

## Estrutura de Arquivos

```
databricks/jobs/s1_segmenthub/
├── JOBS_MANIFEST.md              ← este arquivo
├── seg_exec.py                   ← notebook: executa 1 segmentação (parametrizado)
└── seg_saude_consolidador.py     ← notebook: consolida saúde periódica
```

---

## Estimativa de Escala

| Métrica | Valor |
|---|---|
| Segmentações ativas (produção) | ~1.000 |
| Jobs criados | ~1.000 (1:1) |
| Execuções/dia (mix diário+semanal) | ~800 |
| Overlap: pares calculados/execução | ~999 (incremental, não 500K) |
| Tempo médio por execução | 30-120s (serverless) |
| Custo estimado (serverless DBU) | Proporcional ao uso real |

---

## Auditoria — Bugs Corrigidos (2026-08-18)

### seg_exec.py (6 fixes)

| # | Severidade | Bug | Correção |
|---|---|---|---|
| 1 | CRITICAL | `build_condition(rules=[])` retornava `""` → SQL syntax error | `if not node.get("rules"): return "1=1"` |
| 2 | HIGH | `catalogo_df.filter().first()` em loop (40 Spark jobs, ~120s overhead) | `collect()` → dict O(1) lookup |
| 3 | HIGH | Operador arbitrário interpolado no SQL sem validação | Whitelist `OPS_VALIDOS` com 14 ops válidos |
| 4 | MEDIUM | `datetime.now(timezone.utc)` vs Spark naive timestamp → TypeError | `datetime.utcnow()` (naive, compatível Spark) |
| 5 | HIGH | `INSERT INTO ... VALUES` sem lista de colunas + `''` em vez de NULL | Colunas explícitas + `NULLIF('{val}', '')` |
| 6 | MEDIUM | `df_tempo` calculava idade da execução (dead code, resultado ignorado) | Removido |

### seg_saude_consolidador.py (2 fixes)

| # | Severidade | Bug | Correção |
|---|---|---|---|
| 7 | HIGH | `datetime.now(timezone.utc)` vs Spark naive → TypeError no loop principal | `datetime.utcnow()` |
| 8 | MEDIUM | `notif_id` com minuto-precision → duplicata em retry do job | UUID-based ID |

### job_manager_service.py (1 fix — commit anterior)

| # | Severidade | Bug | Correção |
|---|---|---|---|
| 9 | HIGH | `_registrar_log()` com f-string SQL injection (stack traces com aspas) | Queries parametrizadas via `client.execute_insert()` |

---

## 🔮 Pontos de Revisão Futura

Issues de design identificadas na auditoria que requerem decisão arquitetural.
Não são bugs de crash, mas afetam consistência e escalabilidade.

---

### RF-01: exec_id duplicado (Service ↔ Job criam registros independentes) — ✅ IMPLEMENTADO

**Problema:**

O fluxo de execução manual gera DOIS registros em `seg_execucao` para a mesma execução:

1. **Service** (`segmentacao_service.executar()`):
   - Gera `exec_id = f"exec_{uuid.uuid4().hex[:12]}"`
   - Insere registro com status `em_execucao` ANTES de disparar o job
   - Propósito: dar feedback imediato ao frontend (run_id visível na UI)

2. **Job** (`seg_exec.py` Cell 7):
   - Gera SEU PRÓPRIO `exec_id = f"exec_{SEG_ID}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"`
   - Insere registro com status `sucesso` ao final da execução

**Consequência:**
- O registro do Service (`em_execucao`) NUNCA é atualizado para `sucesso`
- Fica como registro órfão eterno no banco
- `obter_timeline()` mostra execuções duplicadas/inconsistentes
- Contagem de execuções por seg fica inflada

**Soluções propostas (escolher UMA):**

| Opção | Abordagem | Prós | Contras |
|---|---|---|---|
| **A** | Job recebe `exec_id` como widget param, NÃO gera o seu | Consistência total, 1 registro por exec | Requer widget adicional + propagação pelo job_manager |
| **B** | Service NÃO cria registro prévio; job é dono de todo o ciclo | Simples, sem duplicata | Frontend não tem exec_id imediato (precisa polling) |
| **C** | Service cria com status `disparado`, job atualiza (UPDATE) em vez de INSERT | Ambos participam do mesmo registro | Job precisa receber exec_id (volta ao problema de A) |

**Implementação aplicada (Opção A+B combinada):**

1. `segmentacao_service.executar()` gera `exec_id` com UUID e registra `em_execucao` ANTES de disparar
2. `job_manager_service.executar_agora()` propaga `exec_id` como notebook_param
3. `seg_exec.py` tem widget `exec_id`:
   - Se recebido (`IS_PREREGISTERED=True`): faz UPDATE no registro existente
   - Se vazio (execução agendada): gera próprio exec_id e faz INSERT
4. Se job crashar, registro fica como `em_execucao` → consolidador detecta como travada (>2h)

**Resultado:** Zero registros órfãos, timeline consistente, falhas visíveis.

---

### RF-02: Execução fantasma (crash entre Step 3 e Step 5) — ✅ IMPLEMENTADO

**Problema:**

Se o notebook falha APÓS executar a query (Step 3) mas ANTES de registrar em
`seg_execucao` (Step 7) — por exemplo, MERGE no Step 4 falha:

- `seg_resultado_corrente` pode estar parcialmente atualizado
- `seg_resultado_historico` pode ter linhas inseridas
- `seg_execucao` NÃO tem registro dessa tentativa
- `seg_saude` mostra último health anterior (desatualizado)
- O consolidador só detecta atraso 6h depois (próximo run)

**Consequência:**
- Dados no resultado_corrente potencialmente inconsistentes
- Sem visibilidade do que aconteceu (nenhum log de falha)
- Retry automático do job (max_retries=2) pode executar novamente sem saber do parcial

**Soluções propostas:**

| Opção | Abordagem | Prós | Contras |
|---|---|---|---|
| **A** | Try/except global no notebook com finally que SEMPRE registra | Captura falhas em qualquer step | try/except no nível de notebook Databricks é frágil |
| **B** | Registrar status `em_execucao` no INÍCIO (Step 1), atualizar para `sucesso`/`falha` no fim | Sempre existe registro; consolidador detecta `em_execucao` velhos | Requer lógica de rollback no Step 4 |
| **C** | Usar Databricks Job events API no consolidador para detectar runs que falharam | Não muda o notebook; consolidador reconcilia | Consolidador fica mais complexo |

**Implementação aplicada (Opção B combinada com RF-01):**

O service cria registro `em_execucao` ANTES do disparo. O job atualiza para `sucesso` no final.
Se o job crashar em qualquer step, o registro permanece como `em_execucao`.
O consolidador (a cada 6h) detecta registros >2h em `em_execucao` e marca como `falha_timeout`.

**Resultado:** Toda execução tem registro desde o início. Falhas são detectáveis.

---

### RF-03: MERGE em loop no consolidador (N queries sequenciais) — ✅ IMPLEMENTADO

**Problema:**

O `seg_saude_consolidador.py` (Cell 6) executa um MERGE por segmentação problemática:

```python
for update in saude_updates:
    spark.sql(f"MERGE INTO seg_saude ...")
```

Com 100 segmentações atrasadas → 100 MERGE statements sequenciais.
Cada MERGE em Delta envolve: file listing + read + write + commit → ~2-5s cada.
100 × 3s = 5 minutos apenas para atualizar saúde.

**Consequência:**
- Timeout possível (job tem 900s = 15min, mas 5min só para MERGEs)
- Delta log pollution (100 commits individuais na mesma tabela)
- Poderia ser 1 operação bulk de 0.5s

**Solução proposta:**

```python
# Em vez de loop de MERGEs:
if saude_updates:
    df_updates = spark.createDataFrame(saude_updates)
    df_updates.createOrReplaceTempView("saude_batch")
    spark.sql(f"""
      MERGE INTO {CATALOG}.{SCHEMA_SEG}.seg_saude AS target
      USING saude_batch AS source
      ON target.seg_id = source.seg_id
      WHEN MATCHED THEN UPDATE SET
        health_status = source.health_status,
        ultima_verificacao = current_timestamp(),
        alertas_json = source.alertas_json
      WHEN NOT MATCHED THEN INSERT (...)
    """)
```

**Impacto:** 100 MERGEs → 1 MERGE. Performance 100x melhor. 1 commit Delta.

---

### RF-04: Execuções travadas NÃO atualizam seg_saude imediatamente — ✅ IMPLEMENTADO

**Problema:**

Quando o consolidador (Cell 8) detecta execuções travadas (>2h em status `rodando`),
ele marca como `falha_timeout` na `seg_execucao`, mas NÃO atualiza `seg_saude`
da segmentação afetada.

```python
# Cell 8 atual:
for eid in travadas_ids:
    spark.sql(f"UPDATE seg_execucao SET status = 'falha_timeout' WHERE exec_id = '{eid}'")
# ← seg_saude NÃO é atualizado aqui!
```

**Consequência:**
- `seg_saude` continua mostrando health `verde` mesmo após timeout
- Somente no PRÓXIMO run do consolidador (até 6h depois) o atraso é detectado
- Usuário vê dashboard com saúde "verde" para seg que está falhando

**Solução proposta:**

```python
# Após marcar travadas, incluir no array de updates:
if df_travadas.count() > 0:
    for row in df_travadas.collect():
        seg_id = row["seg_id"]
        saude_updates.append({
            "seg_id": seg_id,
            "health_status": "vermelho",
            "alertas_json": json.dumps(["Execução travada (timeout > 2h)"]),
        })
        alertas_gerados.append({
            "seg_id": seg_id,
            "nome": "(seg com timeout)",
            "owner": "",
            "email_contato": "",
            "problemas": ["Execução travada (timeout > 2h)"],
        })
```

**Impacto:** Detecção imediata em vez de delay de 6h. Mínima complexidade.

---

### RF-05: f-string SQL injection no notebook (inputs controlados mas frágil) — ✅ IMPLEMENTADO

**Problema:**

Todos os SQL no `seg_exec.py` usam f-strings com interpolação direta:

```python
spark.sql(f"SELECT ... WHERE seg_id = '{SEG_ID}'")
spark.sql(f"MERGE INTO ... VALUES ('{exec_id}', '{SEG_ID}', ...)")
```

Em contexto PySpark puro, não há endpoint HTTP exposto — os valores vêm de:
- `dbutils.widgets.get()` (controlado pelo job config)
- Banco de dados interno (seg_definicao)
- Geração interna (exec_id com UUID)

**Risco atual: BAIXO** (não é um web endpoint público).

**Porém, se no futuro:**
- Alguém adicionar um endpoint que aceita `seg_id` diretamente de request HTTP
- Ou `regras_json` contiver valores com aspas simples não escapadas em algum edge case
- Ou `nome` de segmentação tiver `'` (ex: "Cliente d'elite")

→ Pode causar SQL injection ou crash.

**Mitigação já aplicada:**
- ✅ `OPS_VALIDOS` whitelist impede operadores maliciosos
- ✅ `sql_val()` escapa aspas simples em strings
- ✅ `NULLIF` para campos que podem ser vazios

**Solução futura ideal:**

```python
# Usar parameterized queries do Spark 3.4+:
spark.sql("SELECT ... WHERE seg_id = :seg_id", args={"seg_id": SEG_ID})

# Ou para MERGE/INSERT, usar DataFrame API:
df_resultado.write.format("delta").mode("append").saveAsTable("seg_resultado_historico")
```

**Impacto:** Imunidade total a injection. Requer refactor significativo mas não urgente.

---

### RF-06: .collect() no consolidador com 1000+ segmentações — ✅ IMPLEMENTADO

**Problema:**

```python
for row in df_check.collect():  # df_check = todas segs ativas
    # Lógica Python de detecção de atraso
```

Com 1.000 segmentações: `collect()` puxa 1.000 rows para o driver → OK.
Mas a lógica de atraso é feita em Python puro (loop, comparações datetime).

**Risco atual:** Com 1.000 segs é aceitável (~2s total no driver).
**Risco futuro:** Com 10.000 segs → OOM potencial + lentidão.

**Solução proposta (quando escalar):**

Mover a lógica de atraso para Spark SQL puro:

```sql
SELECT d.seg_id, d.nome, d.owner, d.email_contato,
       CASE
         WHEN e.ultimo_sucesso IS NULL
              AND s.ultima_verificacao < current_timestamp() - INTERVAL 3 DAYS
           THEN 'Nunca executou com sucesso'
         WHEN d.recorrencia = 'diario'
              AND e.ultimo_sucesso < current_timestamp() - INTERVAL 26 HOURS
           THEN CONCAT('Atraso de ', HOUR(current_timestamp() - e.ultimo_sucesso), 'h')
         WHEN d.recorrencia = 'semanal'
              AND e.ultimo_sucesso < current_timestamp() - INTERVAL 8 DAYS
           THEN CONCAT('Atraso de ', DATEDIFF(current_timestamp(), e.ultimo_sucesso), ' dias')
       END AS problema
FROM seg_definicao d
LEFT JOIN (SELECT seg_id, MAX(executado_em) FILTER(WHERE status='sucesso') AS ultimo_sucesso
           FROM seg_execucao GROUP BY seg_id) e ON d.seg_id = e.seg_id
LEFT JOIN seg_saude s ON d.seg_id = s.seg_id
WHERE d.status = 'ativa' AND d.habilitado = true
HAVING problema IS NOT NULL
```

→ Zero collect, zero loop Python, escala para 100K segs.

**Impacto:** Escalabilidade. Implementar quando segs ativas > 5.000.

---

### RF-07: alertas_json com json.dumps interpolado em SQL — ✅ IMPLEMENTADO

**Problema:**

```python
spark.sql(f"... alertas_json = '{json.dumps(alertas)}' ...")
```

`json.dumps` usa aspas duplas internamente (`["texto"]`), então não conflita com
as aspas simples do SQL na maioria dos casos.

**Porém:**
- Se algum alerta futuro contiver aspas simples no texto (ex: "seg 'VIP' atrasada")
- `json.dumps` preserva o `'` literal → SQL quebra: `'["seg 'VIP' atrasada"]'`

**Risco atual:** Baixo (alertas são gerados internamente com textos controlados).

**Mitigação simples:**

```python
alertas_safe = json.dumps(alertas).replace("'", "''")
spark.sql(f"... alertas_json = '{alertas_safe}' ...")
```

**Impacto:** 1 linha de código. Implementar preventivamente.

---

## Priorização dos Pontos de Revisão

| Prioridade | ID | Issue | Esforço | Risco se não corrigir |
|---|---|---|---|---|
| ✅ Feito | RF-01 | exec_id duplicado | 2h | ~~Dados inconsistentes, timeline poluída~~ |
| ✅ Feito | RF-02 | Execução fantasma | 1h | ~~Perda de visibilidade em falhas~~ |
| ✅ Feito | RF-03 | MERGE em loop | 1h | ~~Performance ruim com muitas segs atrasadas~~ |
| ✅ Feito | RF-04 | Travadas sem seg_saude | 30min | ~~Delay de até 6h na detecção~~ |
| ✅ Feito | RF-07 | alertas_json escape | 10min | ~~Crash se alerta tiver aspas~~ |
| ✅ Feito | RF-05 | f-string SQL | 4-8h | ~~Baixo (inputs controlados hoje)~~ |
| ✅ Feito | RF-06 | collect() escalabilidade | 2h | ~~OK até 5K segs~~ |

---

## Changelog

| Data | Versão | Descrição |
|---|---|---|
| 2026-08-19 | 2.5 | RF-06 implementado: detecção de atrasos 100% Spark SQL (zero collect loop) |
| 2026-08-19 | 2.4 | RF-05 implementado: todas queries parametrizadas (Spark 3.4+ args={}) |
| 2026-08-19 | 2.3 | RF-03 + RF-04 + RF-07 implementados: MERGE bulk, travadas imediatas, escape seguro |
| 2026-08-19 | 2.2 | RF-01 + RF-02 implementados: exec_id unificado + execução fantasma resolvida |
| 2026-08-18 | 2.1 | Auditoria completa: 9 bugs corrigidos, 7 pontos de revisão futura documentados |
| 2026-08-18 | 2.0 | Arquitetura job-per-segment implementada (seg_exec + consolidador + job_manager_service) |
| 2026-08-01 | 1.0 | Manifest inicial |
