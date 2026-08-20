# ADR-001: Tabela Única vs Table-Per-Segment para Resultados

> Architecture Decision Record — Plataforma CDP (S1/S2/S3)

**Status:** Aceita 
**Data:** 2026-08-20 
**Decisão:** Manter tabela única `seg_resultado_corrente` com MERGE 
**Rejeitada:** Criar 2 tabelas por segmento (ativa + histórica)

---

## 1. Contexto

O S1 (SegmentHub) executa \~1.000 segmentações, cada uma com milhares a dezenas de milhares de clientes. Cada execução produz a população atual do segmento. Consumidores (S2, S3) precisam consultar "quem está neste segmento agora".

Foi levantada a hipótese de criar **2 tabelas por segmento** (corrente + histórica) ao invés de usar uma tabela única compartilhada.

---

## 2. Cenário de Escala

| Métrica | Valor |
|---|---|
| Segmentos ativos | \~1.000 |
| Clientes médios por segmento | \~50.000 |
| Rows em seg_resultado_corrente | \~50M |
| Execuções por dia | \~200 (mix diário/semanal/mensal) |
| Concorrência máxima | \~20 Jobs simultâneos |

---

## 3. Opção A: Tabela Única com MERGE (ESCOLHIDA)

### Arquitetura

```
plataforma.segmentacao.seg_resultado_corrente
  CLUSTER BY (seg_id, cpf_cnpj)
  Colunas: seg_id, cpf_cnpj, exec_id, entrou_em

plataforma.segmentacao.seg_resultado_historico
  CLUSTER BY (seg_id, exec_id)
  Colunas: exec_id, seg_id, versao_usada, cpf_cnpj, snapshot_em
```

### Operação de escrita (seg_exec)

```sql
MERGE INTO seg_resultado_corrente AS target
USING (SELECT :seg_id AS seg_id, cpf_cnpj FROM resultado_novo) AS source
ON target.seg_id = source.seg_id AND target.cpf_cnpj = source.cpf_cnpj
WHEN NOT MATCHED THEN INSERT (seg_id, cpf_cnpj, exec_id, entrou_em)
  VALUES (source.seg_id, source.cpf_cnpj, :exec_id, current_timestamp())
WHEN NOT MATCHED BY SOURCE AND target.seg_id = :seg_id THEN DELETE;
```

### Semântica por cenário

| Cenário | Comportamento | `entrou_em` |
|---|---|---|
| Cliente **permanece** no segmento | Nenhuma ação (row intocado) | Preservado (data original) |
| Cliente **novo** entra | INSERT | `current_timestamp()` |
| Cliente **sai** do segmento | DELETE | Row removido |
| Cliente **volta** ao segmento | INSERT (novo ingresso) | `current_timestamp()` (nova data) |

### Por que funciona em escala

1. **Data skipping**: `CLUSTER BY (seg_id)` garante que `WHERE seg_id = ?` lê apenas os arquivos relevantes, não a tabela inteira
2. **Concorrência**: Jobs de seg_ids diferentes tocam arquivos físicos distintos → sem conflito de escrita (optimistic concurrency)
3. **50M rows**: trivial para Delta Lake (producão Databricks routineiramente opera com bilhões)
4. **MERGE eficiente**: a cláusula `target.seg_id = :seg_id` faz pruning — só reescreve arquivos do segmento em questão

---

## 4. Opção B: Table-Per-Segment (REJEITADA)

### Arquitetura proposta

```
plataforma.segmentacao.seg_{seg_id}_corrente     × 1.000
plataforma.segmentacao.seg_{seg_id}_historico    × 1.000
= 2.000 tabelas no Unity Catalog
```

### Problemas identificados

| Problema | Impacto |
|---|---|
| **2.000 tabelas** no metastore | Overhead de metadata, UI lenta, GRANTs explosivos |
| **Overlap analysis impossível** | `seg_overlap` precisaria UNION ALL de 1.000 tabelas |
| **S2/S3 quebram** | `WHERE seg_id = ?` não funciona — precisaria routing dinâmico para nome de tabela |
| **Governança** | 2.000 GRANTs ao invés de 2 |
| **Manutenção** | OPTIMIZE/VACUUM em 2.000 tabelas |
| **Lifecycle** | Criar/deletar tabelas quando segmento é criado/arquivado |
| **Naming collision** | seg_id com caracteres especiais em nomes de tabela |

---

## 5. Por que DELETE+INSERT Também Foi Rejeitado

Foi considerado substituir MERGE por DELETE+INSERT (mais simples):

```sql
-- REJEITADO:
DELETE FROM seg_resultado_corrente WHERE seg_id = :seg_id;
INSERT INTO seg_resultado_corrente SELECT ...;
```

**Problema crítico:** Perde `entrou_em` de clientes que permanecem no segmento.

| Dia | Evento | Com MERGE | Com DELETE+INSERT |
|---|---|---|---|
| 1 | Cliente A entra | entrou_em = Dia 1 | entrou_em = Dia 1 |
| 2 | Seg re-executa (A continua) | entrou_em = Dia 1 ✅ | entrou_em = Dia 2 ❌ |
| 3 | S3 verifica "novos entrantes" | A não é novo ✅ | A parece novo ❌ |

