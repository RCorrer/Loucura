# Databricks notebook source
# DBTITLE 1,SegmentHub (S1) — Mapa Completo de Endpoints
# MAGIC %md
# MAGIC # SegmentHub (S1) — Mapa Completo de Endpoints
# MAGIC
# MAGIC > Referência técnica: cada endpoint com descrição, tabelas/campos que lê e escreve no banco, e contrato de entrada/saída para o frontend.
# MAGIC >
# MAGIC > **Base URL:** `/api` · **Catálogo:** `plataforma` · **Auth:** Header `X-Forwarded-Email`
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## Índice
# MAGIC 1. [Metadata (Catálogo Público)](#metadata)
# MAGIC 2. [Metadata Admin (Governança)](#metadata-admin)
# MAGIC 3. [Segmentações (CRUD)](#segmentacoes-crud)
# MAGIC 4. [Segmentações (Ciclo de Vida)](#segmentacoes-ciclo)
# MAGIC 5. [Segmentações (Versões/Histórico)](#segmentacoes-historico)
# MAGIC 6. [Segmentações (Destinos/Vigência)](#segmentacoes-destino)
# MAGIC 7. [Estimativa](#estimativa)
# MAGIC 8. [Comentários & Notificações](#comentarios)
# MAGIC 9. [Saúde](#saude)
# MAGIC 10. [Chat (IA)](#chat)
# MAGIC 11. [Utilitários](#utilitarios)

# COMMAND ----------

# DBTITLE 1,1. Metadata (Catálogo Público)
# MAGIC %md
# MAGIC ## 1. Metadata (Catálogo Público) <a id="metadata"></a>
# MAGIC
# MAGIC Endpoints de leitura do catálogo no-code. Alimentam o **Rule Builder** no frontend.
# MAGIC
# MAGIC | # | Método | Endpoint | Descrição | Tabelas Lê | Campos Lidos | Tabelas Escreve | Saída (Frontend) |
# MAGIC |---|--------|----------|-----------|------------|--------------|-----------------|------------------|
# MAGIC | 1 | GET | `/api/metadata/temas` | Lista temas disponíveis (menu lateral do builder) | `metadata.catalogo_caracteristicas` | `tema`, `tema_ordem` (DISTINCT) | — | `{data: [{tema, tema_ordem}], meta: {page, size, total}}` |
# MAGIC | 2 | GET | `/api/metadata/temas-completos` | Todos os temas + campos em 1 chamada (resolve N+1) | `metadata.catalogo_caracteristicas` | `tema`, `tema_ordem`, `caracteristica_id`, `campo_label`, `tipo_dado`, `operadores`, `sensibilidade` | — | `{data: [{tema, tema_ordem, campos: [...]}], meta}` |
# MAGIC | 3 | GET | `/api/metadata/temas/{tema}/caracteristicas` | Campos de um tema específico | `metadata.catalogo_caracteristicas` | `caracteristica_id`, `campo_label`, `tipo_dado`, `operadores`, `sensibilidade` (WHERE tema=? AND ativo=true) | — | `{data: [CaracteristicaDTO], meta}` |
# MAGIC | 4 | GET | `/api/metadata/caracteristicas/{id}` | Detalhe completo de 1 campo | `metadata.catalogo_caracteristicas` | ALL columns (WHERE caracteristica_id=? AND ativo=true) | — | `{data: CaracteristicaDetalheDTO}` |
# MAGIC | 5 | GET | `/api/metadata/publicos` | Públicos-base disponíveis | `metadata.catalogo_publicos` | `publico_id`, `nome`, `descricao`, `tabela_fisica`, `join_key` (WHERE ativo=true) | — | `{data: [PublicoDTO], meta}` |
# MAGIC | 6 | GET | `/api/metadata/caracteristicas-em-uso` | Campos referenciados por segs ativas | `metadata.campos_em_uso` (VIEW) | `campo_id`, `qtd_segmentacoes_ativas`, `segmentacoes` | — | `{data: [CaracteristicaEmUsoDTO], meta}` |
# MAGIC
# MAGIC **Nota:** Nenhum endpoint público expõe `usavel_em_peca`, `usavel_em_visao360`, `bloco_visao360` (só admin).

# COMMAND ----------

