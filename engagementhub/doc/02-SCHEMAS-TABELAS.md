# S3 — Schemas e Tabelas

> Modelo de dados do EngagementHub | Schema: `plataforma.engagement`
> 29 tabelas + 3 views | 10 DDLs

---

## 1. Mapa de Relacionamentos

```
  campanha (1)──▶(N) campanha_jornada ─▶ jornada (1)──▶(N) jornada_estado_cliente
     │                                     │                       │
     ├─ campanha_versao                    ├─ jornada_versao        ├─ jornada_log
     ├─ campanha_historico_estado           ├─ jornada_participacao  └─ jornada_teste
     │                                     ├─ config_jornada_politica
     ├─ campanha_prioridade (waterfall)     │
     │                                     └──▶ fila_disparo ─▶ disparo_tentativa
     │                                              │
     │                                              └─▶ tracking_disparo
     │
     ├─ peca (N, reutilizável)
     │    ├─ peca_versao
     │    ├─ peca_aprovacao
     │    └─ asset
     │
     └─ disparo_avulso (DAV, vinculado opcional)

  Configs independentes:
    regras_capping | config_conversao | supressao_optout
    config_janela_envio | config_retry | catalogo_canais | whatsapp_templates
    config_otimizacao | otimizacao_variante | otimizacao_resultado | otimizacao_historico
    saude_operacional | notificacao

  Views (contratos de saída):
    segmento_campanha_map | cliente_jornada_status | variaveis_disponiveis
```

---

## 2. DDL 01 — Campanha

### `campanha`
| Coluna | Tipo | Descrição |
|---|---|---|
| campanha_id | STRING PK | UUID |
| campanha_codigo | STRING | CAM-2025-CROSSSELL-00015 |
| nome | STRING | Nome de exibição |
| descricao | STRING | Descrição livre |
| objetivo | STRING | Objetivo de negócio |
| tags | ARRAY<STRING> | Tags de categorização |
| owner | STRING | Dono |
| area_responsavel | STRING | Área |
| status | STRING | rascunho/em_aprovacao/aprovada/ativa/pausada/encerrada/concluida |
| vigencia_inicio | TIMESTAMP | Início (guardião ativa) |
| vigencia_fim | TIMESTAMP | Fim (guardião conclui) |
| limite_envios | BIGINT | NULL = ilimitado |
| alerta_pct_limite | INT | % para alertar aproximação do limite |
| envios_realizados | BIGINT | Contador incremental |
| versao_atual | INT | Versão corrente |

### `campanha_versao`
| Coluna | Tipo | Descrição |
|---|---|---|
| campanha_id | STRING FK | |
| versao | INT | Número sequencial |
| snapshot_json | STRING | Estado completo no momento |
| alterado_por | STRING | Quem editou |
| motivo | STRING | Nota da alteração |

### `campanha_historico_estado`
| Coluna | Tipo | Descrição |
|---|---|---|
| hist_id | STRING PK | |
| campanha_id | STRING FK | |
| estado_anterior | STRING | |
| estado_novo | STRING | |
| motivo | STRING | Justificativa |
| alterado_por | STRING | |

### `campanha_jornada`
| Coluna | Tipo | Descrição |
|---|---|---|
| campanha_id | STRING FK | |
| jornada_id | STRING FK | |
| ordem | INT | Ordem de exibição |
| ativo | BOOLEAN | |

---

## 3. DDL 02 — Waterfall + Capping

### `campanha_prioridade`
| Coluna | Tipo | Descrição |
|---|---|---|
| campanha_id | STRING FK | |
| prioridade | INT | Menor = maior prioridade (drag-drop) |
| dias_espera_cascata | INT | Dias até liberar próxima campanha |

### `regras_capping`
| Coluna | Tipo | Descrição |
|---|---|---|
| regra_id | STRING PK | |
| canal | STRING | Filtro por canal (ou global) |
| max_mensagens | INT | Limite no período |
| periodo | STRING | dia/semana/mes |
| intervalo_minimo_horas | INT | Cooldown entre envios |
| escopo | STRING | global/por_campanha |
| prioritaria_ignora_cap | BOOLEAN | Campanha prioritária fura cap |

