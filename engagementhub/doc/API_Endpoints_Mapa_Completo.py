# Databricks notebook source
# DBTITLE 1,EngagementHub (S3) — Mapa Completo de Endpoints + Validação DDL
# MAGIC %md
# MAGIC # EngagementHub (S3) — Mapa Completo de Endpoints + Validação DDL
# MAGIC
# MAGIC > 70 endpoints · 9 routers · 33 tabelas + 3 views · Catálogo `plataforma.engagement`
# MAGIC >
# MAGIC > **Stack:** FastAPI + Databricks App · **Auth:** JWT (admin/analista)
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## Visão Geral dos Routers
# MAGIC
# MAGIC | Router | Prefix | Endpoints | Status no main.py |
# MAGIC |--------|--------|-----------|--------------------|
# MAGIC | `campanha.py` | `/api/campanhas` | 9 | ✅ Montado |
# MAGIC | `peca.py` | `/api/pecas` | 10 | ✅ Montado |
# MAGIC | `canal.py` | `/api/canais` | 5 | ✅ Montado |
# MAGIC | `jornada.py` | `/api/jornadas` | 11 | ✅ Montado |
# MAGIC | `orquestrador.py` | `/api/admin/orquestrador` | 3 | ✅ Montado |
# MAGIC | `disparo.py` | `/api/disparo` | 5 | ✅ Montado |
# MAGIC | `avulso.py` | `/api/avulso` | 6 | ⚠️ Comentado |
# MAGIC | `operacao.py` | `/api/operacao` | 8 | ⚠️ Comentado |
# MAGIC | `admin.py` | `/api/admin` (MAB) | 7 | ⚠️ Comentado |
# MAGIC | **main.py** | `/health` | 1 | ✅ |
# MAGIC | **TOTAL** | | **65** (43 ativos + 22 prontos) | |
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## Índice
# MAGIC 1. [Campanhas (9)](#campanhas)
# MAGIC 2. [Peças (10)](#pecas)
# MAGIC 3. [Canais (5)](#canais)
# MAGIC 4. [Jornadas (11)](#jornadas)
# MAGIC 5. [Orquestrador (3)](#orquestrador)
# MAGIC 6. [Disparo (5)](#disparo)
# MAGIC 7. [Avulso (6)](#avulso)
# MAGIC 8. [Operação (8)](#operacao)
# MAGIC 9. [Admin MAB (7)](#admin-mab)
# MAGIC 10. [Matriz: Tabelas x Endpoints](#matriz)
# MAGIC 11. [Validação DDL vs Backend](#validacao)

# COMMAND ----------

# DBTITLE 1,1. Campanhas (9 endpoints)
# MAGIC %md
# MAGIC ## 1. Campanhas <a id="campanhas"></a>
# MAGIC
# MAGIC **Router:** `campanha.py` · **Prefix:** `/api/campanhas` · **Card:** S3-BACK-02
# MAGIC
# MAGIC | # | Método | Rota | Descrição | Tabelas Lê | Tabelas Escreve |
# MAGIC |---|--------|------|-----------|------------|----------------|
# MAGIC | 1 | GET | `/api/campanhas` | Lista paginada (filtro status/busca) | `campanha` | — |
# MAGIC | 2 | GET | `/api/campanhas/{id}` | Detalhe + jornadas vinculadas | `campanha`, `campanha_jornada`, `jornada` | — |
# MAGIC | 3 | POST | `/api/campanhas` | Criar campanha + v1 | — | `campanha`, `campanha_versao` |
# MAGIC | 4 | PUT | `/api/campanhas/{id}` | Editar (versiona snapshot) | `campanha` | `campanha`, `campanha_versao` |
# MAGIC | 5 | POST | `/api/campanhas/{id}/aprovar` | rascunho/em_aprovação → aprovada | `campanha` | `campanha`, `campanha_historico_estado` |
# MAGIC | 6 | POST | `/api/campanhas/{id}/ativar` | aprovada → ativa (valida peças) | `campanha`, `campanha_jornada`, `jornada`, `peca` | `campanha`, `campanha_historico_estado`, `eventos.disparo_eventos` |
# MAGIC | 7 | POST | `/api/campanhas/{id}/pausar` | ativa → pausada | `campanha` | `campanha`, `campanha_historico_estado`, `eventos.disparo_eventos` |
# MAGIC | 8 | POST | `/api/campanhas/{id}/encerrar` | ativa/pausada → encerrada | `campanha` | `campanha`, `campanha_historico_estado`, `eventos.disparo_eventos` |
# MAGIC | 9 | PUT | `/api/campanhas/{id}/limite` | Configura limite de envios | `campanha` | `campanha` |
# MAGIC
# MAGIC ### Campos por Operação
# MAGIC
# MAGIC **POST (criar):** `nome`, `descricao`, `objetivo`, `tags`, `resumo`, `objetivo_negocio`, `observacoes`, `owner`, `area_responsavel`, `email_contato`, `vigencia_inicio`, `vigencia_fim`, `limite_envios`, `alerta_pct_limite`
# MAGIC
# MAGIC **PUT (editar):** mesmos + gera `campanha_versao(campanha_id, versao, snapshot_json, alterado_por, alterado_em, motivo)`
# MAGIC
# MAGIC **Lifecycle (aprovar/ativar/pausar/encerrar):** sem body → gera `campanha_historico_estado(hist_id, campanha_id, estado_anterior, estado_novo, motivo, alterado_por, alterado_em)`

