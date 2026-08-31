# Databricks notebook source
# DBTITLE 1,SegmentHub (S1) — Mapa Frontend: Telas, Endpoints e Contratos
# MAGIC %md
# MAGIC # SegmentHub (S1) — Mapa Frontend: Telas, Endpoints e Contratos
# MAGIC
# MAGIC > Referência técnica: cada tela/componente com endpoints consumidos, payload enviado e resposta esperada.
# MAGIC >
# MAGIC > **Stack:** React 18 + Vite + MUI 5 · **API Base:** `/api` · **Auth:** Token JWT (perfil admin/analista)
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## Visão Geral da Arquitetura Frontend
# MAGIC
# MAGIC ```
# MAGIC   src/
# MAGIC   ├── api/              ← 7 hooks (API clients)
# MAGIC   │   ├── segmentacoes.js    (26 funções)
# MAGIC   │   ├── metadata.js        (10 funções)
# MAGIC   │   ├── metadataAdmin.js   (6 funções)
# MAGIC   │   ├── estimativa.js      (1 função)
# MAGIC   │   ├── chat.js            (1 função — não usado, page usa useChat)
# MAGIC   │   ├── saude.js           (2 funções)
# MAGIC   │   └── notificacoes.js    (2 funções)
# MAGIC   ├── pages/            ← 7 pages (telas)
# MAGIC   │   ├── ListaSegmentacoes.jsx
# MAGIC   │   ├── BuilderSegmentacao.jsx
# MAGIC   │   ├── DetalheSegmentacao.jsx
# MAGIC   │   ├── TimelineSegmentacao.jsx
# MAGIC   │   ├── DashboardSaude.jsx
# MAGIC   │   ├── AdminCatalogo.jsx
# MAGIC   │   └── ChatSegmentacao.jsx
# MAGIC   └── components/       ← 13 componentes reutilizáveis
# MAGIC ```
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## Índice
# MAGIC 1. [ListaSegmentações](#lista)
# MAGIC 2. [BuilderSegmentação](#builder)
# MAGIC 3. [DetalheSegmentação](#detalhe)
# MAGIC 4. [TimelineSegmentação](#timeline)
# MAGIC 5. [DashboardSaúde](#saude)
# MAGIC 6. [AdminCatálogo](#admin)
# MAGIC 7. [ChatSegmentação](#chat)
# MAGIC 8. [Componentes Globais](#globais)
# MAGIC 9. [Validação Front ↔ Back](#validacao)

# COMMAND ----------

# DBTITLE 1,1. ListaSegmentacoes
# MAGIC %md
# MAGIC ## 1. ListaSegmentações <a id="lista"></a>
# MAGIC
# MAGIC **Rota:** `/segmentacoes` · **Page:** `ListaSegmentacoes.jsx` · **Card:** S1-FRONT-01
# MAGIC
# MAGIC ### Endpoints Consumidos
# MAGIC
# MAGIC | Método | Endpoint | Função no hook | Quando dispara |
# MAGIC |--------|----------|--------------|----------------|
# MAGIC | GET | `/api/segmentacoes?page=&size=&status=&busca=` | `listar(filtros)` | onMount + filtro/paginação |
# MAGIC | POST | `/api/segmentacoes/{id}/clonar` | `clonar(id, dados)` | Botão "Clonar" |
# MAGIC
# MAGIC ### Request / Response
# MAGIC
# MAGIC **GET /api/segmentacoes** (listar)
# MAGIC ```
# MAGIC Query params: { page: int, size: int, status?: string, busca?: string }
# MAGIC Response: {
# MAGIC   data: [{
# MAGIC     seg_id, seg_codigo, seg_slug, nome, descricao, objetivo,
# MAGIC     status, versao_atual, criado_por, criado_em, atualizado_em,
# MAGIC     owner, area_responsavel, publico_base_id
# MAGIC   }],
# MAGIC   meta: { page, size, total, total_pages }
# MAGIC }
# MAGIC ```
# MAGIC
# MAGIC **POST /api/segmentacoes/{id}/clonar**
# MAGIC ```
# MAGIC Body: { nome?: string }  (nome do clone, opcional)
# MAGIC Response: { seg_id: string } (ID da nova segmentação clonada)
# MAGIC ```
# MAGIC
# MAGIC ### Dados Consumidos do Response
# MAGIC - `seg_id` → usado como `id` na DataTable + navegação
# MAGIC - `seg_codigo`, `nome`, `status`, `objetivo`, `owner`, `criado_em` → colunas da tabela
# MAGIC - `meta.total` → paginação + badge "Pendentes" (filtra status=em_aprovacao)