# DBTITLE 1,2. Metadata Admin (Governança de Catálogo)
# MAGIC %md
# MAGIC ## 2. Metadata Admin (Governança de Catálogo) <a id="metadata-admin"></a>
# MAGIC
# MAGIC Gerencia flags de integração com S2/S3. **Apenas perfil admin.**
# MAGIC
# MAGIC | # | Método | Endpoint | Descrição | Tabelas Lê | Campos Lidos | Tabelas Escreve | Campos Escritos | Entrada (Frontend) | Saída (Frontend) |
# MAGIC |---|--------|----------|-----------|------------|--------------|-----------------|-----------------|--------------------|-----------------|
# MAGIC | 7 | GET | `/api/metadata/admin/campos` | Lista TODAS características (incl. inativas) | `metadata.catalogo_caracteristicas` | ALL (sem filtro ativo) | — | — | Query: `?tema=&sistema=&status=&busca=&page=&size=` | `{data: [...], meta}` |
# MAGIC | 8 | GET | `/api/metadata/admin/campos/{id}` | Detalhe completo + flags S2/S3 | `metadata.catalogo_caracteristicas` | ALL columns (incl. `usavel_em_peca`, `usavel_em_visao360`, `bloco_visao360`) | — | — | — | `{data: {ALL fields}}` |
# MAGIC | 9 | PUT | `/api/metadata/admin/campos/{id}/flags` | Atualiza flags de integração | `metadata.catalogo_caracteristicas` | `caracteristica_id` (lookup) | `metadata.catalogo_caracteristicas` | `usavel_em_visao360`, `usavel_em_peca`, `bloco_visao360` | `{usavel_em_visao360?, usavel_em_peca?, bloco_visao360?, motivo}` | `{ok, alteracoes: [{flag, de, para}]}` |
# MAGIC | | | | Grava trilha de auditoria | — | — | `metadata.catalogo_governanca_hist` | `hist_id`, `caracteristica_id`, `campo_label`, `flag_alterada`, `sistema_alvo`, `valor_anterior`, `valor_novo`, `acao`, `alterado_por`, `alterado_em` | | |
# MAGIC | 10 | PUT | `/api/metadata/admin/campos/{id}/status` | Ativa/desativa globalmente | `metadata.catalogo_caracteristicas` | `caracteristica_id`, `ativo` | `metadata.catalogo_caracteristicas` | `ativo` | `{ativo: bool, motivo}` | `{ok, alteracoes}` |
# MAGIC | | | | Grava trilha de auditoria | — | — | `metadata.catalogo_governanca_hist` | (idem acima) | | |
# MAGIC | 11 | GET | `/api/metadata/admin/historico` | Histórico geral de governança | `metadata.catalogo_governanca_hist` | ALL (com filtros) | — | — | Query: `?caracteristica_id=&sistema_alvo=&acao=&alterado_por=&de=&ate=&page=&size=` | `{data: [...], meta}` |
# MAGIC | 12 | GET | `/api/metadata/admin/campos/{id}/historico` | Histórico de 1 característica | `metadata.catalogo_governanca_hist` | ALL (WHERE caracteristica_id=?) | — | — | Query: `?page=&size=` | `{data: [...], meta}` |

# COMMAND ----------

