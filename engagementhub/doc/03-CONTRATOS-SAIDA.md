# S3 — Contratos de Saída

> Interfaces estáveis produzidas pelo EngagementHub para consumo externo.
> DDL de produção: [`../sql/views_contratos.sql`](../sql/views_contratos.sql)

---

## 1. Visão Geral

O S3 expoe **5 contratos** para sistemas downstream:

| # | Contrato | Tipo | Consumidores | SLA |
|---|---|---|---|---|
| 1 | `segmento_campanha_map` | VIEW | S2, S4 | Near-realtime (view sobre tabelas ativas) |
| 2 | `cliente_jornada_status` | VIEW | S2, S4 | Near-realtime |
| 3 | `variaveis_disponiveis` | VIEW | Frontend, S4 | Estático (atualiza com metadata S1) |
| 4 | `tracking_disparo` | TABLE | S2, S4 | Append-only, latency \~5min (motor_disparo) |
| 5 | `disparo_eventos` | TABLE | S2, S4 | Append-only, latency \~1min (webhooks) |

---

## 2. Contrato: `segmento_campanha_map`

**Propósito:** Permite que S2 saiba quais campanhas digitais estão rodando para cada segmento, evitando conflitos de abordagem.

| Coluna | Tipo | Descrição |
|---|---|---|
| seg_id | STRING | ID do segmento (chave S1) |
| campanha_id | STRING | ID da campanha |
| campanha_codigo | STRING | Código legível (CAM-2025-...) |
| campanha_nome | STRING | Nome de exibição |
| campanha_status | STRING | ativa \| pausada |
| jornada_id | STRING | ID da jornada vinculada |
| jornada_nome | STRING | Nome da jornada |
| jornada_status | STRING | ativa \| pausada |
| canal | STRING | Canal principal (email/whatsapp) |
| vigencia_inicio | STRING | ISO 8601 início vigência |
| vigencia_fim | STRING | ISO 8601 fim vigência (NULL = sem fim) |

**JOINs source:** `campanha_jornada` → `campanha` + `jornada`

---

## 3. Contrato: `cliente_jornada_status`

**Propósito:** S2 consulta antes de abordar um cliente, evitando duplicidade (cliente já em jornada digital ativa).

| Coluna | Tipo | Descrição |
|---|---|---|
| cpf_cnpj | STRING | Identificador do cliente |
| jornada_id | STRING | ID da jornada |
| jornada_nome | STRING | Nome da jornada |
| no_atual_id | STRING | Nó onde o cliente está no grafo |
| status_participacao | STRING | ativo \| pausado \| concluido |
| entrou_em | STRING | ISO 8601 entrada na jornada |
| atualizado_em | STRING | ISO 8601 última movimentação |
| concluiu_em | STRING | ISO 8601 conclusão (NULL se ativo) |
| resultado | STRING | sucesso \| abandono \| timeout \| NULL |

**JOINs source:** `jornada_estado_cliente` + `jornada` + `jornada_participacao`

---

## 4. Contrato: `variaveis_disponiveis`

**Propósito:** Catálogo de variáveis disponíveis para personalização de peças.

| Coluna | Tipo | Descrição |
|---|---|---|
| campo_id | STRING | Identificador único da variável |
| campo_label | STRING | Label para o editor |
| tipo_dado | STRING | string \| number \| date \| boolean |
| descricao | STRING | Descrição para o analista |
| tabela_origem | STRING | Tabela UC de origem |
| coluna_origem | STRING | Coluna na tabela |

**Source:** `plataforma.metadata.catalogo_caracteristicas`

---

## 5. Contratos Tabela (acesso direto)

### `tracking_disparo`

Funil completo de cada envio: enviado → entregue → aberto → clicou → converteu.

| Coluna chave | Descrição |
|---|---|
| envio_id (PK) | ID único do envio |
| cpf_cnpj | Cliente |
| campanha_id | Campanha de origem |
| canal | email \| whatsapp |
| status_atual | Estado corrente no funil |
| enviado_em/entregue_em/aberto_em/clicou_em | Timestamps de cada etapa |

### `disparo_eventos`

Barramento de eventos granulares (usado por S4 para analytics).

| Coluna chave | Descrição |
|---|---|
| evento_id (PK) | UUID do evento |
| tipo_evento | envio, entrega, abertura, clique, conversao, erro |
| cpf_cnpj | Cliente |
| campanha_id / jornada_id | Contexto |
| ocorrido_em | Timestamp do evento |
| metadata_json | Payload extra (provider response, URL, etc) |

---

## 6. Permissões (GRANTs)

| Principal | Tipo | Acesso |
|---|---|---|
| `sp-s2-atendimentohub` | Service Principal | SELECT em views + tracking + eventos |
| `grp-s4-analytics` | Grupo | SELECT em views + tracking + eventos |

---

## 7. Regras de Evolução

1. **Aditividade:** Novas colunas podem ser adicionadas sem breaking change
2. **Remoção:** Deprecar por 30 dias (column comment) antes de remover
3. **Tipos:** Nunca mudar tipo de coluna existente
4. **Naming:** snake_case, sem prefixos de schema
5. **Versionamento:** Se breaking change inevitável, criar `_v2` e manter `_v1` por 90 dias

---

*DDL de produção com GRANTs: [`../sql/views_contratos.sql`](../sql/views_contratos.sql)*