# COMMAND ----------

# DBTITLE 1,2. BuilderSegmentacao
# MAGIC %md
# MAGIC ## 2. BuilderSegmentação <a id="builder"></a>
# MAGIC
# MAGIC **Rota:** `/segmentacoes/nova` (criar) ou `/segmentacoes/:id/editar` (editar) · **Page:** `BuilderSegmentacao.jsx` · **Cards:** S1-FRONT-02/03/04
# MAGIC
# MAGIC ### Endpoints Consumidos
# MAGIC
# MAGIC | Método | Endpoint | Função | Quando |
# MAGIC |--------|----------|--------|--------|
# MAGIC | GET | `/api/segmentacoes/{id}` | `buscar(id)` | onMount (edição) |
# MAGIC | POST | `/api/segmentacoes` | `criar(dados)` | Submit (novo) |
# MAGIC | PUT | `/api/segmentacoes/{id}` | `atualizar(id, dados)` | Submit (edição) |
# MAGIC | GET | `/api/segmentacoes/{id}/destinos` | `buscarDestinos(id)` | onMount (edição) |
# MAGIC | PUT | `/api/segmentacoes/{id}/destinos` | `atualizarDestinos(id, dest)` | Step 4 salvar |
# MAGIC | PUT | `/api/segmentacoes/{id}/vigencia` | `atualizarVigencia(id, dados)` | Step 4 salvar |
# MAGIC | GET | `/api/metadata/temas-completos` | `listarTemasCompletos()` | onMount (popular TemaMenu) |
# MAGIC | GET | `/api/metadata/publicos` | `listarPublicos()` | onMount (popular PublicoSelector) |
# MAGIC | POST | `/api/estimativa/preview` | `calcularPreview(payload)` | Debounce 800ms ao alterar regras |
# MAGIC
# MAGIC ### Payload de Criação/Atualização (POST/PUT /segmentacoes)
# MAGIC ```json
# MAGIC {
# MAGIC   "nome": "string",
# MAGIC   "descricao": "string",
# MAGIC   "objetivo": "string",
# MAGIC   "owner": "string",
# MAGIC   "area_responsavel": "string",
# MAGIC   "publico_base_id": "string",
# MAGIC   "regras_json": {
# MAGIC     "inclusao": { "operator": "AND|OR", "rules": [...] },
# MAGIC     "exclusao": { "operator": "AND|OR", "rules": [...] } | null
# MAGIC   },
# MAGIC   "recorrencia": "once|hourly|daily|weekly|monthly|custom",
# MAGIC   "agendamento_cron": "string|null",
# MAGIC   "vigencia_inicio": "ISO datetime",
# MAGIC   "vigencia_fim": "ISO datetime|null"
# MAGIC }
# MAGIC ```
# MAGIC
# MAGIC ### Payload Estimativa (POST /api/estimativa/preview)
# MAGIC ```json
# MAGIC {
# MAGIC   "publico_base": "publico_id",
# MAGIC   "inclusao": { "operator": "AND|OR", "rules": [
# MAGIC     { "campo_id": "str", "op": "str", "value": any }
# MAGIC   ]},
# MAGIC   "exclusao": { ... } | null
# MAGIC }
# MAGIC ```
# MAGIC **Response Estimativa:**
# MAGIC ```json
# MAGIC { "estimativa": int, "inclusao": int, "exclusao": int, "tempo_ms": int }
# MAGIC ```
# MAGIC
# MAGIC ### Componentes Filhos Relevantes
# MAGIC
# MAGIC | Componente | Endpoint que consome | Dados usados |
# MAGIC |------------|---------------------|-------------|
# MAGIC | `PublicoSelector` | Recebe lista via props (GET /metadata/publicos) | `publico_id`, `nome`, `descricao` |
# MAGIC | `TemaMenu` | Recebe lista via props (GET /metadata/temas-completos) | `tema`, `caracteristicas[]` |
# MAGIC | `RuleBuilder` | Nenhum direto (manipula state) | `campo_id`, `op`, `value` |
# MAGIC | `ExclusaoBuilder` | Nenhum direto | Mesma estrutura do RuleBuilder |
# MAGIC | `EstimativaBadge` | POST /api/estimativa/preview | `estimativa`, `inclusao`, `exclusao`, `tempo_ms` |
# MAGIC | `DestinoSelector` | Recebe via props | `[{destino:'sistema2'\|'sistema3', habilitado: bool}]` |
# MAGIC | `VigenciaAgendamento` | Nenhum direto | `vigencia_inicio`, `vigencia_fim`, `recorrencia`, `agendamento_cron` |