# DBTITLE 1,3. Segmentações — CRUD
# MAGIC %md
# MAGIC ## 3. Segmentações — CRUD <a id="segmentacoes-crud"></a>
# MAGIC
# MAGIC Operações básicas de criação, leitura, atualização e exclusão.
# MAGIC
# MAGIC | # | Método | Endpoint | Descrição | Tabelas Lê | Tabelas Escreve | Campos Escritos (principais) | Entrada (Frontend) | Saída (Frontend) |
# MAGIC |---|--------|----------|-----------|------------|-----------------|------------------------------|--------------------|-----------------|
# MAGIC | 13 | POST | `/api/segmentacoes` | Cria segmentação (rascunho) | `metadata.catalogo_publicos` (valida publico_base_id) | `segmentacao.seg_definicao` | `seg_id`, `seg_codigo`, `seg_slug`, `nome`, `descricao`, `objetivo`, `owner`, `publico_base_id`, `regras_json`, `status='rascunho'`, `criado_por`, `criado_em` | `SegmentacaoCreateDTO {nome, descricao?, objetivo, publico_base_id, regras_json, owner?, area_responsavel?}` | `{seg_id, seg_codigo, mensagem}` |
# MAGIC | | | | Cria versão 1 | — | `segmentacao.seg_versao` | `versao_id`, `seg_id`, `versao=1`, `regras_json`, `alterado_por`, `alterado_em` | | |
# MAGIC | | | | Grava histórico estado | — | `segmentacao.seg_historico_estado` | `hist_id`, `seg_id`, `estado_anterior=null`, `estado_novo='rascunho'`, `alterado_por` | | |
# MAGIC | 14 | GET | `/api/segmentacoes` | Lista com filtros e paginação | `segmentacao.seg_definicao` | — | — | Query: `?status=&objetivo=&owner=&busca=&page=&size=` | `{data: [SegmentacaoResponseDTO], meta: {page, size, total, total_pages}}` |
# MAGIC | 15 | GET | `/api/segmentacoes/{seg_id}` | Detalhe completo | `segmentacao.seg_definicao` | — | — | — | `SegmentacaoDetalheDTO {seg_id, seg_codigo, nome, ..., regras_json, status, ...}` |
# MAGIC | 16 | PUT | `/api/segmentacoes/{seg_id}` | Atualiza. Se ativa → cria nova versão | `segmentacao.seg_definicao` | `segmentacao.seg_definicao` | campos alterados + `atualizado_em`, `versao_atual++` | `SegmentacaoUpdateDTO {nome?, descricao?, objetivo?, regras_json?, ...}` | `{mensagem}` |
# MAGIC | | | | Se regras mudaram | — | `segmentacao.seg_versao` | nova versão com regras atualizadas | | |
# MAGIC | 17 | DELETE | `/api/segmentacoes/{seg_id}` | Arquiva (soft delete) | `segmentacao.seg_definicao` | `segmentacao.seg_definicao` | `status='arquivada'` | — | `{mensagem}` |
# MAGIC | | | | Grava histórico | — | `segmentacao.seg_historico_estado` | transição → arquivada | | |
# MAGIC | | | | Deleta Job | — | `segmentacao.seg_job_log` | log de ação 'deletar' | | |
# MAGIC | 18 | POST | `/api/segmentacoes/{seg_id}/clonar` | Clona segmentação existente | `segmentacao.seg_definicao` (lê original) | `segmentacao.seg_definicao` | novo `seg_id`, `seg_codigo`, `tipo_origem='clone'`, `seg_origem_id` | `CloneSegmentacaoDTO {novo_nome?, novo_owner?}` | `{seg_id, seg_codigo, mensagem}` |
# MAGIC | | | | Cria versão 1 do clone | — | `segmentacao.seg_versao` | versão 1 com regras copiadas | | |

# COMMAND ----------

