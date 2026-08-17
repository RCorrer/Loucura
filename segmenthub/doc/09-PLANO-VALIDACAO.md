# Plano de Validação — SegmentHub (S1)

> Checklist minucioso para validação end-to-end de todos os fluxos do sistema.
> Cada item deve ser verificado em código-fonte E testado em runtime.

---

## FLUXO 1 — Criação de Segmentação (Builder → Save → Delta)

### 1.1 Frontend: State e Árvore Recursiva

| # | Checkpoint | Arquivo | O que verificar |
|---|---|---|---|
| 1.1.1 | State inicial correto | `BuilderSegmentacao.jsx` L54-58 | `regrasInclusao = { operator: 'AND', rules: [...] }` (objeto, NÃO array) |
| 1.1.2 | Reset ao trocar modo (edição→criação) | `BuilderSegmentacao.jsx` L171 | `setRegrasInclusao({ operator: 'AND', rules: [...] })` |
| 1.1.3 | handleSelectCampo grava `caracteristica_id` | `BuilderSegmentacao.jsx` L190 | `campo_id: campo.caracteristica_id` (não `campo_fisico`) |
| 1.1.4 | RuleBuilder.normalizeToTree aceita objeto | `RuleBuilder.jsx` | `if (val.operator && Array.isArray(val.rules)) return val` |
| 1.1.5 | RuleBuilder.normalizeToTree aceita array legado | `RuleBuilder.jsx` | Converte `[{rules}]` → `{ operator, rules }` |
| 1.1.6 | RuleNode recursão funciona | `RuleNode.jsx` | `isLeaf(item)` = `'campo_id' in item`; sub-nós renderizam RuleNode |
| 1.1.7 | RuleNode.onChange emite árvore atualizada | `RuleNode.jsx` | `onChange({ ...node, rules: newRules })` |
| 1.1.8 | ExclusaoBuilder usa RuleNode | `ExclusaoBuilder.jsx` | Mesmo padrão que RuleBuilder |

### 1.2 Frontend: handleSalvar (cleanTree + coerceValue)

| # | Checkpoint | O que verificar |
|---|---|---|
| 1.2.1 | `temFolhaValida` percorre árvore recursivamente | `node.rules.some(item => ...)` com recursão em sub-nós |
| 1.2.2 | `cleanTree` remove folhas com `campo_id` vazio | `if (!item.campo_id \|\| !item.op \|\| ...) return null` |
| 1.2.3 | `cleanTree` remove sub-nós vazios | `.filter(Boolean)` após recursão |
| 1.2.4 | `coerceValue` converte string numérica → number | `"18"` → `18` |
| 1.2.5 | `coerceValue` converte string boolean → boolean | `"true"` → `true` |
| 1.2.6 | `coerceValue` split vírgula para in/not_in/between | `"SP,RJ"` → `["SP", "RJ"]` |
| 1.2.7 | `coerceValue` is_null/is_not_null retorna null | Sem value |
| 1.2.8 | Saída de cleanTree é `{ operator, rules }` válido | Nunca retorna array |
| 1.2.9 | Payload final contém `regras_json.inclusao` e `regras_json.exclusao` | Ambos como árvore ou null |

### 1.3 Backend: Pydantic (regras.py)

| # | Checkpoint | O que verificar |
|---|---|---|
| 1.3.1 | `RegraFolha` aceita `campo_id`, `op`, `value` | `value: Optional[Union[str, int, float, bool, List]]` |
| 1.3.2 | `RegraNo` aceita `operator` e `rules` recursivo | `rules: List[Union['RegraFolha', 'RegraNo']]` |
| 1.3.3 | `RegraNo.model_rebuild()` resolve forward refs | Sem erro em runtime |
| 1.3.4 | `RegrasJson` aceita `inclusao` e `exclusao` | `exclusao: Optional[RegraNo]` |
| 1.3.5 | Discriminação folha vs nó funciona | Pydantic distingue por presença de `operator` vs `campo_id` |
| 1.3.6 | 3+ níveis aninhados aceitos | Testar `{ OR: [{ AND: [{ AND: [...] }] }] }` |