# COMMAND ----------

# DBTITLE 1,2. Peças (10 endpoints)
# MAGIC %md
# MAGIC ## 2. Peças <a id="pecas"></a>
# MAGIC
# MAGIC **Router:** `peca.py` · **Prefix:** `/api/pecas` · **Card:** S3-BACK-03
# MAGIC
# MAGIC | # | Método | Rota | Descrição | Tabelas Lê | Tabelas Escreve |
# MAGIC |---|--------|------|-----------|------------|----------------|
# MAGIC | 1 | GET | `/api/pecas/variaveis` | Catálogo de variáveis para personalização | `variaveis_disponiveis` (VIEW) | — |
# MAGIC | 2 | GET | `/api/pecas` | Lista paginada (filtro canal/status) | `peca` | — |
# MAGIC | 3 | GET | `/api/pecas/{id}` | Detalhe + versões | `peca`, `peca_versao` | — |
# MAGIC | 4 | POST | `/api/pecas` | Criar peça + v1 | — | `peca`, `peca_versao` |
# MAGIC | 5 | PUT | `/api/pecas/{id}` | Editar (versiona) | `peca` | `peca`, `peca_versao` |
# MAGIC | 6 | POST | `/api/pecas/{id}/aprovar` | Aprovar peça | `peca` | `peca`, `peca_aprovacao` |
# MAGIC | 7 | POST | `/api/pecas/{id}/reprovar` | Reprovar peça | `peca` | `peca`, `peca_aprovacao` |
# MAGIC | 8 | POST | `/api/pecas/{id}/preview` | Preview renderizado (HTML) | `peca` | — |
# MAGIC | 9 | GET | `/api/pecas/{id}/versoes` | Histórico de versões | `peca_versao` | — |
# MAGIC | 10 | POST | `/api/pecas/assets` | Upload de asset (imagem) | — | `asset` (+ Volume) |
# MAGIC
# MAGIC ### Campos Criados
# MAGIC
# MAGIC **POST (criar):** `nome`, `descricao`, `canal`, `tags`, `conteudo_json`, `html_renderizado`, `assunto`, `template_meta_id`, `variaveis_usadas`, `owner`, `area_responsavel`
# MAGIC
# MAGIC **Variáveis (contrato S1):** `campo_id`, `campo_label`, `tipo_dado`, `descricao` — via VIEW `variaveis_disponiveis` que lê `metadata.catalogo_caracteristicas`

# COMMAND ----------

# DBTITLE 1,3. Canais (5 endpoints)
# MAGIC %md
# MAGIC ## 3. Canais <a id="canais"></a>
# MAGIC
# MAGIC **Router:** `canal.py` · **Prefix:** `/api/canais` · **Card:** S3-BACK-04
# MAGIC
# MAGIC | # | Método | Rota | Descrição | Tabelas Lê | Tabelas Escreve |
# MAGIC |---|--------|------|-----------|------------|----------------|
# MAGIC | 1 | GET | `/api/canais/providers` | Lista providers Python registrados | (runtime) | — |
# MAGIC | 2 | GET | `/api/canais` | Lista canais (filtro ativo) | `catalogo_canais` | — |
# MAGIC | 3 | GET | `/api/canais/{id}` | Detalhe de um canal | `catalogo_canais` | — |
# MAGIC | 4 | POST | `/api/canais` | Criar canal (admin) | — | `catalogo_canais` |
# MAGIC | 5 | PUT | `/api/canais/{id}` | Editar canal (admin) | `catalogo_canais` | `catalogo_canais` |

