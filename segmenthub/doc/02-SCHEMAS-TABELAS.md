# Schemas e Tabelas — SegmentHub

> Modelo de dados completo do catálogo `plataforma` utilizado pelo S1.

---

## Diagrama de Relacionamentos (ER)

```
  ┌────────────────────────────── RELACIONAMENTOS PRINCIPAIS ──────────────────────────────┐
  │                                                                                  │
  │  CATALOGO_PUBLICOS ──────────┐                                                    │
  │  USUARIOS_PERFIL ────────────┤                                                    │
  │                                ▼                                                    │
  │                    ╔═════════════════════╗                                       │
  │                    ║   SEG_DEFINICAO     ║───┬───┬───┬───┬───┬───┬───┐        │
  │                    ║   (tabela central)  ║   │   │   │   │   │   │   │        │
  │                    ╚═════════════════════╝   │   │   │   │   │   │   │        │
  │                          │                    │   │   │   │   │   │   │        │
  │  ┌────────────────────┼────────────────────┼───┼───┼───┼───┼───┼───┘   │
  │  │                    │                    │   │   │   │   │   │            │
  │  ▼                    ▼                    ▼   ▼   ▼   ▼   ▼   ▼            │
  │  SEG_       SEG_         SEG_      SEG_  SEG_  SEG_  SEG_ SEG_          │
  │  EXECUCAO   VERSAO       DESTINO   COMENT NOTIF SAUDE HIST JOB_LOG      │
  │  │                                                   (1:1)              │
  │  ├────────────────┐                                                          │
  │  ▼                ▼                                                          │
  │  SEG_RESULTADO    SEG_RESULTADO                                               │
  │  _CORRENTE        _HISTORICO                                                  │
  │  │                                                                            │
  │  ▼                                                                            │
  │  (seg_overlap removido — funcionalidade descontinuada)                          │
  │                                                                                │
  │  CATALOGO_CARACTERISTICAS ──▶ CATALOGO_GOVERNANCA_HIST                          │
  │                                                                                │
  └─────────────────────────────────────────────────────────────────────────────────┘

  Legenda:  ══  tabela principal  │  ──▶  relação 1:N  │  (1:1) relação 1:1
```

---

## Schema: `plataforma.metadata`

Catálogo no-code — mapeia campos amigáveis para colunas físicas.

### `catalogo_caracteristicas`

Tabela central do Builder. Cada linha é um campo disponível para segmentação.

| Coluna | Tipo | Descrição |
|---|---|---|
| `caracteristica_id` | STRING PK | ID único do campo |
| `tema` | STRING | Agrupamento no menu (ex: Financeiro, Comportamento) |
| `tema_ordem` | INT | Ordenação do tema |
| `tabela_fisica` | STRING | Tabela real no Unity Catalog |
| `tabela_label` | STRING | Nome amigável da tabela |
| `campo_fisico` | STRING | Coluna real |
| `campo_label` | STRING | Nome exibido ao usuário |
| `tipo_dado` | STRING | `numeric` / `categorical` / `date` / `boolean` |
| `operadores` | ARRAY\<STRING\> | Operadores válidos (=, >, in, between...) |
| `valores_dominio` | ARRAY\<STRING\> | Domínio para categóricos |
| `join_key` | STRING | Chave de junção (ex: cpf_cnpj) |
| `sensibilidade` | STRING | `normal` / `sensível` / `lgpd` |
| `usavel_em_peca` | BOOLEAN | Flag consumida pelo S3 (variável de peça) |
| `usavel_em_visao360` | BOOLEAN | Flag consumida pelo S2 (Visão 360) |
| `bloco_visao360` | STRING | Bloco sugerido: cadastral/financeiro/produtos/comportamento |
| `ativo` | BOOLEAN | Disponível no catálogo |
| `descricao` | STRING | Descrição funcional |

**Índices:** Bloom Filter em `caracteristica_id`, `campo_label`  
**Cluster By:** `tema`  
**Nota:** Flags `usavel_em_*` são administradas pelo S1 (admin) mas **não consumidas** na lógica de segmentação.

---

### `catalogo_publicos`

Públicos-base pré-definidos (ponto de partida de toda segmentação).