Impactos:
* S3 poderia re-disparar comunicação para cliente que já recebeu
* Analytics de "tempo no segmento" ficam incorretos
* Políticas de reentrada (`config_jornada_politica`) perdem referência temporal

---

## 6. Tratamento de Reentrada (Cliente sai e volta)

O sistema lida com reentrada em 3 camadas:

```
┌──────────────────────────────────────────────────────┐
│ CAMADA 1 — S1 (seg_resultado_corrente)           │
│                                                      │
│ Dia 1: MERGE insere (entrou_em = Dia 1)              │
│ Dia 5: Cliente sai das regras → MERGE deleta          │
│ Dia 12: Cliente volta → MERGE insere (entrou_em = 12) │
├──────────────────────────────────────────────────────┤
│ CAMADA 2 — S3 (jornada_estado_cliente)               │
│                                                      │
│ Dia 1: Motor cria estado (status='ativo', no='enviar')│
│ Dia 5: Cliente não está mais no seg → ao_sair_segmento│
│         → 'continua' (termina jornada) ou 'remove'    │
│ Dia 12: Orquestrador vê CPF de novo → checa política  │
├──────────────────────────────────────────────────────┤
│ CAMADA 3 — S3 (config_jornada_politica)              │
│                                                      │
│ reentrada = 'bloqueada'                              │
│   → CPF já participou → ignora para sempre            │
│ reentrada = 'apos_dias' + reentrada_dias = 30        │
│   → Permite se saiu_em < 30 dias atrás               │
│ reentrada = 'permitida'                              │
│   → Cria novo estado, vezes_participou++             │
└──────────────────────────────────────────────────────┘
```

### Exemplo completo (timeline)

```
Dia 1:  S1 executa → Cliente A entra no segmento (entrou_em=Dia1)
        S3 orquestrador → vê A → enfileira na jornada
        Motor jornada → cria estado_cliente (status=ativo)
        Motor disparo → envia email

Dia 2:  S1 re-executa → Cliente A continua (MERGE não toca)
        S3 orquestrador → vê A → já tem estado ativo → IGNORA ✓

Dia 5:  S1 re-executa → Cliente A não bate mais nas regras → MERGE DELETE
        S3 motor jornada → detecta que A sumiu do segmento
        Política ao_sair_segmento='remove' → status='saiu'
        jornada_participacao: saiu_em=Dia5, status_final='saiu_segmento'

Dia 12: S1 re-executa → Cliente A volta (MERGE INSERT, entrou_em=Dia12)
        S3 orquestrador → vê A → checa participacao anterior
        Política reentrada='apos_dias', reentrada_dias=7
        Dia12 - Dia5 = 7 dias → PERMITE ✓
        Novo estado criado, vezes_participou=2
```

---

## 7. Escalabilidade do Histórico

**Preocupação real:** `seg_resultado_historico` é append-only e cresce:

```
1.000 segs × 50K clientes × 1 exec/dia × 90 dias retenção = 4.5B rows
```

**Mitigações implementadas:**

| Medida | Detalhe |
|---|---|
| `CLUSTER BY (seg_id, exec_id)` | Queries por segmento são eficientes |
| `targetFileSize = 1GB` | Menos arquivos, menos overhead |
| `VACUUM RETAIN 90 HOURS` | Mantido pelo DDL (manutenção periódica) |
| `seg_execucao.qtd_clientes` | Analytics agregado sem precisar do histórico |

**Opções futuras se necessário:**
* Guardar apenas **deltas** (quem entrou/saiu) ao invés de snapshot completo
* Reduzir retenção para 30 dias
* Mover histórico antigo para tabela cold (arquivo)
* Amostrar ao invés de guardar tudo (se só para analytics)

---

## 8. Impacto nos Consumidores

| Sistema | Contrato de leitura | Impacto da decisão |
|---|---|---|
| S3 (EngagementHub) | `SELECT cpf_cnpj WHERE seg_id = ?` | Zero — continua igual |
| S2 (ClientView) | `SELECT seg_id WHERE cpf_cnpj = ?` | Zero — continua igual |
| S4 (Analytics) | JOINs com seg_resultado para KPIs | Zero — tabela única facilita |
| seg_overlap | `JOIN seg_resultado a ON a.cpf_cnpj = b.cpf_cnpj` | Zero — impossível com table-per-seg |

---

## 9. Decisão Final

**Manter arquitetura atual (tabela única + MERGE)** porque:

1. Já está otimizada (Liquid Clustering por seg_id)
2. 50-100M rows é trivial para Delta Lake
3. MERGE preserva `entrou_em` (crítico para evitar re-disparo)
4. Não quebra S2/S3 (contrato `WHERE seg_id = ?` inalterado)
5. Permite seg_overlap e analytics cross-segment
6. Table-per-segment criaria 2.000 tabelas com overhead operacional inaceitável

---

*Documento criado em: 2026-08-20 | Validado com: DDL `s1_segmenthub/02_segmentacao.sql` + `seg_exec` notebook*
