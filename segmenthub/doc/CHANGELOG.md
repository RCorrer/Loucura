# Changelog — SegmentHub (S1)

---

## [2026-08-21] Auditoria & Correções Completas

### Bug Fixes — Backend (8 correções)

#### CRÍTICOS

1. **`segmentacao_repository.py:buscar_por_id()`**  
   `job_id_databricks` não estava no SELECT (33→34 colunas).  
   *Impacto:* Frontend recebia `null` para o job_id mesmo quando populado.

2. **`segmentacao_repository.py:executar_segmentacao()`**  
   INSERT incompleto (faltava `versao_usada` e `executado_em`).  
   *Impacto:* Execuções gravavam com versão NULL — auditoria quebrada.

#### ALTOS

3. **`query_engine.py:_is_string_field()`**  
   Verificava `tipo_dado == "string"` (inexistente). Corrigido: `== "categorical"`.  
   *Impacto:* LOWER() não era aplicado em comparações de campos categóricos.

4. **`main.py`**  
   Router `chat` não estava importado nem registrado.  
   *Impacto:* Endpoint `/api/chat/*` retornava 404.

5. **`segmentacao_service.py:clonar()`**  
   Usava `tipo="clone"` (inválido; tipo é direta/composta).  
   Corrigido: `tipo_origem="clone"`, `seg_origem_id=seg_id`, preserva tipo original.  
   DTO expandido: `SegmentacaoCreateDTO` +`seg_origem_id`, `tipo_origem`.  
   Repository INSERT: 23→25 colunas.

6. **`security.py`**  
   DEV_USER não era protegido por gate de ENV.  
   *Impacto:* Em produção, fallback para "admin" era possível.

#### MÉDIOS/BAIXOS

7. **`doc/04-CICLO-VIDA-ESTADOS.md`**  
   Estado `aprovada` não documentado. Adicionado diagrama + tabela de transições.

8. **`print()` → `logger`**  
   Prints de debug substituídos por `logging.getLogger(__name__)` em `segmentacao_service.py` e `api/segmentacao.py`.

---

### DDL Fixes (8 correções em 5 arquivos)

| Arquivo | Correção |
|---|---|
| `01_metadata.sql` | View `campos_em_uso`: status `agendada` (inexistente) substituído por `aprovada` + `encerrada` |
| `02_segmentacao.sql` | Status COMMENT: adicionados `aprovada`/`encerrada`; `tipo_origem` +`chatbot`; `exec_id` formato uuid; `origem_execucao` `reativacao`; `seg_overlap` removida |
| `03_eventos.sql` | `tipo_evento` truncado: `reativad` → `reativada` |
| `04_segmentacao_history.sql` | Marcado como descontinuado (duplicata de 05) |
| `06_job_manager.sql` | Adicionados `USING DELTA`, `CLUSTER BY (seg_id)`, `TBLPROPERTIES` |

---

### Seed Rewrite (seed_completo notebook)

#### Problemas corrigidos:
- **RBAC:** `usuario_id` era "admin" (genérico). Agora usa email real para OBO auth
- **catalogo_caracteristicas:** `tabela_fisica` não era fully-qualified. Corrigido: `plataforma.caracteristicas.customer_features_wide`
- **catalogo_publicos:** `join_key` ausente (campo NOT NULL). Adicionado: `cpf_cnpj`
- **Operadores:** Apenas `["=", ">", "<"]`. Expandido para todos suportados pelo QueryEngine
- **regras_json:** Formato antigo `{operator, conditions}`. Corrigido para modelo `RegrasJson` (`{publico_base, inclusao, exclusao}`)
- **customer_features_wide:** Faltavam `segmento` e `dias_desde_ultimo_acesso`
- **seg_destino:** Schema tinha `atualizado_por` (não existe no DDL). Corrigido para `criado_em`
- **seg_definicao:** Faltava `job_id_databricks` no schema da seed
- **exec_id:** Formato legado. Corrigido para uuid
- **estado_civil:** Title case no gerador ≠ lowercase no domínio. Normalizado

#### Dados adicionados:
- `seg_saude`: 2 registros (health verde para as segmentações seed)
- `seg_versao`: 2 registros (versão 1 de cada seg)
- `seg_historico_estado`: 3 registros (trilha rascunho→em_aprovacao→aprovada→ativa)
- 6 tabelas auxiliares inicializadas vazias: `seg_comentario`, `seg_notificacao`, `seg_job_log`, `seg_resultado_historico`, `seg_eventos`, `catalogo_governanca_hist`

#### Tabelas necessárias para criar segmentação (fluxo completo):
1. `governanca.usuarios_perfil` — auth (lookup por email)
2. `metadata.catalogo_caracteristicas` — campos disponíveis (18 campos, 4 temas)
3. `metadata.catalogo_publicos` — públicos-base (3: varejo, uniclass, private)
4. `caracteristicas.customer_features_wide` — dados reais (50k clientes)
5. `publico.pub_*` — audiências base
6. `segmentacao.seg_definicao` — INSERT de novas segmentações
7. `segmentacao.seg_execucao` — registro de execuções
8. `segmentacao.seg_resultado_corrente` — resultados

---

### Doc Updates

