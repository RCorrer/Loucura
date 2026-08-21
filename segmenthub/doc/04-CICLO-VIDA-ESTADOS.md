# Ciclo de Vida e Estados — SegmentHub

> Máquina de estados, transições, versionamento e governança de vigência.

---

## 1. Máquina de Estados da Segmentação

```
                        ┌─────────────────────────────────────────────────────────────┐
                        │              MÁQUINA DE ESTADOS — SEGMENTAÇÃO                │
                        └─────────────────────────────────────────────────────────────┘

    ╔══════════╗    Enviar p/     ╔══════════════╗     Aprovar       ╔═══════════╗    Ativar       ╔══════════╗
    ║ RASCUNHO ║───aprovação────▶ ║ EM_APROVAÇÃO ║───(checklist)───▶ ║ APROVADA  ║──(cria Job)─▶ ║  ATIVA   ║
    ╚══════════╝                  ╚══════════════╝                   ╚═══════════╝                  ╚══════════╝
         │              ▲              │                              │    │    │
         │              │  Rejeitar    │                   Pausar     │    │    │
         │              └──────────────┘                 (rm sched.)  │    │    │
         │                                                    │      │    │    │
         │                                                    ▼      │    │    │
         │                                              ╔══════════╗  │    │    │
         │                     Reativar (restaura sched)║ PAUSADA  ║◀─┘    │    │
         │                          ┌───────────────────╚══════════╝       │    │
         │                          │                        │             │    │
         │                          ▼                        │ Encerrar    │    │
         │                    ╔══════════╗                   │(deleta Job) │    │ Encerrar
         │    Reativar        ║  ATIVA   ║                   │             │    │(deleta Job)
         │  (cria novo Job)   ╚══════════╝                   │             │    │
         │                          ▲                        ▼             │    ▼
         │                          │                  ╔════════════╗      │  ╔════════════╗
         │                          └──────────────────║ ENCERRADA  ║      │  ║ ENCERRADA  ║
         │                                             ╚════════════╝      │  ╚════════════╝
         │                                                   │             │         │
         │  Arquivar                                         │ Arquivar    │         │
         ▼                                                   ▼             ▼         ▼
    ╔════════════════════════════════════════════════════════════════════════════════════╗
    ║                               ARQUIVADA  (terminal)                               ║
    ╚════════════════════════════════════════════════════════════════════════════════════╝
```

**Legenda:** `══` estado  │  `──▶` transição  │  Qualquer estado pode ir para ARQUIVADA

---

## 2. Descrição dos Estados

| Estado | Descrição | Job? | Executa? |
|---|---|---|---|
| ◻ `rascunho` | Em construção. Editável livremente. | Não | Não |
| ◧ `em_aprovacao` | Aguardando validação por admin. | Não | Não |
| ● `ativa` | Em produção. Job com schedule ativo. | **Sim** | **Sim** (cron) |
| ◐ `pausada` | Temporariamente parada. Resultado mantido. | Sim (sem schedule) | Não |
| ○ `encerrada` | Finalizada. Resultado preservado read-only. | Não (deletado) | Não |
| ✕ `arquivada` | Soft-delete definitivo. | Não (deletado) | Não |

---

## 3. Transições e Efeitos Colaterais

### 3.1 Aprovar

```
  ┌─────────────────────────────────────────────────────────────────────┐
  │  APROVAR (admin only)                                               │
  │                                                                     │
  │  ① Valida regras (Validator + catálogo)                             │
  │       │                                                             │
  │       ▼                                                             │
  │  ② Cria Databricks Job (SDK: jobs.create + schedule cron)           │
  │       │                                                             │
  │       ▼                                                             │
  │  ③ UPDATE seg_definicao SET status = 'ativa'                        │
  │       │                                                             │
  │       ▼                                                             │
  │  ④ INSERT seg_historico_estado (em_aprovacao → ativa)                │
  │       │                                                             │
  │       ▼                                                             │
  │  ⑤ INSERT eventos.seg_eventos (tipo = 'aprovada')                   │
  └─────────────────────────────────────────────────────────────────────┘
```

### 3.2 Pausar

```
  ┌─────────────────────────────────────────────────────────────────────┐
  │  PAUSAR                                                             │
  │                                                                     │
  │  ① jobs.update(schedule=None)  →  Job existe mas não roda           │
  │  ② UPDATE status = 'pausada'                                        │
  │  ③ INSERT seg_historico_estado                                       │
  │  ④ INSERT seg_eventos (tipo = 'pausada')                            │
  └─────────────────────────────────────────────────────────────────────┘
```