### 1.4 Backend: POST /segmentacoes

| # | Checkpoint | Arquivo | O que verificar |
|---|---|---|---|
| 1.4.1 | Endpoint cria registro em `seg_definicao` | `segmentacao.py` | INSERT com `regras_json` serializado |
| 1.4.2 | Status inicial = `rascunho` | `segmentacao_service.py` | Não pula para outro status |
| 1.4.3 | `job_id_databricks` é null no rascunho | DDL | Só criado no `ativar`/`executar` |
| 1.4.4 | Versão inicial = 1 | `seg_versao` | INSERT com `versao = 1` |
| 1.4.5 | Destinos gravados em `seg_destino` | Repository | INSERT per-destino |

---

## FLUXO 2 — Estimativa em Tempo Real (EstimativaBadge → query_engine → SQL Warehouse)

### 2.1 Frontend: EstimativaBadge

| # | Checkpoint | O que verificar |
|---|---|---|
| 2.1.1 | `podEstimar` percorre árvore recursivamente | `temFolha(node)`: trata objeto, array legado, e folha |
| 2.1.2 | `cleanTreeForEstimate` trata objeto árvore | `if (node.operator && Array.isArray(node.rules))` |
| 2.1.3 | `prepararRegras` faz split de vírgula | `"SP,RJ"` → `["SP", "RJ"]` para in/not_in/between |
| 2.1.4 | `prepararRegras` converte numéricos | `"18"` → `18` |
| 2.1.5 | `prepararRegras` converte booleans | `"true"` → `true` |
| 2.1.6 | Payload: `{ publico_base, inclusao: árvore, exclusao: árvore\|null }` | Formato RegrasJson |
| 2.1.7 | Debounce 800ms funciona | Não dispara a cada keystroke |
| 2.1.8 | AbortController cancela requests anteriores | `abortRef.current.abort()` |

### 2.2 Backend: query_engine.py

| # | Checkpoint | O que verificar |
|---|---|---|
| 2.2.1 | `_carregar_catalogo()` carrega com `WHERE ativo = true` | Campos inativos excluídos |
| 2.2.2 | `_carregar_publicos()` carrega com `WHERE ativo = true` | Públicos inativos excluídos |
| 2.2.3 | `_resolver_campo(campo_id)` retorna `tabela_fisica.campo_fisico` | NÃO usa campo_id direto |
| 2.2.4 | `_resolver_campo` registra tabela em `_tabelas_usadas` | Para JOINs dinâmicos |
| 2.2.5 | `_resolver_campo` com campo inexistente → ValueError | Mensagem clara |
| 2.2.6 | `_build_no` recursivo com parênteses | `f"({cond})"` para cada condição |
| 2.2.7 | Separator AND vs OR correto | `" AND "` se operator=="AND", senão `" OR "` |
| 2.2.8 | Exclusão usa `AND NOT (...)` | Não `AND (...)` |
| 2.2.9 | JOINs dinâmicos montados para tabelas != tabela_base | LEFT JOIN com join_key correto |
| 2.2.10 | Público base resolvido via `_cache_publicos` | Não hardcoded |
| 2.2.11 | `generate_estimativa_query` usa `approx_count_distinct` | Performance |
| 2.2.12 | Operador `contains` gera `LIKE ?` com `%valor%` | Params (não inline) |
| 2.2.13 | Operador `starts_with` gera `LIKE ?` com `valor%` | Params (não inline) |
| 2.2.14 | `between` valida lista com 2 elementos | ValueError se não |
| 2.2.15 | `in`/`not_in` valida que value é lista | ValueError se não |

### 2.3 Backend: EstimativaService + Repository

| # | Checkpoint | O que verificar |
|---|---|---|
| 2.3.1 | `RegraValidator.validar_regras()` chamado antes | Erros de validação retornam 422 |
| 2.3.2 | Validator verifica campo existe no catálogo | `campo_id` inválido → erro |
| 2.3.3 | Validator verifica operador permitido | `op` não na lista → erro |
| 2.3.4 | Repository executa com `params` (tuple) | Parametrizado, não inline |
| 2.3.5 | Resultado retorna `{ estimativa, inclusao, exclusao, tempo_ms }` | Formato correto |