### `config_conversao`
| Coluna | Tipo | Descrição |
|---|---|---|
| config_id | STRING PK | |
| escopo | STRING | global/por_campanha |
| evento_conversao | STRING | abriu/clicou/converteu |
| janela_dias | INT | Janela de atribuição |

### `supressao_log`
| Coluna | Tipo | Descrição |
|---|---|---|
| supressao_id | STRING PK | |
| cpf_cnpj | STRING | Cliente suprimido |
| campanha_id | STRING | Campanha relacionada |
| canal | STRING | Canal |
| motivo | STRING | opt_out/capping/waterfall/blacklisted/janela |
| detalhe | STRING | Explicação legível |

---

## 4. DDL 03 — Canais

### `catalogo_canais`
| Coluna | Tipo | Descrição |
|---|---|---|
| canal_id | STRING PK | email, whatsapp, sms... |
| nome_exibicao | STRING | Nome amigável |
| suporta_html | BOOLEAN | Capacidade |
| suporta_imagem | BOOLEAN | Capacidade |
| suporta_botoes | BOOLEAN | Capacidade |
| max_caracteres | INT | Limite de texto |
| formato_editor | STRING | rico_html/mensagem_simples/card |
| provider_class | STRING | Classe Python (EmailProvider/WhatsAppProvider) |
| rate_limit_por_segundo | INT | Throttling |
| rate_limit_por_dia | INT | Limite diário |

---

## 5. DDL 04 — Peças

### `peca`
| Coluna | Tipo | Descrição |
|---|---|---|
| peca_id | STRING PK | |
| peca_codigo | STRING | PEC-2025-EMAIL-00087 (canal no código) |
| nome, descricao | STRING | |
| canal | STRING | email/whatsapp |
| conteudo_json | STRING | Estrutura do editor (GrapesJS/mensagem) |
| html_renderizado | STRING | Cache do HTML final |
| assunto | STRING | Assunto (email) |
| template_meta_id | STRING | ID HSM aprovado (WhatsApp) |
| variaveis_usadas | ARRAY<STRING> | Variáveis incluídas na peça |
| status_aprovacao | STRING | rascunho/em_aprovacao/aprovada/reprovada |
| versao_atual | INT | |

### `peca_versao`, `peca_aprovacao`, `whatsapp_templates`, `asset`
Estruturas de suporte (versões, aprovação multi-etapa, templates Meta, gerenciamento de imagens).

### View: `variaveis_disponiveis`
```sql
SELECT caracteristica_id AS campo_id, campo_label, tipo_dado, descricao
FROM plataforma.metadata.catalogo_caracteristicas
WHERE ativo = true AND sensibilidade = 'normal' AND usavel_em_peca = true;
```

---

## 6. DDL 05 — Jornadas

### `jornada`
| Coluna | Tipo | Descrição |
|---|---|---|
| jornada_id | STRING PK | |
| jornada_codigo | STRING | JOR-2025-00015-01 |
| campanha_id | STRING FK | Vínculo com campanha |
| grafo_json | STRING | Grafo React Flow (nós + arestas + loops) |
| seg_entrada_id | STRING | seg_id do S1 — PONTE para contratos de saída |
| status | STRING | rascunho/aprovada/ativa/pausada/encerrada |
| ao_sair_segmento | STRING | continua/remove (sobrescreve política global) |

### `jornada_estado_cliente`
| Coluna | Tipo | Descrição |
|---|---|---|
| estado_id | STRING PK | |
| jornada_id | STRING FK | |
| cpf_cnpj | STRING | Cliente |
| no_atual | STRING | Nó em que está |
| status | STRING | ativo/aguardando/concluido/saiu |
| proxima_acao_em | TIMESTAMP | Quando motor processa de novo |
| historico_nos | ARRAY<STRING> | Nós percorridos |

> Base do contrato `cliente_jornada_status` (view para o S2)

### `jornada_participacao`, `jornada_log`, `jornada_teste`, `config_jornada_politica`
Controle de reentrada, auditoria por nó, preview/simulação, políticas configuráveis.

---

## 7. DDL 06 — Disparo

### `fila_disparo`
| Coluna | Tipo | Descrição |
|---|---|---|
| fila_id | STRING PK | |
| cpf_cnpj | STRING | Destinatário |
| campanha_id, jornada_id, no_id | STRING | Contexto |
| peca_id | STRING | Peça a renderizar |
| canal | STRING | Canal de envio |
| destinatario | STRING | Email ou telefone resolvido |
| agendado_para | TIMESTAMP | Quando enviar |
| status | STRING | pendente/enviado/falha/suprimido |
| tentativas | INT | Contador de retry |