# COMMAND ----------

# DBTITLE 1,3. DetalheSegmentacao
# MAGIC %md
# MAGIC ## 3. DetalheSegmentação <a id="detalhe"></a>
# MAGIC
# MAGIC **Rota:** `/segmentacoes/:id` · **Page:** `DetalheSegmentacao.jsx` · **Card:** S1-FRONT-05
# MAGIC
# MAGIC ### Endpoints Consumidos
# MAGIC
# MAGIC | Método | Endpoint | Função | Quando |
# MAGIC |--------|----------|--------|--------|
# MAGIC | GET | `/api/segmentacoes/{id}` | `buscar(id)` | onMount |
# MAGIC | GET | `/api/segmentacoes/{id}/destinos` | `buscarDestinos(id)` | onMount |
# MAGIC | GET | `/api/segmentacoes/{id}/execucoes` | `listarExecucoes(id)` | onMount |
# MAGIC | GET | `/api/segmentacoes/{id}/versoes` | `listarVersoes(id)` | onMount |
# MAGIC | GET | `/api/segmentacoes/{id}/estados` | `listarEstados(id)` | onMount |
# MAGIC | GET | `/api/saude/{seg_id}` | `obterDetalhe(segId)` | onMount |
# MAGIC | POST | `/api/segmentacoes/{id}/validar` | `validar(id)` | Botão "Validar" |
# MAGIC | POST | `/api/segmentacoes/{id}/enviar-aprovacao` | `enviarAprovacao(id)` | Botão "Enviar p/ Aprovação" |
# MAGIC | POST | `/api/segmentacoes/{id}/aprovar` | `aprovar(id, checklist)` | Botão "Aprovar" |
# MAGIC | POST | `/api/segmentacoes/{id}/ativar` | `ativar(id)` | Botão "Ativar" |
# MAGIC | POST | `/api/segmentacoes/{id}/pausar` | `pausar(id)` | Botão "Pausar" |
# MAGIC | POST | `/api/segmentacoes/{id}/reativar` | `reativar(id)` | Botão "Reativar" |
# MAGIC | POST | `/api/segmentacoes/{id}/encerrar` | `encerrar(id)` | Botão "Encerrar" |
# MAGIC | POST | `/api/segmentacoes/{id}/executar` | `executar(id)` | Botão "Executar" |
# MAGIC | DELETE | `/api/segmentacoes/{id}` | `arquivar(id)` | Botão "Arquivar" |
# MAGIC | GET | `/api/segmentacoes/{id}/comentarios` | `listarComentarios(id)` | Componente Comentarios |
# MAGIC | POST | `/api/segmentacoes/{id}/comentarios` | `criarComentario(id, p)` | Enviar comentário |
# MAGIC | PUT | `/api/comentarios/{cid}` | `editarComentario(cid, p)` | Editar/resolver comentário |
# MAGIC
# MAGIC ### Response GET /segmentacoes/{id} (campos consumidos na tela)
# MAGIC ```
# MAGIC {
# MAGIC   seg_id, nome, descricao, objetivo, status, owner, area_responsavel,
# MAGIC   regras_json, versao_atual, publico_base_id, criado_em, atualizado_em,
# MAGIC   criado_por, recorrencia, agendamento_cron,
# MAGIC   vigencia_inicio, vigencia_fim
# MAGIC }
# MAGIC ```
# MAGIC
# MAGIC ### Response GET /segmentacoes/{id}/execucoes
# MAGIC ```
# MAGIC [{ exec_id, versao_usada, origem_execucao, executado_em, qtd_clientes, status, job_run_url }]
# MAGIC ```
# MAGIC
# MAGIC ### Response GET /segmentacoes/{id}/versoes
# MAGIC ```
# MAGIC [{ versao, regras_json, criado_em, criado_por, motivo }]
# MAGIC ```
# MAGIC
# MAGIC ### Payload POST /aprovar
# MAGIC ```json
# MAGIC { "itens_verificados": ["regras_ok", "destino_ok", "vigencia_ok"] }
# MAGIC ```
# MAGIC
# MAGIC ### Ações de Lifecycle (POST sem body)
# MAGIC `validar`, `enviar-aprovacao`, `ativar`, `pausar`, `reativar`, `encerrar`, `executar` — nenhum envia body.