---

## FLUXO 3 — Execução Real (Job seg_exec → Delta)

### 3.1 Job: Carregamento e Resolução

| # | Checkpoint | Cell | O que verificar |
|---|---|---|---|
| 3.1.1 | Lê `regras_json` de `seg_definicao` | Cell 3 | Desserializa JSON para dict |
| 3.1.2 | Carrega catálogo com `ativo = true` | Cell 4 | `spark.table(...).filter("ativo = true")` |
| 3.1.3 | Resolve `publico_base` via `catalogo_publicos` | Cell 4 | `tabela_fisica` + `join_key` |
| 3.1.4 | `build_condition` recursivo | Cell 4 | `if "rules" in rule: sub = build_condition(...)` |
| 3.1.5 | Resolve `campo_id` → `tabela_fisica.campo_fisico` | Cell 4 | `catalogo_df.filter(F.col(...))` |
| 3.1.6 | Campo inexistente → ValueError | Cell 4 | Mensagem clara com campo_id |

### 3.2 Job: Geração de SQL

| # | Checkpoint | O que verificar |
|---|---|---|
| 3.2.1 | `sql_val` boolean → `true`/`false` | NÃO `True`/`False` (Python) |
| 3.2.2 | `sql_val` string → escape aspas simples | `O'Brien` → `O''Brien` |
| 3.2.3 | `sql_val` numérico → sem aspas | `42` (não `'42'`) |
| 3.2.4 | BETWEEN usa `sql_val` em ambos valores | Datas string recebem aspas |
| 3.2.5 | IN/NOT_IN usa `sql_val` per-item | Lista heterogênea funciona |
| 3.2.6 | `extrair_tabelas()` recursivo | Percorre inclusão e exclusão |
| 3.2.7 | JOINs gerados para tabelas != tabela_base | LEFT JOIN com join_key |
| 3.2.8 | Exclusão como `AND NOT (...)` | Não `AND (...)` |
| 3.2.9 | SELECT DISTINCT com alias `cpf_cnpj` | Alinhado com DDL seg_resultado_corrente |

### 3.3 Job: Execução e Persistência

| # | Checkpoint | Cell | O que verificar |
|---|---|---|---|
| 3.3.1 | `spark.sql(query_sql)` executa sem erro | Cell 4 | SQL válido |
| 3.3.2 | MERGE em `seg_resultado_corrente` | Cell 5 | Upsert por (seg_id, cpf_cnpj) |
| 3.3.3 | INSERT em `seg_execucao` com status=sucesso | Cell 6 | Registro de execução |
| 3.3.4 | INSERT em `seg_eventos` tipo=executada | Cell 7 | Para S3 consumir |
| 3.3.5 | UPDATE `seg_saude` com métricas | Cell 8 | publico_atual, ultima_verificacao |
| 3.3.6 | Em caso de erro: status=erro em seg_execucao | Cell 9 | try/except |

---

## FLUXO 4 — Ciclo de Vida (Status Transitions)

### 4.1 Mapa de Transições

| De | Para | Endpoint | Permissão | UI (DetalheSegmentacao) |
|---|---|---|---|---|
| `rascunho` | `em_aprovacao` | POST /:id/enviar-aprovacao | analista | Botão "Enviar p/ Aprovação" |
| `rascunho` | (deletado) | DELETE /:id | analista | Botão "Descartar" + ConfirmDialog |
| `em_aprovacao` | `ativa` | POST /:id/aprovar | **admin** | ValidationModal (5 itens) |
| `ativa` | `pausada` | POST /:id/pausar | analista | Menu → ConfirmDialog |
| `ativa` | `encerrada` | POST /:id/encerrar | analista | Menu → ConfirmDialog |
| `ativa` | `arquivada` | POST /:id/arquivar | analista | Menu → ConfirmDialog |
| `pausada` | `ativa` | POST /:id/reativar | analista | Botão "Reativar" |
| `pausada` | `encerrada` | POST /:id/encerrar | analista | Menu → ConfirmDialog |
| `pausada` | `arquivada` | POST /:id/arquivar | analista | Menu → ConfirmDialog |
| `encerrada` | `ativa` | POST /:id/reativar | analista | Botão "Reativar" |
| `encerrada` | `arquivada` | POST /:id/arquivar | analista | Botão "Arquivar" |

