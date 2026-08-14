# S1 SegmentHub — Jobs Manifest

## Arquitetura: Job-per-Segment

Cada segmentação ativa possui seu próprio Databricks Job.
O Job Manager Service (backend) cria/pausa/deleta jobs automaticamente
quando o ciclo de vida da segmentação muda.

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
| `executar(seg_id)` manual | `jobs.run_now(job_id, params)` → dispar manual (origem='manual') |
| `atualizar_vigencia(seg_id, cron)` | `jobs.update(schedule=novo_cron)` → atualiza schedule |

### Mapeamento Backend → Jobs API

O backend armazena `job_id` na tabela `seg_execucao` e mantém um campo
`job_id_databricks` na `seg_definicao` (a ser adicionado via ALTER TABLE)
para permitir operações CRUD no job.

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

## Jobs Removidos (migração v1 → v2)

| Job Antigo | Motivo da Remoção | Substituição |
|---|---|---|
| ~~S1-JOB-01 seg_exec~~ | Gargalo de concorrência (1 job para 1000 segs) | Jobs individuais `S1-SEG-{codigo}` |
| ~~S1-JOB-02 seg_guardiao~~ | Schedule nativo do Databricks Jobs já faz isso | Removido — cada job tem seu próprio cron |
| ~~S1-JOB-03 seg_saude~~ | Reformulado para detectar atrasos e gerar alertas | `S1-INFRA-SAUDE-CONSOLIDADOR` |
| ~~S1-JOB-04 seg_overlap~~ | O(n²) inviável com 1000 segs | Overlap incremental dentro de `seg_exec.py` (Step 7) |

---

## Alterações Necessárias no Backend

### 1. Nova coluna em `seg_definicao`

```sql
ALTER TABLE plataforma.segmentacao.seg_definicao
ADD COLUMN job_id_databricks STRING COMMENT 'ID do Databricks Job criado para esta segmentação';
```

### 2. Novo service: `job_manager_service.py`

Métodos necessários:
- `criar_job(seg_id)` → chama Databricks SDK `w.jobs.create(...)`
- `pausar_job(seg_id)` → `w.jobs.update(job_id, schedule=None)`
- `reativar_job(seg_id, cron)` → `w.jobs.update(job_id, schedule=cron)`
- `deletar_job(seg_id)` → `w.jobs.delete(job_id)`
- `executar_agora(seg_id)` → `w.jobs.run_now(job_id, params)`
- `atualizar_schedule(seg_id, cron)` → `w.jobs.update(job_id, schedule=cron)`

### 3. Integração nos endpoints existentes

```python
# Em segmentacao_service.py:
def ativar(self, seg_id, usuario):
    self.transicionar_status(seg_id, "ativa")
    job_id = self.job_manager.criar_job(seg_id)  # NOVO
    self.repository.atualizar(seg_id, {"job_id_databricks": job_id})

def pausar(self, seg_id, usuario):
    self.transicionar_status(seg_id, "pausada")
    self.job_manager.pausar_job(seg_id)  # NOVO

def reativar(self, seg_id, usuario):
    self.transicionar_status(seg_id, "ativa")
    self.job_manager.reativar_job(seg_id)  # NOVO

def encerrar(self, seg_id, usuario):
    self.transicionar_status(seg_id, "encerrada")
    self.job_manager.deletar_job(seg_id)  # NOVO
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