### `disparo_tentativa`
Registra cada tentativa (sucesso/falha_temporaria/falha_permanente) com response do provider.

### `disparo_avulso`
Envio standalone ou vinculado a campanha. Contadores: qtd_publico, qtd_elegivel, qtd_enviado.

### `config_janela_envio`, `config_retry`
Horários permitidos por canal + política de retry com backoff.

---

## 8. DDL 07 — Tracking

### `tracking_disparo`
| Coluna | Tipo | Descrição |
|---|---|---|
| envio_id | STRING PK | Único (idempotência) |
| cpf_cnpj | STRING | CLUSTER BY |
| campanha_id, jornada_id, peca_id | STRING | Contexto |
| canal | STRING | |
| enviado_em | TIMESTAMP | |
| entregue_em | TIMESTAMP | Webhook provider |
| visualizado_em | TIMESTAMP | WhatsApp read |
| aberto_em | TIMESTAMP | Pixel email |
| clicou_em | TIMESTAMP | Redirect |
| converteu_em | TIMESTAMP | Preenchido pelo consumidor_conversao (S2→S3) |
| status_atual | STRING | Funil: enviado/entregue/visualizado/aberto/clicou/converteu/falha |

> **CONTRATO:** Lido por S2 (engajamento) e S4 (KPIs). `converteu_em` vem do evento `retorno_atendimento` do S2.

---

## 9. DDL 08 — Otimização MAB

### `config_otimizacao`
Config Thompson Sampling: métrica_alvo, trafego_minimo_pct, min_amostras, frequência.

### `otimizacao_variante`
Arms do bandit: jornada_id, no_id (A/B Split), peca_id, peso_atual.

### `otimizacao_resultado`
Contadores por variante: envios, aberturas, cliques, conversões.

### `otimizacao_historico`
Transparência: peso_anterior → peso_novo + motivo.

---

## 10. DDL 09 — Operação

### `saude_operacional`
Health checks: filas travadas, rate limit, taxa falha, template rejeitado.

### `notificacao`
Alertas in-app com severidade (info/alerta/critico).

---

## 11. DDL 10 — Contratos de Saída (Views)

### View: `segmento_campanha_map`
```sql
-- Ponte: seg_id (S1) → campanha(s) (S3) via jornada.seg_entrada_id
SELECT DISTINCT j.seg_entrada_id AS seg_id, c.campanha_id, c.campanha_codigo, ...
FROM jornada j JOIN campanha c ON c.campanha_id = j.campanha_id
WHERE j.seg_entrada_id IS NOT NULL;
```

### View: `cliente_jornada_status`
```sql
-- Posição do cliente na jornada (contrato limpo para S2)
SELECT e.cpf_cnpj, e.jornada_id, e.no_atual, e.status, e.historico_nos, ...
FROM jornada_estado_cliente e JOIN jornada j ...
```

---

## 12. Totais

| DDL | Tabelas | Views |
|---|---|---|
| 01_campanha | 4 | 0 |
| 02_waterfall_capping | 4 | 0 |
| 03_canais | 1 | 0 |
| 04_pecas | 5 | 1 (variaveis_disponiveis) |
| 05_jornadas | 7 | 0 |
| 06_disparo | 5 | 0 |
| 07_tracking | 1 | 0 |
| 08_otimizacao | 4 | 0 |
| 09_operacao | 2 | 0 |
| 10_contratos_saida | 0 | 2 |
| **Total** | **33** | **3** |

---

## 13. Validação DDL vs Roadmap

| Status | Observação |
|---|---|
| ✅ Alinhado | Todas as tabelas referenciadas nos 29 cartões existem nos DDLs |
| ✅ Naming | `supressao_log` (renomeado de `supressao_optout` para consistência) |
| ✅ Views | 3 views com lógica correta (contratos S2 + variáveis S1) |
| ✅ Dependências | S1 (seg_resultado_corrente), S0 (consentimento, golden_record) referenciados |

---

*Gerado a partir dos DDLs em `databricks/ddl/s3_engagement/` — Agosto 2026.*