# COMMAND ----------

# DBTITLE 1,4. Jornadas (11 endpoints)
# MAGIC %md
# MAGIC ## 4. Jornadas <a id="jornadas"></a>
# MAGIC
# MAGIC **Router:** `jornada.py` · **Prefix:** `/api/jornadas` · **Cards:** S3-BACK-05-A/B/C
# MAGIC
# MAGIC | # | Método | Rota | Descrição | Tabelas Lê | Tabelas Escreve |
# MAGIC |---|--------|------|-----------|------------|----------------|
# MAGIC | 1 | GET | `/api/jornadas` | Lista paginada (filtro campanha/status) | `jornada` | — |
# MAGIC | 2 | GET | `/api/jornadas/{id}` | Detalhe + grafo + versões | `jornada`, `jornada_versao` | — |
# MAGIC | 3 | POST | `/api/jornadas` | Criar + vincular campanha + v1 | `campanha` (valida existe) | `jornada`, `jornada_versao`, `campanha_jornada` |
# MAGIC | 4 | PUT | `/api/jornadas/{id}` | Editar + versionar (só rascunho) | `jornada` | `jornada`, `jornada_versao` |
# MAGIC | 5 | POST | `/api/jornadas/{id}/aprovar` | rascunho → aprovada (valida grafo) | `jornada` | `jornada` |
# MAGIC | 6 | POST | `/api/jornadas/{id}/ativar` | aprovada → ativa | `jornada`, `segmentacao.seg_definicao`, `segmentacao.seg_destino` | `jornada` |
# MAGIC | 7 | POST | `/api/jornadas/{id}/pausar` | ativa → pausada | `jornada` | `jornada` |
# MAGIC | 8 | POST | `/api/jornadas/{id}/encerrar` | ativa/pausada → encerrada | `jornada` | `jornada` |
# MAGIC | 9 | POST | `/api/jornadas/{id}/testar` | Simulação ou teste real | `jornada` | `jornada_teste` |
# MAGIC | 10 | GET | `/api/jornadas/{id}/participacao` | Histórico de participação | `jornada_participacao` | — |
# MAGIC | 11 | GET | `/api/jornadas/{id}/politica` | Política efetiva (global + override) | `config_jornada_politica`, `jornada` | — |
# MAGIC
# MAGIC ### Validação do Grafo (ativar)
# MAGIC - Usa `grafo_validator.validar_grafo(grafo_json)` → verifica: nó de entrada único, sem loops infinitos, todas arestas conectam nós existentes
# MAGIC - Usa `validar_segmento_ativo(seg_entrada_id)` → verifica seg ativa + com destino sistema3 no S1

# COMMAND ----------

# DBTITLE 1,5-6. Orquestrador + Disparo
# MAGIC %md
# MAGIC ## 5. Orquestrador <a id="orquestrador"></a>
# MAGIC
# MAGIC **Router:** `orquestrador.py` · **Prefix:** `/api/admin/orquestrador` · **Card:** S3-BACK-07
# MAGIC
# MAGIC | # | Método | Rota | Descrição | Tabelas Lê | Tabelas Escreve |
# MAGIC |---|--------|------|-----------|------------|----------------|
# MAGIC | 1 | POST | `/api/admin/orquestrador/executar` | Disparo manual do ciclo | `jornada`, `seg_resultado_corrente`, `jornada_estado_cliente`, `fila_disparo` | `fila_disparo`, `jornada_estado_cliente`, `supressao_log` |
# MAGIC | 2 | GET | `/api/admin/orquestrador/status` | Resumo operacional (fila + supressões) | `fila_disparo`, `supressao_log` | — |
# MAGIC | 3 | GET | `/api/admin/orquestrador/supressoes` | Supressões recentes (24h) | `supressao_log` | — |
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 6. Disparo <a id="disparo"></a>
# MAGIC
# MAGIC **Router:** `disparo.py` · **Prefix:** `/api/disparo` · **Card:** S3-BACK-08
# MAGIC
# MAGIC | # | Método | Rota | Descrição | Tabelas Lê | Tabelas Escreve |
# MAGIC |---|--------|------|-----------|------------|----------------|
# MAGIC | 1 | GET | `/api/disparo/fila` | Lista fila (filtro status/canal) | `fila_disparo` | — |
# MAGIC | 2 | POST | `/api/disparo/executar` | Executa motor de disparo manual | `fila_disparo`, `peca`, `catalogo_canais` | `fila_disparo`, `disparo_tentativa`, `tracking_disparo` |
# MAGIC | 3 | GET | `/api/disparo/stats` | Estatísticas (enviado/falha/pendente) | `fila_disparo`, `tracking_disparo` | — |
# MAGIC | 4 | GET | `/api/disparo/{fila_id}/tentativas` | Histórico de tentativas de um item | `disparo_tentativa` | — |
# MAGIC | 5 | POST | `/api/disparo/{fila_id}/reprocessar` | Reenfileira item com falha | `fila_disparo` | `fila_disparo` |