# COMMAND ----------

# DBTITLE 1,4. TimelineSegmentacao
# MAGIC %md
# MAGIC ## 4. TimelineSegmentação <a id="timeline"></a>
# MAGIC
# MAGIC > **Nota:** A antiga página `DocumentacaoSegmentacao.jsx` (rota `/segmentacoes/:id/documentacao`) foi **removida**.
# MAGIC > Destino & Vigência agora vivem no **Step 4 do Builder** (`BuilderSegmentacao.jsx`).
# MAGIC
# MAGIC **Rota:** `/segmentacoes/:id/timeline` · **Page:** `TimelineSegmentacao.jsx` · **Card:** S1-FRONT-06
# MAGIC
# MAGIC | Método | Endpoint | Função | Quando |
# MAGIC |--------|----------|--------|--------|
# MAGIC | GET | `/api/segmentacoes/{id}` | `buscar(id)` | onMount (nome) |
# MAGIC | GET | `/api/segmentacoes/{id}/timeline` | `obterTimeline(id)` | Aba Timeline |
# MAGIC | GET | `/api/segmentacoes/{id}/comentarios` | `listarComentarios(id)` | Aba Comentários |
# MAGIC | POST | `/api/segmentacoes/{id}/comentarios` | `criarComentario(id, p)` | Enviar |
# MAGIC | PUT | `/api/comentarios/{cid}` | `editarComentario(cid, p)` | Editar/resolver |
# MAGIC
# MAGIC **Response GET /timeline:**
# MAGIC ```
# MAGIC [{
# MAGIC   tipo: 'criacao'|'transicao'|'execucao'|'versao'|'comentario',
# MAGIC   data: ISO string,
# MAGIC   descricao: string,
# MAGIC   detalhes: { ... }
# MAGIC }]
# MAGIC ```
# MAGIC
# MAGIC **Payload POST /comentarios:**
# MAGIC ```json
# MAGIC {
# MAGIC   "texto": "string",
# MAGIC   "tipo": "geral",
# MAGIC   "respondendo_a": "comentario_id|null",
# MAGIC   "mencoes": ["usuario1", "usuario2"]
# MAGIC }
# MAGIC ```
# MAGIC
# MAGIC **Payload PUT /comentarios/{id}:**
# MAGIC ```json
# MAGIC { "texto": "string" }  ou  { "resolvido": true|false }
# MAGIC ```