# DBTITLE 1,4. Segmentações — Ciclo de Vida
# MAGIC %md
# MAGIC ## 4. Segmentações — Ciclo de Vida <a id="segmentacoes-ciclo"></a>
# MAGIC
# MAGIC Transições de status + execução manual.
# MAGIC
# MAGIC | # | Método | Endpoint | Descrição | Tabelas Lê | Tabelas Escreve | Campos Escritos (principais) | Entrada | Saída |
# MAGIC |---|--------|----------|-----------|------------|-----------------|------------------------------|---------|------|
# MAGIC | 19 | POST | `/{seg_id}/validar` | Validação completa (regras + catalogo + estimativa) | `segmentacao.seg_definicao`, `metadata.catalogo_caracteristicas`, `metadata.catalogo_publicos` | — | — | — | `{valido: bool, erros?: [...], resumo?: {regras, estimativa}}` |
# MAGIC | 20 | POST | `/{seg_id}/enviar-aprovacao` | Envia para aprovação | `segmentacao.seg_definicao` | `segmentacao.seg_definicao` | `status='em_aprovacao'` | — | `{mensagem}` |
# MAGIC | | | | | | `segmentacao.seg_historico_estado` | transição rascunho → em_aprovacao | | |
# MAGIC | 21 | POST | `/{seg_id}/aprovar` | Aprova (só admin). Cria Job + evento | `segmentacao.seg_definicao` | `segmentacao.seg_definicao` | `status='aprovada'`, `aprovado_por`, `aprovado_em`, `checklist_validacao_json` | `{checklist: {...}}` | `{mensagem}` |
# MAGIC | | | | Cria Databricks Job | — | `segmentacao.seg_definicao` | `job_id_databricks` | | |
# MAGIC | | | | Log do Job Manager | — | `segmentacao.seg_job_log` | log acao='criar' | | |
# MAGIC | | | | Emite evento | — | `eventos.seg_eventos` | `evento_id`, `seg_id`, tipo='aprovada' | | |
# MAGIC | | | | Grava histórico | — | `segmentacao.seg_historico_estado` | transição → aprovada | | |
# MAGIC | 22 | POST | `/{seg_id}/ativar` | Ativa segmentação aprovada | `segmentacao.seg_definicao` | `segmentacao.seg_definicao` | `status='ativa'` | — | `{mensagem}` |
# MAGIC | | | | | — | `segmentacao.seg_historico_estado` | transição → ativa | | |
# MAGIC | 23 | POST | `/{seg_id}/pausar` | Pausa (remove schedule do Job) | `segmentacao.seg_definicao` | `segmentacao.seg_definicao` | `status='pausada'` | — | `{mensagem}` |
# MAGIC | | | | | — | `segmentacao.seg_job_log` | log acao='pausar' | | |
# MAGIC | | | | | — | `segmentacao.seg_historico_estado` | transição → pausada | | |
# MAGIC | 24 | POST | `/{seg_id}/reativar` | Reativa (restaura schedule) | `segmentacao.seg_definicao` | `segmentacao.seg_definicao` | `status='ativa'` | — | `{mensagem}` |
# MAGIC | | | | | — | `segmentacao.seg_job_log` | log acao='reativar' | | |
# MAGIC | | | | | — | `segmentacao.seg_historico_estado` | transição → ativa | | |
# MAGIC | 25 | POST | `/{seg_id}/encerrar` | Encerra definitivamente (deleta Job) | `segmentacao.seg_definicao` | `segmentacao.seg_definicao` | `status='encerrada'` | — | `{mensagem}` |
# MAGIC | | | | | — | `segmentacao.seg_job_log` | log acao='deletar' | | |
# MAGIC | | | | Emite evento | — | `eventos.seg_eventos` | tipo='encerrada' | | |
# MAGIC | | | | | — | `segmentacao.seg_historico_estado` | transição → encerrada | | |
# MAGIC | 26 | POST | `/{seg_id}/executar` | Execução manual (dispara Job run) | `segmentacao.seg_definicao` | `segmentacao.seg_execucao` | `exec_id`, `seg_id`, `versao_usada`, `origem_execucao='manual'`, `status='rodando'`, `job_id`, `run_id` | — | `{exec_id, run_id, job_id, mensagem}` |
# MAGIC | | | | | — | `segmentacao.seg_job_log` | log acao='executar' | | |
# MAGIC | | | | Emite evento | — | `eventos.seg_eventos` | tipo='executada' | | |
# MAGIC
# MAGIC **Nota:** Cada transição valida a máquina de estados. Transições inválidas retornam 422.

# COMMAND ----------

# DBTITLE 1,5. Segmentações — Versões e Histórico
# MAGIC %md
# MAGIC ## 5. Segmentações — Versões e Histórico <a id="segmentacoes-historico"></a>
# MAGIC
# MAGIC Consultas de auditoria e versionamento.
# MAGIC
# MAGIC | # | Método | Endpoint | Descrição | Tabelas Lê | Campos Lidos | Escreve | Saída |
# MAGIC |---|--------|----------|-----------|------------|--------------|---------|------|
# MAGIC | 27 | GET | `/{seg_id}/versoes` | Lista versões de regras | `segmentacao.seg_versao` | `versao_id`, `versao`, `motivo`, `alterado_por`, `alterado_em` (WHERE seg_id=?) | — | `[{versao_id, versao, motivo, alterado_por, alterado_em}]` |
# MAGIC | 28 | GET | `/{seg_id}/versoes/{versao}` | Regras de uma versão específica | `segmentacao.seg_versao` | ALL (WHERE seg_id=? AND versao=?) | — | `{versao_id, seg_id, versao, regras_json, motivo, alterado_por, alterado_em}` |
# MAGIC | 29 | GET | `/{seg_id}/execucoes` | Histórico de execuções | `segmentacao.seg_execucao` | `exec_id`, `versao_usada`, `origem_execucao`, `executado_em`, `qtd_clientes`, `status`, `job_run_url` | — | `[{exec_id, versao_usada, qtd_clientes, status, executado_em, ...}]` |
# MAGIC | 30 | GET | `/{seg_id}/estados` | Histórico de transições de status | `segmentacao.seg_historico_estado` | ALL (WHERE seg_id=? ORDER BY alterado_em DESC) | — | `[{hist_id, estado_anterior, estado_novo, motivo, alterado_por, alterado_em}]` |
# MAGIC | 31 | GET | `/{seg_id}/timeline` | Timeline unificada (versões + execuções + estados) | `seg_versao` + `seg_execucao` + `seg_historico_estado` | Merge por data | — | `[{tipo: 'versao'\|'execucao'\|'estado', data, ...details}]` |