| Coluna | Tipo | Descrição |
|---|---|---|
| `publico_id` | STRING PK | ID do público |
| `nome` | STRING | Nome amigável |
| `descricao` | STRING | Descrição |
| `tabela_fisica` | STRING | Tabela física (schema `publico`) |
| `join_key` | STRING | Coluna PK (ex: cpf_cnpj) |
| `criado_por_time` | STRING | Time responsável |
| `ativo` | BOOLEAN | Disponível |

---

### `catalogo_governanca_hist`

Trilha de auditoria: quem liberou/retirou características para S2/S3.

| Coluna | Tipo | Descrição |
|---|---|---|
| `hist_id` | STRING PK | ID do registro |
| `caracteristica_id` | STRING FK | Característica alterada |
| `campo_label` | STRING | Snapshot do label |
| `flag_alterada` | STRING | `usavel_em_visao360` / `usavel_em_peca` / `bloco_visao360` / `ativo` |
| `sistema_alvo` | STRING | `s2` / `s3` / `global` |
| `valor_anterior` | STRING | Valor antes da mudança |
| `valor_novo` | STRING | Valor após mudança |
| `acao` | STRING | `liberou` / `retirou` / `alterou_bloco` |
| `alterado_por` | STRING | Usuário que fez a alteração |
| `alterado_em` | TIMESTAMP | Data/hora |

**Política:** Append-only (nunca update/delete).

---

### `campos_em_uso` (VIEW)

Campos referenciados por segmentações ativas (proteção de metadado).

| Coluna | Tipo | Lógica |
|---|---|---|
| `campo_id` | STRING | Extraído via regex do `regras_json` |
| `qtd_segmentacoes_ativas` | BIGINT | COUNT DISTINCT seg_id |
| `segmentacoes` | ARRAY\<STRING\> | Lista de seg_codigo |

---

## Schema: `plataforma.segmentacao`

Núcleo produtor — armazena definições, resultados e monitoramento.

### `seg_definicao`

Tabela principal. Cada linha = 1 segmentação.

| Coluna | Tipo | Descrição |
|---|---|---|
| `seg_id` | STRING PK | Chave única |
| `seg_codigo` | STRING | Código amigável (SEG-NOME-HASH) |
| `seg_slug` | STRING | URL-friendly |
| `nome` | STRING | Nome da segmentação |
| `descricao` | STRING | Descrição |
| `objetivo` | STRING | AQUISICAO/RENTABILIZACAO/RETENCAO/ENGAJAMENTO/COBRANCA |
| `seg_tags` | ARRAY\<STRING\> | Tags livres |
| `resumo` | STRING | Resumo funcional |
| `objetivo_negocio` | STRING | Contexto de negócio |
| `publico_alvo_descricao` | STRING | Descrição do público |
| `observacoes` | STRING | Notas adicionais |
| `documentacao_md` | STRING | Markdown explicativo |
| `owner` | STRING | Responsável |
| `area_responsavel` | STRING | Área |
| `email_contato` | STRING | E-mail para alertas |
| `criado_por` | STRING | Criador |
| `criado_em` | TIMESTAMP | Data de criação |
| `seg_origem_id` | STRING | Link com segmentação pai (clone) |
| `tipo_origem` | STRING | `nova` / `clone` / `derivada` / `chatbot` |
| `tipo` | STRING | `direta` / `composta` |
| `publico_base_id` | STRING FK | Público-base selecionado |
| `regras_json` | STRING | Árvore de regras (JSON) |
| `status` | STRING | `rascunho` / `em_aprovacao` / `ativa` / `pausada` / `encerrada` / `arquivada` |
| `vigencia_inicio` | TIMESTAMP | Início da vigência |
| `vigencia_fim` | TIMESTAMP | Fim da vigência |
| `agendamento_cron` | STRING | Expressão Quartz (6 campos) |
| `recorrencia` | STRING | `once` / `diaria` / `semanal` / `mensal` |
| `aprovado_por` | STRING | Quem aprovou |
| `aprovado_em` | TIMESTAMP | Quando aprovou |
| `checklist_validacao_json` | STRING | Checklist de aprovação |
| `versao_atual` | INT | Versão corrente |
| `atualizado_em` | TIMESTAMP | Última atualização |
| `habilitado` | BOOLEAN | Soft-enable |
| `job_id_databricks` | STRING | ID do Databricks Job (job-per-segment) |