# COMMAND ----------

# DBTITLE 1,7-8-9. Avulso + Operação + Admin MAB
# MAGIC %md
# MAGIC ## 7. Avulso <a id="avulso"></a>
# MAGIC
# MAGIC **Router:** `avulso.py` · **Prefix:** `/api/avulso` · **Card:** S3-BACK-10 · **Status:** ⚠️ Comentado no main.py
# MAGIC
# MAGIC | # | Método | Rota | Descrição | Tabelas Lê | Tabelas Escreve |
# MAGIC |---|--------|------|-----------|------------|----------------|
# MAGIC | 1 | POST | `/api/avulso` | Criar DAV | — | `disparo_avulso` |
# MAGIC | 2 | GET | `/api/avulso` | Listar DAVs | `disparo_avulso` | — |
# MAGIC | 3 | GET | `/api/avulso/{id}` | Detalhe DAV | `disparo_avulso` | — |
# MAGIC | 4 | POST | `/api/avulso/{id}/aprovar` | Aprovar DAV | `disparo_avulso` | `disparo_avulso` |
# MAGIC | 5 | POST | `/api/avulso/{id}/executar` | Executar (governança + enfileira) | `disparo_avulso`, `seg_resultado_corrente`\*, `consentimento`\*, `regras_capping` | `fila_disparo`, `supressao_log`, `disparo_avulso` |
# MAGIC | 6 | DELETE | `/api/avulso/{id}` | Cancelar DAV | `disparo_avulso` | `disparo_avulso` |
# MAGIC
# MAGIC \* `seg_resultado_corrente` = `plataforma.segmentacao` (S1). `consentimento` = `plataforma.core_cliente`.
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 8. Operação <a id="operacao"></a>
# MAGIC
# MAGIC **Router:** `operacao.py` · **Prefix:** `/api/operacao` · **Card:** S3-BACK-12 · **Status:** ⚠️ Comentado
# MAGIC
# MAGIC | # | Método | Rota | Descrição | Tabelas Lê | Tabelas Escreve |
# MAGIC |---|--------|------|-----------|------------|----------------|
# MAGIC | 1 | GET | `/api/operacao/dashboard` | Métricas consolidadas | `fila_disparo`, `tracking_disparo`, `campanha` | — |
# MAGIC | 2 | GET | `/api/operacao/saude` | Status de saúde | `saude_operacional` | — |
# MAGIC | 3 | POST | `/api/operacao/saude/verificar` | Forçar verificação | `fila_disparo`, `tracking_disparo` | `saude_operacional` |
# MAGIC | 4 | GET | `/api/operacao/alertas` | Alertas/notificações | `notificacao` | — |
# MAGIC | 5 | POST | `/api/operacao/alertas/{id}/lida` | Marcar como lida | `notificacao` | `notificacao` |
# MAGIC | 6 | GET | `/api/operacao/fila/resumo` | Breakdown fila por status/canal | `fila_disparo` | — |
# MAGIC | 7 | GET | `/api/operacao/metricas/envios` | Métricas por dia/canal | `tracking_disparo` | — |
# MAGIC | 8 | POST | `/api/operacao/notificar` | Criar notificação manual | — | `notificacao` |
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 9. Admin MAB <a id="admin-mab"></a>
# MAGIC
# MAGIC **Router:** `admin.py` · **Prefix:** `/api/admin` · **Card:** S3-BACK-11 · **Status:** ⚠️ Comentado
# MAGIC
# MAGIC | # | Método | Rota | Descrição | Tabelas Lê | Tabelas Escreve |
# MAGIC |---|--------|------|-----------|------------|----------------|
# MAGIC | 1 | GET | `/api/admin/mab/variantes` | Variantes + resultados | `otimizacao_variante`, `otimizacao_resultado` | — |
# MAGIC | 2 | POST | `/api/admin/mab/recalcular` | Recalculo Thompson Sampling | `otimizacao_variante`, `otimizacao_resultado` | `otimizacao_variante`, `otimizacao_historico` |
# MAGIC | 3 | POST | `/api/admin/mab/pausar` | Pausar variante | `otimizacao_variante` | `otimizacao_variante`, `otimizacao_historico` |
# MAGIC | 4 | POST | `/api/admin/mab/fixar-vencedora` | Fixar vencedora | `otimizacao_variante` | `otimizacao_variante`, `otimizacao_historico` |
# MAGIC | 5 | GET | `/api/admin/mab/historico` | Histórico pesos | `otimizacao_historico` | — |
# MAGIC | 6 | GET | `/api/admin/mab/config` | Config otimização | `config_otimizacao` | — |
# MAGIC | 7 | PUT | `/api/admin/mab/config` | Atualizar config | `config_otimizacao` | `config_otimizacao` |