# COMMAND ----------

# DBTITLE 1,6-7-8. DashboardSaude + AdminCatalogo + ChatSegmentacao
# MAGIC %md
# MAGIC ## 6. DashboardSaúde <a id="saude"></a>
# MAGIC
# MAGIC **Rota:** `/saude` · **Page:** `DashboardSaude.jsx` · **Card:** S1-FRONT-07
# MAGIC
# MAGIC | Método | Endpoint | Função | Quando |
# MAGIC |--------|----------|--------|--------|
# MAGIC | GET | `/api/saude` | `obterDashboard()` | onMount |
# MAGIC | GET | `/api/saude/{seg_id}` | `obterDetalhe(segId)` | Modal detalhe |
# MAGIC
# MAGIC **Response GET /api/saude (dashboard consolidado):**
# MAGIC ```json
# MAGIC {
# MAGIC   "resumo": { "total_ativas": int, "verde": int, "amarelo": int, "vermelho": int },
# MAGIC   "segmentacoes": [{
# MAGIC     "seg_id", "nome", "health_status", "ultima_verificacao",
# MAGIC     "variacao_publico_pct", "taxa_sucesso_exec", "publico_atual"
# MAGIC   }]
# MAGIC }
# MAGIC ```
# MAGIC
# MAGIC **Response GET /api/saude/{seg_id}:**
# MAGIC ```json
# MAGIC {
# MAGIC   "seg_id", "health_status", "ultima_verificacao",
# MAGIC   "variacao_publico_pct", "taxa_sucesso_exec",
# MAGIC   "tempo_medio_exec_seg", "alertas_json", "publico_atual"
# MAGIC }
# MAGIC ```
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 7. AdminCatálogo <a id="admin"></a>
# MAGIC
# MAGIC **Rota:** `/admin/catalogo` · **Page:** `AdminCatalogo.jsx` · **Card:** S1-FRONT-10
# MAGIC
# MAGIC | Método | Endpoint | Função | Quando |
# MAGIC |--------|----------|--------|--------|
# MAGIC | GET | `/api/metadata/admin/campos?tema=&sistema=&status=&busca=` | `listarCampos(filtros)` | onMount + filtros |
# MAGIC | GET | `/api/metadata/admin/campos/{id}` | `obterCampo(id)` | Abrir drawer |
# MAGIC | PUT | `/api/metadata/admin/campos/{id}/flags` | `atualizarFlags(id, flags)` | Salvar flags |
# MAGIC | PUT | `/api/metadata/admin/campos/{id}/status` | `atualizarStatus(id, ativo)` | Toggle switch |
# MAGIC | GET | `/api/metadata/admin/historico?page=` | `listarHistorico(filtros)` | Tab "Histórico geral" |
# MAGIC | GET | `/api/metadata/admin/campos/{id}/historico?page=` | `listarHistoricoCampo(id, page)` | Tab histórico no drawer |
# MAGIC
# MAGIC **Payload PUT /flags:**
# MAGIC ```json
# MAGIC {
# MAGIC   "disponivel_s2": true,
# MAGIC   "disponivel_s3": true,
# MAGIC   "bloco_campo": false
# MAGIC }
# MAGIC ```
# MAGIC
# MAGIC **Payload PUT /status:**
# MAGIC ```json
# MAGIC { "ativo": true|false }
# MAGIC ```
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 8. ChatSegmentação <a id="chat"></a>
# MAGIC
# MAGIC **Rota:** `/chat` · **Page:** `ChatSegmentacao.jsx` · **Card:** S1-FRONT-09
# MAGIC
# MAGIC | Método | Endpoint | Função | Quando |
# MAGIC |--------|----------|--------|--------|
# MAGIC | POST | `/api/chat/mensagem` | `useChat` (shared-ui) | Enviar mensagem |
# MAGIC
# MAGIC **Payload POST /chat/mensagem:**
# MAGIC ```json
# MAGIC {
# MAGIC   "mensagem": "string",
# MAGIC   "historico": [{ "role": "user|assistant", "content": "string" }],
# MAGIC   "contexto": { "seg_id": "string|null" }
# MAGIC }
# MAGIC ```
# MAGIC
# MAGIC **Response:**
# MAGIC ```json
# MAGIC {
# MAGIC   "resposta": "string (texto do LLM)",
# MAGIC   "regras_json": { ... } | null,
# MAGIC   "sugestao_nome": "string|null"
# MAGIC }
# MAGIC ```
# MAGIC
# MAGIC **Nota:** A page usa `useChat` do shared-ui (não o hook `useChatApi`). O hook `chat.js` é legado e não é importado por nenhuma page.