# COMMAND ----------

# DBTITLE 1,6. Segmentações — Destinos e Vigência
# MAGIC %md
# MAGIC ## 6. Segmentações — Destinos e Vigência <a id="segmentacoes-destino"></a>
# MAGIC
# MAGIC Configuração de natureza (humano/digital) e agendamento.
# MAGIC
# MAGIC | # | Método | Endpoint | Descrição | Tabelas Lê | Tabelas Escreve | Campos Escritos | Entrada | Saída |
# MAGIC |---|--------|----------|-----------|------------|-----------------|-----------------|---------|------|
# MAGIC | 32 | GET | `/{seg_id}/destinos` | Destinos configurados | `segmentacao.seg_destino` | — | — | — | `[{seg_id, destino, habilitado, criado_em}]` |
# MAGIC | 33 | PUT | `/{seg_id}/destinos` | Atualiza destinos | `segmentacao.seg_destino` | `segmentacao.seg_destino` | MERGE: `seg_id`, `destino` (sistema2/sistema3), `habilitado`, `criado_em` | `[{destino: 'sistema2'\|'sistema3', habilitado: bool}]` | `{mensagem}` |
# MAGIC | 34 | PUT | `/{seg_id}/vigencia` | Atualiza vigência e cron | `segmentacao.seg_definicao` | `segmentacao.seg_definicao` | `vigencia_inicio`, `vigencia_fim`, `agendamento_cron`, `recorrencia` | `{vigencia_inicio?, vigencia_fim?, agendamento_cron?, recorrencia?}` | `{mensagem}` |
# MAGIC | | | | Atualiza schedule do Job | — | `segmentacao.seg_job_log` | log acao='atualizar_schedule' | | |

# COMMAND ----------

# DBTITLE 1,7. Estimativa
# MAGIC %md
# MAGIC ## 7. Estimativa <a id="estimativa"></a>
# MAGIC
# MAGIC Cálculo de tamanho do público em tempo real (sem salvar).
# MAGIC
# MAGIC | # | Método | Endpoint | Descrição | Tabelas Lê | Campos Lidos | Escreve | Entrada | Saída |
# MAGIC |---|--------|----------|-----------|------------|--------------|---------|---------|------|
# MAGIC | 35 | POST | `/api/estimativa/preview` | Calcula estimativa via HyperLogLog | `metadata.catalogo_caracteristicas` (resolve campo_fisico/tabela_fisica), `metadata.catalogo_publicos` (resolve tabela do público), `caracteristicas.customer_features_wide` (dados reais), `publico.pub_*` (público-base) | `cpf_cnpj` (approx_count_distinct) + campos das regras | — | `RegrasJson {publico_base, inclusao: {operator, rules: [{campo_id, op, value}]}, exclusao?}` | `{estimativa: int, inclusao: int, exclusao: int, tempo_ms: int}` |
# MAGIC
# MAGIC **Segurança:** Nunca retorna lista de CPFs. Apenas contagem aproximada.

# COMMAND ----------