### 3.3 Reativar

```
  ┌─────────────────────────────────────────────────────────────────────┐
  │  REATIVAR                                                           │
  │                                                                     │
  │  ① jobs.update(schedule=cron)  →  Restaura agendamento              │
  │  ② UPDATE status = 'ativa'                                          │
  │  ③ INSERT seg_historico_estado                                       │
  │  ④ INSERT seg_eventos (tipo = 'reativada')                          │
  └─────────────────────────────────────────────────────────────────────┘
```

### 3.4 Encerrar

```
  ┌─────────────────────────────────────────────────────────────────────┐
  │  ENCERRAR                                                           │
  │                                                                     │
  │  ① jobs.delete(job_id)  →  Remove Job completamente                 │
  │  ② UPDATE status = 'encerrada'                                      │
  │  ③ INSERT seg_historico_estado                                       │
  │  ④ INSERT seg_eventos (tipo = 'encerrada')                          │
  └─────────────────────────────────────────────────────────────────────┘
```

### 3.5 Tabela Resumo de Transições

| Transição | Quem pode | Efeito no Job | Evento |
|---|---|---|---|
| `rascunho` → `em_aprovacao` | analista, admin | — | — |
| `em_aprovacao` → `aprovada` | **admin** | — | `aprovada` |
| `aprovada` → `ativa` | analista, admin | `jobs.create()` | — |
| `ativa` → `pausada` | analista, admin | `jobs.update(schedule=None)` | `pausada` |
| `pausada` → `ativa` | analista, admin | `jobs.update(schedule=cron)` | `reativada` |
| `ativa` → `encerrada` | analista, admin | `jobs.delete()` | `encerrada` |
| `encerrada` → `ativa` | analista, admin | `jobs.create()` (novo) | `reativada` |
| `*` → `arquivada` | analista, admin | `jobs.delete()` (se existir) | — |

---

## 4. Versionamento de Regras

```
  ╭───────────╮  Aprovar  ╭───────────╮  Editar   ╭───────────╮  Aprovar  ╭───────────╮
  │ v1        │─────────▶ │ v1        │─────────▶ │ v2        │─────────▶ │ v2        │ ...
  │ (rascunho)│           │ ● ATIVA   │           │ (rascunho)│           │ ● ATIVA   │
  ╰───────────╯           ╰───────────╯           ╰───────────╯           ╰───────────╯
                            em produção              editando                em produção
                            (continua)               (v1 continua             (v2 substitui
                                                      rodando)                v1 em prod.)
```

**Regras de versionamento:**

* Editar segmentação **ativa** → cria automaticamente `v+1` em rascunho
* Versão anterior **continua em produção** até a nova ser aprovada
* Cada versão armazena `regras_json` completo + `motivo` (nota obrigatória)
* Timeline unifica: versões + estados + execuções + comentários

**Tabela `seg_versao`:**

```
┌────────────┬────────────┬────────┬─────────────┬──────────────────┬──────────────┬─────────────┐
│ versao_id  │ seg_id     │ versao │ regras_json │ motivo           │ alterado_por │ alterado_em │
├────────────┼────────────┼────────┼─────────────┼──────────────────┼──────────────┼─────────────┤
│ v_001_...  │ seg_abc123 │ 1      │ {inclusao…} │ Criação inicial  │ rafael@...   │ 2026-08-01  │
│ v_002_...  │ seg_abc123 │ 2      │ {inclusao…} │ Ajuste de renda  │ rafael@...   │ 2026-08-15  │
└────────────┴────────────┴────────┴─────────────┴──────────────────┴──────────────┴─────────────┘
```

---

## 5. Vigência e Agendamento

```
  ┌─────────────── CICLO DE VIGÊNCIA ───────────────────────────────────────────────────┐
  │                                                                                     │
  │   CRIAÇÃO            PRODUÇÃO                                   ENCERRAMENTO        │
  │   ───────            ────────                                   ────────────        │
  │                                                                                     │
  │   ┌────────┐         ┌──────────────────────────────────┐       ┌──────────────┐    │
  │   │Rascunho│         │  vigencia_inicio                 │       │ vigencia_fim │    │
  │   │  ▸     │         │       │                          │       │      │       │    │
  │   │Aprovar │         │       ▼                          │       │      ▼       │    │
  │   └────┬───┘         │  Job criado (schedule ativo)     │       │ Job encerrado│    │
  │        │             │       │                          │       │ auto (exit)  │    │
  │        │             │       ▼                          │       └──────────────┘    │
  │        └────────────▶│  Exec ▸ Exec ▸ Exec ▸ Exec ▸ ...│──────────────▶             │
  │                      │  (recálculo periódico via cron)  │                           │
  │                      └──────────────────────────────────┘                           │
  └─────────────────────────────────────────────────────────────────────────────────────┘
```