**Cluster By:** `status, objetivo, owner`  
**Índices:** Bloom Filter em `seg_id`, `seg_codigo`, `seg_slug`  
**Contrato:** Lida por S2, S3, S4 (GRANT SELECT)

---

### `seg_execucao`

Registro de cada execução/recálculo.

| Coluna | Tipo | Descrição |
|---|---|---|
| `exec_id` | STRING PK | Formato: `exec_{seg_id}_{YYYYMMDD_HHMMSS}` |
| `seg_id` | STRING FK | Segmentação |
| `versao_usada` | INT | Versão da regra usada |
| `origem_execucao` | STRING | `agendada` / `manual` / `reativacao` |
| `executado_em` | TIMESTAMP | Início |
| `qtd_clientes` | BIGINT | COUNT exato |
| `status` | STRING | `sucesso` / `erro` / `erro_metadado` / `rodando` / `falha_timeout` |
| `job_id` | STRING | Databricks Job ID |
| `run_id` | STRING | Run ID |
| `job_run_url` | STRING | URL do run |

---

### `seg_resultado_corrente`

Estado ATUAL do público (snapshot mais recente via MERGE).

| Coluna | Tipo | Descrição |
|---|---|---|
| `seg_id` | STRING PK (composta) | Segmentação |
| `cpf_cnpj` | STRING PK (composta) | Cliente |
| `exec_id` | STRING | Execução que incluiu |
| `entrou_em` | TIMESTAMP | Quando entrou |

**Cluster By:** `seg_id, cpf_cnpj`  
**Contrato:** Lida por S2, S3 (GRANT SELECT) — contrato-chave de integração

---

### `seg_resultado_historico`

Append-only: snapshot completo por execução (auditoria).

| Coluna | Tipo | Descrição |
|---|---|---|
| `exec_id` | STRING PK (composta) | Execução |
| `seg_id` | STRING | Segmentação |
| `versao_usada` | INT | Versão |
| `cpf_cnpj` | STRING PK (composta) | Cliente |
| `snapshot_em` | TIMESTAMP | Momento do snapshot |

**Retenção:** 90 dias (arquivos deletados), 365 dias (log Delta)

---

### `seg_versao`

Histórico de versões de regras.

| Coluna | Tipo | Descrição |
|---|---|---|
| `versao_id` | STRING PK | ID |
| `seg_id` | STRING FK | Segmentação |
| `versao` | INT | Número sequencial |
| `regras_json` | STRING | Regras daquela versão |
| `motivo` | STRING | Nota de versão |
| `alterado_por` | STRING | Quem alterou |
| `alterado_em` | TIMESTAMP | Quando |

---

### `seg_historico_estado`

Auditoria de transições de status.

| Coluna | Tipo | Descrição |
|---|---|---|
| `hist_id` | STRING PK | ID |
| `seg_id` | STRING FK | Segmentação |
| `estado_anterior` | STRING | Status antes |
| `estado_novo` | STRING | Status depois |
| `motivo` | STRING | Razão |
| `alterado_por` | STRING | Quem |
| `alterado_em` | TIMESTAMP | Quando |

---

### `seg_destino`