# DBTITLE 1,8. Comentários & Notificações
# MAGIC %md
# MAGIC ## 8. Comentários & Notificações <a id="comentarios"></a>
# MAGIC
# MAGIC Colaboração em threads + notificações in-app.
# MAGIC
# MAGIC | # | Método | Endpoint | Descrição | Tabelas Lê | Tabelas Escreve | Campos Escritos | Entrada | Saída |
# MAGIC |---|--------|----------|-----------|------------|-----------------|-----------------|---------|------|
# MAGIC | 36 | GET | `/api/segmentacoes/{seg_id}/comentarios` | Thread aninhada | `segmentacao.seg_comentario` | — | — | — | `[{comentario_id, autor, texto, tipo, versao_referencia, respondendo_a, mencoes, resolvido, criado_em, editado_em, respostas: [...]}]` |
# MAGIC | 37 | POST | `/api/segmentacoes/{seg_id}/comentarios` | Cria comentário. Menções (@user) geram notificação | `segmentacao.seg_comentario` (valida respondendo_a) | `segmentacao.seg_comentario` | `comentario_id`, `seg_id`, `autor`, `texto`, `tipo`, `versao_referencia`, `respondendo_a`, `mencoes`, `criado_em` | `{texto, tipo?, versao_referencia?, respondendo_a?, mencoes?: []}` | `{comentario_id, mensagem}` |
# MAGIC | | | | Gera notificações para mencionados | — | `segmentacao.seg_notificacao` | `notif_id`, `destinatario`, `tipo='mencao'`, `seg_id`, `titulo`, `mensagem`, `lida=false`, `criado_em` | | |
# MAGIC | 38 | PUT | `/api/comentarios/{comentario_id}` | Edita texto ou marca resolvido | `segmentacao.seg_comentario` | `segmentacao.seg_comentario` | `texto`?, `resolvido`?, `editado_em` | `{texto?, resolvido?}` | `{mensagem}` |
# MAGIC | 39 | GET | `/api/notificacoes` | Notificações do usuário logado | `segmentacao.seg_notificacao` | — | — | Query: `?lida=true\|false` | `[{notif_id, tipo, seg_id, titulo, mensagem, lida, criado_em}]` |
# MAGIC | 40 | PUT | `/api/notificacoes/{notif_id}/lida` | Marca como lida | `segmentacao.seg_notificacao` | `segmentacao.seg_notificacao` | `lida=true` | — | `{mensagem}` |

# COMMAND ----------

# DBTITLE 1,9. Saúde
# MAGIC %md
# MAGIC ## 9. Saúde <a id="saude"></a>
# MAGIC
# MAGIC Monitoramento de health das segmentações (populado por Job de saúde).
# MAGIC
# MAGIC | # | Método | Endpoint | Descrição | Tabelas Lê | Campos Lidos | Escreve | Saída |
# MAGIC |---|--------|----------|-----------|------------|--------------|---------|------|
# MAGIC | 41 | GET | `/api/saude` | Dashboard consolidado | `segmentacao.seg_saude` + `segmentacao.seg_definicao` | `seg_id`, `health_status`, `variacao_publico_pct`, `taxa_sucesso_exec`, `publico_atual` (JOIN com nome/status da seg) | — | `{resumo: {total, verde, amarelo, vermelho}, segmentacoes: [{seg_id, nome, health_status, ...}]}` |
# MAGIC | 42 | GET | `/api/saude/{seg_id}` | Saúde detalhada + alertas | `segmentacao.seg_saude` + `segmentacao.seg_execucao` (histórico recente) | ALL de seg_saude + últimas N execuções | — | `{seg_id, health_status, variacao_publico_pct, taxa_sucesso_exec, tempo_medio_exec_seg, alertas_json, publico_atual, ultima_verificacao, historico_execucoes: [...]}` |

# COMMAND ----------

# DBTITLE 1,10. Chat (IA)
# MAGIC %md
# MAGIC ## 10. Chat (IA) <a id="chat"></a>
# MAGIC
# MAGIC Chatbot que converte linguagem natural em regras de segmentação.
# MAGIC
# MAGIC | # | Método | Endpoint | Descrição | Tabelas Lê | Campos Lidos | Escreve | Entrada | Saída |
# MAGIC |---|--------|----------|-----------|------------|--------------|---------|---------|------|
# MAGIC | 43 | POST | `/api/chat/mensagem` | Processa mensagem do usuário | `metadata.catalogo_caracteristicas` (contexto para LLM), `metadata.catalogo_publicos` (públicos disponíveis) | `campo_label`, `tipo_dado`, `operadores`, `valores_dominio`, `tema` | — | `{mensagem: str, session_id?: str, historico?: [{role, content}]}` | `{resposta: str, regras_json?: RegrasJson, acao?: 'abrir_builder'\|'refinar'\|null, precisa_confirmacao: bool, session_id: str}` |
# MAGIC
# MAGIC **LLM:** `databricks-claude-sonnet-4-6` via Databricks Model Serving. 
# MAGIC **Segurança:** Nunca executa SQL diretamente. Apenas sugere regras_json para o builder.