# COMMAND ----------

# DBTITLE 1,10. Matriz: Tabelas x Endpoints
# MAGIC %md
# MAGIC ## 10. Matriz: Tabelas x Endpoints <a id="matriz"></a>
# MAGIC
# MAGIC | Tabela | Campanha | Peça | Canal | Jornada | Orq. | Disparo | Avulso | Operação | MAB |
# MAGIC |--------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
# MAGIC | `campanha` | RW | — | — | R | — | — | — | R | — |
# MAGIC | `campanha_versao` | W | — | — | — | — | — | — | — | — |
# MAGIC | `campanha_historico_estado` | W | — | — | — | — | — | — | — | — |
# MAGIC | `campanha_jornada` | R | — | — | W | — | — | — | — | — |
# MAGIC | `campanha_prioridade` | — | — | — | — | R | — | — | — | — |
# MAGIC | `regras_capping` | — | — | — | — | R | — | R | — | — |
# MAGIC | `config_conversao` | — | — | — | — | — | — | — | — | — |
# MAGIC | `supressao_log` | — | — | — | — | RW | — | W | — | — |
# MAGIC | `catalogo_canais` | — | — | RW | — | — | R | — | — | — |
# MAGIC | `peca` | R | RW | — | — | — | R | — | — | — |
# MAGIC | `peca_versao` | — | RW | — | — | — | — | — | — | — |
# MAGIC | `peca_aprovacao` | — | W | — | — | — | — | — | — | — |
# MAGIC | `whatsapp_templates` | — | R | — | — | — | — | — | — | — |
# MAGIC | `asset` | — | W | — | — | — | — | — | — | — |
# MAGIC | `jornada` | R | — | — | RW | R | — | — | — | — |
# MAGIC | `jornada_versao` | — | — | — | RW | — | — | — | — | — |
# MAGIC | `jornada_estado_cliente` | — | — | — | — | RW | — | — | — | — |
# MAGIC | `jornada_participacao` | — | — | — | R | — | — | — | — | — |
# MAGIC | `jornada_log` | — | — | — | — | W | — | — | — | — |
# MAGIC | `jornada_teste` | — | — | — | W | — | — | — | — | — |
# MAGIC | `config_jornada_politica` | — | — | — | R | R | — | — | — | — |
# MAGIC | `fila_disparo` | — | — | — | — | RW | RW | W | R | — |
# MAGIC | `disparo_tentativa` | — | — | — | — | — | RW | — | — | — |
# MAGIC | `disparo_avulso` | — | — | — | — | — | — | RW | — | — |
# MAGIC | `config_janela_envio` | — | — | — | — | R | R | — | — | — |
# MAGIC | `config_retry` | — | — | — | — | — | R | — | — | — |
# MAGIC | `tracking_disparo` | — | — | — | — | — | W | — | R | R |
# MAGIC | `config_otimizacao` | — | — | — | — | — | — | — | — | RW |
# MAGIC | `otimizacao_variante` | — | — | — | — | — | — | — | — | RW |
# MAGIC | `otimizacao_resultado` | — | — | — | — | — | — | — | — | R |
# MAGIC | `otimizacao_historico` | — | — | — | — | — | — | — | — | RW |
# MAGIC | `saude_operacional` | — | — | — | — | — | — | — | RW | — |
# MAGIC | `notificacao` | — | — | — | — | — | — | — | RW | — |
# MAGIC | `eventos.disparo_eventos` | W | — | — | — | — | — | — | R | — |
# MAGIC | **VIEWs** | | | | | | | | | |
# MAGIC | `variaveis_disponiveis` | — | R | — | — | — | — | — | — | — |
# MAGIC | `segmento_campanha_map` | — | — | — | — | — | — | — | — | — |
# MAGIC | `cliente_jornada_status` | — | — | — | — | — | — | — | — | — |
# MAGIC
# MAGIC **Legenda:** R = Lê · W = Escreve · RW = Ambos
# MAGIC
# MAGIC ### Tabelas NUNCA tocadas pela API (Job-only ou contrato de saída)
# MAGIC
# MAGIC | Tabela | Quem gerencia | Motivo |
# MAGIC |--------|---------------|--------|
# MAGIC | `config_conversao` | Admin manual / futuro Job | Config waterfall de conversão |
# MAGIC | `segmento_campanha_map` (VIEW) | View materializada | Contrato de saída para S2 |
# MAGIC | `cliente_jornada_status` (VIEW) | View materializada | Contrato de saída para S2 |
# MAGIC | `jornada_estado_cliente` | Orquestrador core (não API direta) | Gerenciado por `core/orquestrador.py` interno |
# MAGIC | `jornada_log` | Orquestrador core | Audit trail de execução |