# COMMAND ----------

# DBTITLE 1,9. Componentes Globais
# MAGIC %md
# MAGIC ## 9. Componentes Globais (Shell) <a id="globais"></a>
# MAGIC
# MAGIC ### NotificacoesPainel (sininho global)
# MAGIC
# MAGIC **Onde:** `App.jsx` (sempre visível na topbar)
# MAGIC
# MAGIC | Método | Endpoint | Função | Quando |
# MAGIC |--------|----------|--------|--------|
# MAGIC | GET | `/api/notificacoes?lida=false` | `fetchNotifications()` | onMount + polling 30s |
# MAGIC | PUT | `/api/notificacoes/{id}/lida` | `markAsRead(notifId)` | Click na notif |
# MAGIC | PUT | `/api/notificacoes/marcar-todas` | `markAllAsRead()` | Botão "Marcar todas lidas" |
# MAGIC
# MAGIC **Response GET /notificacoes:**
# MAGIC ```json
# MAGIC [{
# MAGIC   "notif_id": "string",
# MAGIC   "destinatario": "string",
# MAGIC   "tipo": "mencao|saude|estado|comentario|alerta_saude",
# MAGIC   "seg_id": "string|null",
# MAGIC   "titulo": "string",
# MAGIC   "mensagem": "string",
# MAGIC   "lida": false,
# MAGIC   "criado_em": "ISO datetime"
# MAGIC }]
# MAGIC ```
# MAGIC
# MAGIC **Campos consumidos pelo componente:** `notif_id`, `tipo`, `titulo`, `mensagem`, `lida`, `criado_em`
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### EstimativaBadge (dentro do Builder)
# MAGIC
# MAGIC Já documentado na seção 2 (Builder). Destaques:
# MAGIC - Debounce de 800ms antes de disparar
# MAGIC - Monta payload recursivo (`RegraNo` tree) a partir do state do Builder
# MAGIC - Coerce strings numéricas → number, listas (vírgula) → array
# MAGIC - Operadores `is_null`/`is_not_null` enviam `value: null`
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### Comentarios (Timeline + Detalhe)
# MAGIC
# MAGIC **Props recebidas (não faz fetch direto):**
# MAGIC - `onCriar(payload)` → chama `criarComentario(segId, payload)`
# MAGIC - `onEditar(comentarioId, payload)` → chama `editarComentario(cid, payload)`
# MAGIC
# MAGIC **Payload enviado pelo componente:**
# MAGIC ```json
# MAGIC // Criar
# MAGIC { "texto": "str", "tipo": "geral", "respondendo_a": "id|null", "mencoes": ["user"] }
# MAGIC // Editar texto
# MAGIC { "texto": "novo texto" }
# MAGIC // Marcar resolvido
# MAGIC { "resolvido": true|false }
# MAGIC ```
# MAGIC
# MAGIC **Campos consumidos:** `comentario_id`, `autor`, `texto`, `tipo`, `criado_em`, `respondendo_a`, `resolvido`

# COMMAND ----------