# COMMAND ----------

# DBTITLE 1,11. Utilitários
# MAGIC %md
# MAGIC ## 11. Utilitários <a id="utilitarios"></a>
# MAGIC
# MAGIC Endpoints de infraestrutura (sem auth para health).
# MAGIC
# MAGIC | # | Método | Endpoint | Descrição | Auth | Tabelas | Saída |
# MAGIC |---|--------|----------|-----------|------|---------|------|
# MAGIC | 44 | GET | `/health` | Health check | Não | — | `{status: 'ok', timestamp}` |
# MAGIC | 45 | GET | `/api/me` | Usuário autenticado (debug) | Sim | `governanca.usuarios_perfil` | `{usuario_id, nome, sistema, perfil, ativo}` |
# MAGIC | 46 | GET | `/api/debug-headers` | Visualiza headers (debug) | Sim | — | `{headers: {...}}` |
# MAGIC | 47 | GET | `/api/test-db` | Testa conexão Databricks SQL | Sim | (SELECT 1) | `{connected: bool, latency_ms}` |

# COMMAND ----------

# DBTITLE 1,Resumo: Tabelas x Endpoints (Matriz)
# MAGIC %md
# MAGIC ## Resumo: Tabelas x Endpoints (Matriz)
# MAGIC
# MAGIC | Tabela | Lê (endpoints) | Escreve (endpoints) |
# MAGIC |--------|----------------|---------------------|
# MAGIC | `metadata.catalogo_caracteristicas` | #1-6, #7-8, #19, #35, #43 | #9, #10 |
# MAGIC | `metadata.catalogo_publicos` | #5, #13, #19, #35, #43 | — |
# MAGIC | `metadata.catalogo_governanca_hist` | #11, #12 | #9, #10 |
# MAGIC | `metadata.campos_em_uso` (VIEW) | #6 | — (view lê seg_definicao) |
# MAGIC | `segmentacao.seg_definicao` | #14, #15, #16, #17-26, #29-31, #41 | #13, #16, #17, #20-26 |
# MAGIC | `segmentacao.seg_execucao` | #29, #31, #42 | #26 |
# MAGIC | `segmentacao.seg_resultado_corrente` | (via Job, não API) | (via Job, não API) |
# MAGIC | `segmentacao.seg_resultado_historico` | (via Job, não API) | (via Job, não API) |
# MAGIC | `segmentacao.seg_versao` | #27, #28, #31 | #13, #16, #18 |
# MAGIC | `segmentacao.seg_historico_estado` | #30, #31 | #13, #17, #20-26 |
# MAGIC | `segmentacao.seg_destino` | #32 | #33 |
# MAGIC | `segmentacao.seg_comentario` | #36, #37 | #37, #38 |
# MAGIC | `segmentacao.seg_notificacao` | #39 | #37, #40 |
# MAGIC | `segmentacao.seg_saude` | #41, #42 | (via Job saúde) |
# MAGIC | `segmentacao.seg_job_log` | — | #17, #21, #23-26, #34 |
# MAGIC | `eventos.seg_eventos` | — | #21, #25, #26 |
# MAGIC | `governanca.usuarios_perfil` | #45 (auth em todos) | — |
# MAGIC | `caracteristicas.customer_features_wide` | #35 (estimativa) | — |
# MAGIC | `publico.pub_*` | #35 (estimativa) | — |
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC **Total: 47 endpoints** (6 metadata + 6 admin + 6 CRUD + 8 ciclo + 5 histórico + 3 destino + 1 estimativa + 5 colab + 2 saúde + 1 chat + 4 utils)
# MAGIC
# MAGIC ---
# MAGIC *Gerado a partir dos routers reais em `/segmenthub/src/api/` — Ago/2026*