### 4.2 Checklist per-transition

| # | Checkpoint | O que verificar |
|---|---|---|
| 4.2.1 | Backend valida status atual antes de transicionar | Rejeita transição inválida (ex: rascunho→ativa) |
| 4.2.2 | INSERT em `seg_historico_estado` | Registro com (de, para, alterado_por, timestamp) |
| 4.2.3 | INSERT em `seg_eventos` | tipo_evento correspondente |
| 4.2.4 | ConfirmDialog aparece para ações destrutivas | severity: warning/error |
| 4.2.5 | Aprovar requer perfil admin | `require_perfil(["admin"])` |
| 4.2.6 | Badge "X pendentes" na ListaSegmentacoes | Filtra `status = 'em_aprovacao'` |

---

## FLUXO 5 — Governança de Catálogo (Admin → Flags → S2/S3)

### 5.1 Frontend: AdminCatalogo

| # | Checkpoint | O que verificar |
|---|---|---|
| 5.1.1 | Switch `Ativo` (S1) editável inline | `handleToggleStatus(campo)` |
| 5.1.2 | Switch `S2` editável inline | `handleToggleFlag(campo, 'usavel_em_visao360')` |
| 5.1.3 | Switch `S3` editável inline | `handleToggleFlag(campo, 'usavel_em_peca')` |
| 5.1.4 | Filtro por sistema funciona | dropdown S2/S3 → filtra tabela |
| 5.1.5 | Snackbar com feedback claro | "campo: S3 (Peças) liberado/retirado" |
| 5.1.6 | Drawer edita `bloco_visao360` | TextField + validação (requer S2=true) |
| 5.1.7 | Histórico no drawer mostra trilha per-campo | Tab "Histórico" |
| 5.1.8 | Histórico geral na tab principal | Lista todas alterações recentes |

### 5.2 Backend: PUT /flags

| # | Checkpoint | O que verificar |
|---|---|---|
| 5.2.1 | `FlagUpdateDTO` aceita update parcial | Todos os campos são Optional |
| 5.2.2 | Repository: params SET antes, WHERE por último | `tuple(set_params + [caracteristica_id])` |
| 5.2.3 | Só atualiza flags que REALMENTE mudaram | Compara estado atual |
| 5.2.4 | Valida: `bloco_visao360` requer `usavel_em_visao360=true` | ValueError se não |
| 5.2.5 | Grava histórico per-flag alterada | `_gravar_historico()` para cada |
| 5.2.6 | `sistema_alvo` derivado da flag | `usavel_em_peca` → `"s3"` |
| 5.2.7 | `acao` derivada do valor | `False→True` = "liberou", `True→False` = "retirou" |
| 5.2.8 | Endpoint admin-only | `require_perfil(["admin"])` |

### 5.3 Consumo por S2/S3

| # | Checkpoint | O que verificar |
|---|---|---|
| 5.3.1 | S2 filtra `usavel_em_visao360 = true AND ativo = true` | Ambas condições |
| 5.3.2 | S3 filtra `usavel_em_peca = true AND ativo = true` | Ambas condições |
| 5.3.3 | Toggle S2 NÃO afeta S3 | Independentes |
| 5.3.4 | Toggle Ativo NÃO afeta flags S2/S3 | Status ≠ flags |
| 5.3.5 | GRANT SELECT concedido para S2/S3 | Unity Catalog |

---

## FLUXO 6 — Resolução de Campos (catálogo → SQL)

### 6.1 Catálogo: catalogo_caracteristicas

| # | Checkpoint | O que verificar |
|---|---|---|
| 6.1.1 | Coluna `caracteristica_id` é PK | Única, sem duplicatas |
| 6.1.2 | Coluna `campo_fisico` é o nome real da coluna | Existe na `tabela_fisica` |
| 6.1.3 | Coluna `tabela_fisica` é fully qualified | `catalog.schema.table` |
| 6.1.4 | Coluna `join_key` é a chave de join | Existe em tabela_fisica E na tabela_base |
| 6.1.5 | Coluna `operadores` é array válido | `[">", "<", "=", ...]` |
| 6.1.6 | Coluna `tema_ordem` existe para ordenação | Numérica |