# COMMAND ----------

# DBTITLE 1,11. Validação DDL vs Backend
# MAGIC %md
# MAGIC ## 11. Validação DDL vs Backend <a id="validacao"></a>
# MAGIC
# MAGIC ### Resultado: ✅ Backend alinhado com DDL
# MAGIC
# MAGIC | Categoria | Qtd | Colunas | Status |
# MAGIC |-----------|-----|---------|--------|
# MAGIC | Tabelas usadas pela API | 33 | 337 | ✅ OK |
# MAGIC | Tabelas config/futuro (API não toca) | 1 | 7 | ⚠️ Esperado |
# MAGIC | Views (contratos saída S2) | 3 | — | ✅ OK |
# MAGIC | **Total DDL** | **34 + 3 views** | **344** | **✅** |
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### ✅ Tabelas 100% Cobertas pelo Backend (33/34)
# MAGIC
# MAGIC Todas as 33 tabelas são referenciadas por pelo menos um módulo:
# MAGIC - **9 tabelas** — CRUD direto pela API REST (campanha, peca, jornada, catalogo_canais, etc.)
# MAGIC - **10 tabelas** — Escritas pela API em operações de lifecycle/versionamento
# MAGIC - **9 tabelas** — Gerenciadas pelo core (orquestrador, motor_disparo, MAB)
# MAGIC - **5 tabelas** — Config lidas pelo core (capping, janela, retry, política, prioridade)
# MAGIC
# MAGIC ### ⚠️ Tabela Não Usada (1/34 — by design)
# MAGIC
# MAGIC | Tabela | Motivo | Quem vai gerenciar |
# MAGIC |--------|--------|--------------------|
# MAGIC | `config_conversao` | Config do waterfall de conversão | Futuro admin UI ou seed manual |
# MAGIC
# MAGIC ### 📊 Views de Contrato (3)
# MAGIC
# MAGIC | View | Consumidor | Usada pela API S3? |
# MAGIC |------|------------|--------------------|
# MAGIC | `variaveis_disponiveis` | `peca.py` (GET /pecas/variaveis) | ✅ Sim |
# MAGIC | `segmento_campanha_map` | S2 (ClientView 360) | ❌ Não (contrato de saída) |
# MAGIC | `cliente_jornada_status` | S2 (ClientView 360) | ❌ Não (contrato de saída) |
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### Comparação S1 vs S3
# MAGIC
# MAGIC | Dimensão | S1 (SegmentHub) | S3 (EngagementHub) |
# MAGIC |----------|-----------------|--------------------|
# MAGIC | Tabelas DDL | 16 | 34 + 3 views |
# MAGIC | Colunas totais | ~140 | 344 |
# MAGIC | Endpoints | 47 | 65 (43 ativos + 22 prontos) |
# MAGIC | Routers | 7 | 9 |
# MAGIC | Validação DDL↔Back | 16/16 ✅ | 33/34 ✅ (1 futuro) |
# MAGIC | Jobs | 2 notebooks | 7 planejados (pendente) |
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC *Gerado a partir de 11 DDLs + 9 routers API reais — Ago/2026*
