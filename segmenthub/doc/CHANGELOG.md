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