### 6.2 Catálogo: catalogo_publicos

| # | Checkpoint | O que verificar |
|---|---|---|
| 6.2.1 | Coluna `publico_id` é PK | Única |
| 6.2.2 | Coluna `tabela_fisica` é fully qualified | Tabela existe e tem dados |
| 6.2.3 | Coluna `join_key` é a chave de join | Geralmente `cpf_cnpj` |
| 6.2.4 | Coluna `ativo` controla visibilidade | `false` → não aparece no Builder |

### 6.3 Resolução em Ambas Engines

| # | Checkpoint | query_engine | seg_exec |
|---|---|---|---|
| 6.3.1 | `campo_id` → `campo_fisico` | `_resolver_campo()` | `catalogo_df.filter(...)` |
| 6.3.2 | Registra tabela para JOINs | `_tabelas_usadas.add(...)` | `extrair_tabelas()` |
| 6.3.3 | SQL usa `tabela_fisica.campo_fisico` | ✓ | ✓ |
| 6.3.4 | NÃO usa `campo_id` direto | ✓ (CORRIGIDO) | ✓ |
| 6.3.5 | Campos de N tabelas → N-1 JOINs | ✓ | ✓ |
| 6.3.6 | Tabela == tabela_base → sem JOIN | ✓ | ✓ |

---

## FLUXO 7 — Saúde (seg_saude_consolidador → Dashboard)

| # | Checkpoint | O que verificar |
|---|---|---|
| 7.1 | Job `seg_saude_consolidador` calcula métricas | Notebook 9 cells |
| 7.2 | `health_status` derivado de regras | healthy/warning/critical |
| 7.3 | `taxa_sucesso_exec` é 0-100 | Frontend NÃO multiplica por 100 |
| 7.4 | `variacao_publico_pct` calculada corretamente | (atual - anterior) / anterior * 100 |
| 7.5 | API `GET /saude` retorna lista | Para DashboardSaude.jsx |
| 7.6 | API `GET /saude/:id` retorna detalhe | Para DetalheSegmentacao.jsx |

---

## FLUXO 8 — Destinos (seg_destino → S2/S3)

| # | Checkpoint | O que verificar |
|---|---|---|
| 8.1 | DestinoSelector: 2 switches independentes | sistema2 e sistema3 |
| 8.2 | PUT /:id/destinos atualiza `seg_destino` | MERGE (upsert) |
| 8.3 | S3 filtra `seg_destino WHERE destino='sistema3' AND habilitado=true` | Contrato |
| 8.4 | S2 filtra `seg_destino WHERE destino='sistema2' AND habilitado=true` | Contrato |
| 8.5 | Destinos buscados na edição | `buscarDestinos` no useEffect |

---

## FLUXO 9 — Segurança (RBAC)

| # | Checkpoint | O que verificar |
|---|---|---|
| 9.1 | `get_current_user` extrai de `X-Forwarded-Email` | Header Databricks Apps |
| 9.2 | `require_perfil(["admin"])` rejeita analista | HTTP 403 |
| 9.3 | `require_perfil(["admin", "analista"])` aceita ambos | HTTP 200 |
| 9.4 | Aprovar requer admin | Endpoint `/:id/aprovar` |
| 9.5 | Admin catálogo requer admin | Todos endpoints `/metadata/admin/*` |
| 9.6 | Analista pode criar/editar/executar | Endpoints regulares |

---

## FLUXO 10 — Integração (Eventos → S3)

| # | Checkpoint | O que verificar |
|---|---|---|
| 10.1 | seg_exec insere em `seg_eventos` tipo=executada | Cell 7 do notebook |
| 10.2 | Payload inclui `seg_id`, `qtd_clientes`, `destino` | Formato JSON documentado |
| 10.3 | `processado = false` no INSERT | S3 filtra por esse campo |
| 10.4 | S3 marca `processado = true` após consumir | Não reprocessa |
| 10.5 | Eventos de ciclo de vida (pausada, encerrada, etc.) | Inseridos nos endpoints |