| Campo | Tipo | Descrição |
|---|---|---|
| `vigencia_inicio` | TIMESTAMP | Quando o Job deve começar a executar |
| `vigencia_fim` | TIMESTAMP | Quando encerrar automaticamente |
| `recorrencia` | STRING | `once` (estático) / `diaria` / `semanal` / `mensal` |
| `agendamento_cron` | STRING | Quartz Cron (6 campos, timezone São Paulo) |

**Comportamento:**

* `recorrencia=once` → Job executa uma vez e segmentação fica estática
* `vigencia_fim` alcançado → notebook `seg_exec` detecta expiração e sai sem executar
* Atualização de cron → `jobs.update()` via JobManagerService

---

## 6. Fluxo de Clonagem

```
  ╔═══════════════════════╗     POST /clonar     ╔═══════════════════════╗
  ║ Segmentação Original  ║ ──────────────────▶  ║ Nova Segmentação      ║
  ║                       ║                      ║                       ║
  ║  seg_id: seg_abc123   ║                      ║  seg_id: seg_def456   ║
  ║  status: ativa        ║                      ║  status: rascunho     ║
  ║  versão: 3            ║                      ║  versão: 1            ║
  ╚═══════════════════════╝                      ║  tipo_origem: clone   ║
                                                 ║  seg_origem: abc123   ║
                                                 ╚═══════════════════════╝
```

| Herda | NÃO herda |
|---|---|
| regras_json, objetivo, tags | status (sempre rascunho) |
| documentação, área, observações | vigência, agendamento |
| publico_base, exclusão | resultado, execuções |
| — | job, histórico, comentários |

---

## 7. Auditoria Completa (seg_historico_estado)

Toda transição grava um registro imutável:

```
┌────────────────┬────────────────┬──────────────────────┬──────────────────────────────┬─────────────────────┐
│ estado_anterior│ estado_novo    │ motivo               │ alterado_por                 │ alterado_em         │
├────────────────┼────────────────┼──────────────────────┼──────────────────────────────┼─────────────────────┤
│ rascunho       │ em_aprovacao   │ Envio para aprovação │ analista@email.com      │ 2026-08-10 09:30:00 │
│ em_aprovacao   │ ativa          │ Aprovação + Job      │ admin@email.com         │ 2026-08-10 14:00:00 │
│ ativa          │ pausada        │ Pausa manual         │ usuario@email.com       │ 2026-08-15 14:30:00 │
│ pausada        │ ativa          │ Reativação manual    │ usuario@email.com       │ 2026-08-20 09:00:00 │
│ ativa          │ encerrada      │ Vigência expirada    │ system (guardião)            │ 2026-09-01 00:00:00 │
└────────────────┴────────────────┴──────────────────────┴──────────────────────────────┴─────────────────────┘
```

---

## 8. Destinos (Natureza da Segmentação)

```
                              ┌──────────────────────────────┐
                              │        SEGMENTAÇÃO           │
                              │        seg_destino           │
                              └──────────┬───────────────────┘
                                         │
                    ┌────────────────────┼─────────────────────┐
                    │                    │                     │
                    ▼                    ▼                     ▼
        ┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
        │ destino: sistema2 │ │ destino: sistema3 │ │ ambos (2 linhas)  │
        │ ▸ HUMANO          │ │ ▸ DIGITAL         │ │ ▸ HUMANO+DIGITAL  │
        └─────────┬─────────┘ └─────────┬─────────┘ └────┬────────┬────┘
                  │                     │                │        │
                  ▼                     ▼                ▼        ▼
        ┌─────────────────┐   ┌─────────────────┐  ┌──────┐ ┌──────┐
        │ S2 ClientView   │   │ S3 Engagement   │  │  S2  │ │  S3  │
        │ → Gerente atende│   │ → Disparo auto  │  └──────┘ └──────┘
        └─────────────────┘   └─────────────────┘
```

**Regras:**

* `seg_destino` aceita 1 ou 2 linhas por segmentação (sistema2 e/ou sistema3)
* Lido por S2, S3, S4 via GRANT SELECT (Decisão #2 do contrato)
* Toda segmentação com destino `sistema2` = **atendimento humano** (sempre)
* Destino `sistema3` = disparo digital (pode acumular com humano)

---

*Baseado na implementação real do `SegmentacaoService` e `JobManagerService`.*