Natureza da segmentação (humano/digital). **Contrato-chave** (Decisão #2).

| Coluna | Tipo | Descrição |
|---|---|---|
| `seg_id` | STRING PK (composta) | Segmentação |
| `destino` | STRING PK (composta) | `sistema2` (humano) / `sistema3` (digital) |
| `habilitado` | BOOLEAN | Ativo |
| `criado_em` | TIMESTAMP | Data |

**Contrato:** Lida por S2, S3, S4.

---

### `seg_saude`

Health status por segmentação (populado pelo job de saúde).

| Coluna | Tipo | Descrição |
|---|---|---|
| `seg_id` | STRING PK | Segmentação |
| `health_status` | STRING | `verde` / `amarelo` / `vermelho` |
| `ultima_verificacao` | TIMESTAMP | Última checagem |
| `variacao_publico_pct` | DOUBLE | Variação % entre execuções |
| `taxa_sucesso_exec` | DOUBLE | % de execuções bem-sucedidas |
| `tempo_medio_exec_seg` | INT | Tempo médio (segundos) |
| `alertas_json` | STRING | Alertas ativos (JSON) |
| `publico_atual` | BIGINT | Tamanho atual |

---

### ~~`seg_overlap`~~ (REMOVIDA)

> Funcionalidade de overlap descontinuada. Tabela removida do schema.

---

### `seg_comentario`

Thread de comentários colaborativos.

| Coluna | Tipo | Descrição |
|---|---|---|
| `comentario_id` | STRING PK | ID |
| `seg_id` | STRING FK | Segmentação |
| `versao_referencia` | INT | Versão ref |
| `tipo` | STRING | Tipo do comentário |
| `autor` | STRING | Quem escreveu |
| `texto` | STRING | Conteúdo |
| `respondendo_a` | STRING FK | Comentário pai (thread) |
| `mencoes` | ARRAY\<STRING\> | Usuários mencionados |
| `resolvido` | BOOLEAN | Marcado como resolvido |
| `criado_em` | TIMESTAMP | Data |
| `editado_em` | TIMESTAMP | Última edição |

---

### `seg_notificacao`

Notificações in-app.

| Coluna | Tipo | Descrição |
|---|---|---|
| `notif_id` | STRING PK | ID |
| `destinatario` | STRING | Usuário destino |
| `tipo` | STRING | `mencao` / `alerta_saude` / `mudanca_estado` |
| `seg_id` | STRING FK | Segmentação relacionada |
| `titulo` | STRING | Título |
| `mensagem` | STRING | Corpo |
| `lida` | BOOLEAN | Lida/não lida |
| `criado_em` | TIMESTAMP | Data |

---

### `seg_job_log`

Log de auditoria do JobManagerService.

| Coluna | Tipo | Descrição |
|---|---|---|
| `log_id` | STRING PK | ID |
| `seg_id` | STRING FK | Segmentação |
| `acao` | STRING | `criar` / `pausar` / `reativar` / `deletar` / `executar` / `atualizar_schedule` |
| `job_id` | STRING | Databricks Job ID |
| `run_id` | STRING | Run ID |
| `status` | STRING | `sucesso` / `erro` |
| `detalhes` | STRING | Detalhes/erro (JSON) |
| `executado_por` | STRING | Usuário |
| `criado_em` | TIMESTAMP | Data |

---

## Schema: `plataforma.eventos`

### `seg_eventos`

Eventos produzidos pelo S1 (consumidos por S3 e S4).

| Coluna | Tipo | Descrição |
|---|---|---|
| `evento_id` | STRING PK | ID |
| `seg_id` | STRING | Segmentação |
| `exec_id` | STRING | Execução (se aplicável) |
| `tipo_evento` | STRING | `publicada` / `executada` / `aprovada` / `pausada` / `encerrada` / `reativada` |
| `destino` | STRING | Sistema consumidor |
| `payload_json` | STRING | `{seg_id, seg_codigo, versao_usada, qtd_clientes, destino}` |
| `criado_em` | TIMESTAMP | Data |

---

## Schema: `plataforma.governanca`

### `usuarios_perfil`

RBAC unificado dos 4 sistemas.

| Coluna | Tipo | Descrição |
|---|---|---|
| `usuario_id` | STRING | Email do usuário |
| `nome` | STRING | Nome |
| `sistema` | STRING | `segmenthub` / `clientview360` / `engagement` / `analytics` |
| `perfil` | STRING | `admin` / `analista` / `gerente` / `vendedor` / `viewer` |
| `ativo` | BOOLEAN | Ativo |
| `concedido_por` | STRING | Quem concedeu |
| `concedido_em` | TIMESTAMP | Quando |

---

## Schemas de Origem (Leitura)

### `plataforma.caracteristicas.customer_features_wide`

Tabela de features de clientes. Mapeada pelo `catalogo_caracteristicas` para os campos físicos.

### `plataforma.publico.pub_*`

Públicos-base (ex: `pub_pf_ativos`, `pub_pj_mei`). Referenciados por `catalogo_publicos.tabela_fisica`.

### `plataforma.core_cliente.golden_record`

Cadastro consolidado (cpf_cnpj, nome, email, telefone, segmento, agência).

---

*Baseado nos DDLs reais em `/databricks/ddl/s0_comum/` e `/databricks/ddl/s1_segmenthub/`.*