---

## FLUXO 11 — Edição de Segmentação Existente

| # | Checkpoint | O que verificar |
|---|---|---|
| 11.1 | `useEffect` carrega `regras_json` do backend | GET /:id |
| 11.2 | JSON deserializado para árvore no state | `setRegrasInclusao(regras_json.inclusao)` |
| 11.3 | RuleBuilder renderiza árvore existente | Exibe regras salvas |
| 11.4 | Destinos carregados | `buscarDestinos` na edição |
| 11.5 | Público selecionado restaurado | `setPublicoSelecionado(...)` |
| 11.6 | Save incrementa versão | INSERT em `seg_versao` com versao+1 |
| 11.7 | Só edita em status `rascunho` | Backend rejeita em outros status |

---

## FLUXO 12 — Timeline e Comentários

| # | Checkpoint | O que verificar |
|---|---|---|
| 12.1 | GET /:id/timeline retorna eventos ordenados | DESC por data |
| 12.2 | Eventos incluem mudanças de estado | `seg_historico_estado` |
| 12.3 | Eventos incluem execuções | `seg_execucao` |
| 12.4 | Comentários via POST /:id/comentarios | INSERT em `seg_comentario` |
| 12.5 | Comentários exibidos no componente `Comentarios` | Lista com autor e data |

---

## CENÁRIOS DE EDGE CASE

| # | Cenário | Comportamento esperado |
|---|---|---|
| E1 | Campo desativado após uso em regras | seg_exec falha com `erro_metadado` |
| E2 | Público base desativado após uso | seg_exec falha com ValueError |
| E3 | Regras com 5+ níveis aninhados | cleanTree + build_condition recursivos |
| E4 | Valor string com apóstrofo (`O'Brien`) | sql_val escapa → `O''Brien` |
| E5 | Valor boolean True/False | sql_val → `true`/`false` (Spark) |
| E6 | BETWEEN com datas string | sql_val → `'2024-01-01'` (com aspas) |
| E7 | IN com lista vazia | Pydantic rejeita (validator) |
| E8 | Exclusão null | `AND NOT` NÃO é adicionado |
| E9 | Todos os campos da mesma tabela_fisica | Zero JOINs extras |
| E10 | Campos de 3 tabelas diferentes | 2 LEFT JOINs gerados |
| E11 | Admin tenta desativar campo em uso | Deve consultar `campos-em-uso` |
| E12 | Execução concorrente do mesmo segmento | Job SDK previne duplicação |
| E13 | Toggle S2/S3 sem alterar valor | Repository detecta sem mudança → noop |
| E14 | `bloco_visao360` sem `usavel_em_visao360=true` | ValueError no repository |

---

## MATRIZ DE COBERTURA POR COMPONENTE

| Componente | Fluxo(s) coberto(s) | Criticidade |
|---|---|---|
| `BuilderSegmentacao.jsx` | F1, F11 | 🔴 Alta |
| `EstimativaBadge.jsx` | F2 | 🔴 Alta |
| `RuleNode.jsx` | F1, F2, F11 | 🔴 Alta |
| `DetalheSegmentacao.jsx` | F4 | 🟡 Média |
| `AdminCatalogo.jsx` | F5 | 🟡 Média |
| `DestinoSelector.jsx` | F8 | 🟢 Baixa |
| `query_engine.py` | F2, F6 | 🔴 Alta |
| `seg_exec` (notebook) | F3, F6, F10 | 🔴 Alta |
| `metadata_admin_repository.py` | F5 | 🟡 Média |
| `regras.py` (Pydantic) | F1, F2, F3 | 🔴 Alta |
| `validator.py` | F2 | 🟡 Média |
| `security.py` | F9 | 🟡 Média |
| `segmentacao.py` (API) | F1, F4, F8, F11 | 🔴 Alta |
| `seg_saude_consolidador` | F7 | 🟢 Baixa |

---

*Gerado em 2025-07. Baseado na branch `feature/frontend-ux-gaps`.*