- `02-SCHEMAS-TABELAS.md`: Status +`aprovada`; `exec_id` formato corrigido
- `04-CICLO-VIDA-ESTADOS.md`: Estado `aprovada` documentado (diagrama + transições)
- `CHANGELOG.md`: Criado (este arquivo)

---

## [2026-08-21] Validação DDL ↔ Backend — Fixes Adicionais

### Bug Fixes (4 correções)

#### CRÍTICO

9. **`comentario_repository.py:atualizar_comentario()`**  
   Ordem dos params posicionais invertida: `comentario_id` era inserido antes dos SET values.  
   *Impacto:* UPDATE executava `SET texto = <comentario_id>` + `WHERE comentario_id = <texto>` — corrupção silenciosa.

#### MÉDIOS

10. **`02_segmentacao.sql` — `seg_execucao.status` COMMENT**  
    Adicionado `falha_timeout` aos valores válidos (usado pelo job_manager ao atingir deadline).

11. **`05_governanca_hist.sql`**  
    Faltavam `CLUSTER BY (caracteristica_id)` e `TBLPROPERTIES ('delta.autoOptimize.optimizeWrite' = 'true')`.  
    *Impacto:* Performance degradada em queries de auditoria por característica.

12. **`segmentacao_service.py` — prints restantes**  
    ~30 `print()` nos métodos `criar()` e `clonar()` não foram removidos no fix #8 original.  
    Todos convertidos para `logger.debug/info/warning/error` com `exc_info=True` nos excepts.

---

## [2026-08-21] Validação DDL ↔ Jobs (notebooks)

### Escopo
Validados os 2 notebooks de job S1 (`seg_exec`, `seg_saude_consolidador`) contra os DDLs.

### seg_exec.py — ✅ ZERO inconsistências
6 operações SQL (SELECT, MERGE, INSERT, UPDATE) em 7 tabelas:
`seg_definicao`, `catalogo_caracteristicas`, `catalogo_publicos`, `seg_resultado_corrente`,
`seg_resultado_historico`, `seg_execucao`, `seg_saude`. Todas as colunas batem com DDL.

### seg_saude_consolidador.py — 2 fixes

13. **Step 2: status `'rodando'` inexistente no filtro**  
    `WHERE status IN ('rodando', 'em_execucao')` — backend nunca insere `rodando` (DDL define apenas `em_execucao`).  
    Corrigido para `WHERE status = 'em_execucao'`.  
    *Impacto:* Condição morta (nunca matchava), mas confusa e inconsistente com DDL.

14. **Step 5: INSERT notificação com f-string (SQL Injection risk)**  
    Usava interpolação direta de `titulo`, `mensagem`, `owner` (com `.replace("'", "''")`).  
    Convertido para `spark.sql(..., args={...})` (parametrização nativa Spark 3.4+).  
    *Impacto:* Eliminava risco de SQL injection se nome/owner contivessem chars especiais.

---

## [2026-08-21] Validação Integração Backend ↔ Jobs

### Issue Crítico Encontrado

**Registro `seg_execucao` preso em `em_execucao` quando job falha prematuramente.**

Fluxo problemático (antes do fix):
1. Backend gera `exec_id` e insere em `seg_execucao` com status `em_execucao`
2. Backend dispara `run_now` com `exec_id` propagado via widget param
3. Job faz validação (status, vigência) e chama `dbutils.notebook.exit()`
4. **Registro fica preso** em `em_execucao` por 2h até consolidador detectar

### Fix #15: Error handler global em `seg_exec`

- Adicionada função `_marcar_exec_erro(motivo)` no Setup
- Step 1: todas as 3 saídas prematuras agora chamam `_marcar_exec_erro()` antes de `exit()`
- Step 2: público base não encontrado → graceful exit com UPDATE `erro`
- Step 3: exception na query SQL → try/except → `_marcar_exec_erro()` + exit
- Step 4: exception na persistência → try/except → `_marcar_exec_erro()` + exit
- Steps 5-6: se falharem após resultado computado, o notebook crasha mas o
  consolidador detecta em 2h (aceitável — resultado já está em seg_resultado_corrente)

*Impacto:* Feedback imediato para o usuário em execuções manuais. Antes: até 2h de delay.

### Validado (sem issues)

- Contrato `exec_id` entre service e notebook: ✅ (IS_PREREGISTERED → UPDATE, agendada → INSERT)
- Params `notebook_params` do `run_now`: ✅ (seg_id, origem_execucao, exec_id)
- Params `base_parameters` do `criar_job`: ✅ (seg_id, origem_execucao=agendada, sem exec_id)
- Ciclo ativar/pausar/reativar/deletar ↔ jobs.create/update/delete: ✅
- `atualizar_vigencia` sync cron → `atualizar_schedule`: ✅
- Consolidador lê `seg_definicao.status='ativa'` + `seg_execucao`: ✅
- Consolidador marca `falha_timeout` → backend lê via `listar_execucoes()`: ✅
- Consolidador gera `seg_notificacao` → backend lê via `listar_notificacoes()`: ✅
- `seg_saude` escrita por seg_exec (individual) e consolidador (bulk): ✅
- Backend lê `seg_saude` via `saude_repository.buscar_saude_por_seg_id()`: ✅