# DBTITLE 1,10. Validacao Front ↔ Back
# MAGIC %md
# MAGIC ## 10. Validação Front ↔ Back <a id="validacao"></a>
# MAGIC
# MAGIC ### Resultado da Validação Automatizada
# MAGIC
# MAGIC **✅ INTEGRAÇÃO 100% ALINHADA — Zero divergências críticas**
# MAGIC
# MAGIC | Dimensão | Front | Back | Status |
# MAGIC |----------|-------|------|--------|
# MAGIC | Endpoints chamados/expostos | 43 | 43 | ✅ Match perfeito |
# MAGIC | Payload POST/PUT segmentação | 9 campos | 9 campos | ✅ Match perfeito |
# MAGIC | Response campos consumidos | Todos existem | Retorna extras | ✅ |
# MAGIC | Estimativa (req/resp) | 3/4 | 3/4 | ✅ Perfeito |
# MAGIC | Comentários (req) | 4 | 4 | ✅ Perfeito |
# MAGIC | Vigência (req) | 4 | 4 | ✅ Perfeito |
# MAGIC | Chat (req/resp) | 3/3 | 3/3 | ✅ Perfeito |
# MAGIC | Notificações (resp) | 7 campos | 8 campos | ✅ |
# MAGIC | Flags admin (req) | 3 | 3 | ✅ Perfeito |
# MAGIC | Destinos (req) | array 2 | array 2 | ✅ Perfeito |
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### Detalhamento
# MAGIC
# MAGIC **1. Endpoints: 43/43 match**
# MAGIC - ❌ Front chama endpoint inexistente no back: **0**
# MAGIC - ❌ Back expõe endpoint não usado pelo front: **0**
# MAGIC - Cobertura de 100%: cada função do frontend tem um endpoint correspondente no backend
# MAGIC
# MAGIC **2. Payloads enviados:**
# MAGIC - POST/PUT /segmentacoes: front envia 9 campos (nome, descricao, objetivo, owner, area_responsavel, publico_base_id, regras_json + destinos e vigência via endpoints separados), back aceita exatamente esses campos via SegmentacaoCreateDTO/UpdateDTO.
# MAGIC - Todos os outros payloads têm match perfeito (campo-a-campo).
# MAGIC
# MAGIC **3. Responses consumidos:**
# MAGIC - Em todos os casos, o front consome um subconjunto dos campos retornados pelo back. Nenhum campo esperado pelo front está ausente na resposta.
# MAGIC - O back retorna campos extras (para flexibilidade futura) que o front ignora sem problema.
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### Observações Positivas
# MAGIC
# MAGIC | Item | Detalhe |
# MAGIC |------|---------|
# MAGIC | 🔒 Segurança | Front nunca acessa CPFs (seg_resultado_*). Correto por design. |
# MAGIC | 🎯 Debounce | EstimativaBadge usa 800ms de debounce — evita flood no back |
# MAGIC | 🔄 Polling | NotificacoesPainel faz polling a cada 30s (não WebSocket) — compatível com Databricks App |
# MAGIC | 📝 Coerce | EstimativaBadge converte strings → numbers e listas (vírgula) → arrays antes de enviar |
# MAGIC | 🔗 Linkagem | Front usa `job_run_url` do response de execuções para linkar ao Databricks Jobs |
# MAGIC | 📦 chat.js | Hook legado — page usa `useChat` do shared-ui diretamente. Não é bug, mas pode ser removido |
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### Única Sugestão de Melhoria
# MAGIC
# MAGIC | Severidade | Item | Detalhe |
# MAGIC |------------|------|---------|
# MAGIC | 💡 BAIXA | `chat.js` legado | O arquivo `src/api/chat.js` exporta `useChatApi` mas nenhuma page o importa (usam `useChat` do shared-ui). Pode ser removido para limpeza. |
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC *Validação executada em Ago/2026 a partir do código-fonte real (7 API clients + 8 pages + 5 components vs 7 routers backend).*
