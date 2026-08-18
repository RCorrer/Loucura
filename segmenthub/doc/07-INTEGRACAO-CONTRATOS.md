# Integração — Implementação no S1 (SegmentHub)

> Detalhes de implementação específicos de como o S1 participa da integração.  
> Para a visão completa de todos os contratos da plataforma (4 sistemas),  
> ver [11-CONTRATOS-DADOS-EVENTOS.md](./11-CONTRATOS-DADOS-EVENTOS.md).

---

## 1. Dados Consumidos pelo S1

| Schema.Tabela | Produção | Uso no S1 |
|---|---|---|
| `publico.pub_*` | Equipe de dados | Públicos-base (SELECT no query_engine) |
| `caracteristicas.customer_features_wide` | Equipe de dados | Features para filtragem |
| `metadata.catalogo_caracteristicas` | S1 (admin) | Catálogo no-code |
| `metadata.catalogo_publicos` | S1 (admin) | Lista de públicos |
| `governanca.usuarios_perfil` | Admin global | RBAC |

---

## 2. Governança de Campos — Implementação

> Regras de desacoplamento completas: ver [11-CONTRATOS §3](./11-CONTRATOS-DADOS-EVENTOS.md).

**Como o S1 implementa a Regra #4:** O admin edita flags via `/api/metadata/admin/campos/{id}/flags`. A lógica de segmentação do S1 **nunca** consulta essas flags. S2 e S3 as acessam diretamente via GRANT SELECT.

### 3 Controles Independentes por Campo

O Admin Catálogo (`/admin/catalogo`) expõe **3 controles independentes** por campo, editáveis inline na tabela:

| Switch | Flag no Delta | Quem é afetado | Exemplo de uso |
|---|---|---|---|
| **Ativo (S1)** | `ativo` | TemaMenu do Builder — campo aparece nas regras | Desligar impede uso em segmentação |
| **S2 (Visão 360)** | `usavel_em_visao360` | S2 filtra `WHERE usavel_em_visao360 = true` | Desligar oculta da Visão 360 |
| **S3 (Peças)** | `usavel_em_peca` | S3 filtra `WHERE usavel_em_peca = true` | Desligar impede personalização |

**Independência total:** Um campo pode estar ativo para segmentação mas oculto do S2, visível no S2 mas indisponível para regras, ou liberado para S3 mas bloqueado no S2.

**Fluxo técnico (toggle inline):**

```
Admin clica Switch S3           PUT /api/metadata/admin/campos/{id}/flags
(AdminCatalogo.jsx)       ───▶  Body: { "usavel_em_peca": true }
       │                                     │
       │                        FlagUpdateDTO (Pydantic, Optional)
       │                                     │
       │                        MetadataAdminService:
       │                          1. Busca estado atual
       │                          2. Compara: False→True
       │                          3. UPDATE catalogo_caracteristicas SET usavel_em_peca = ?
       │                             WHERE caracteristica_id = ?
       │                          4. INSERT governanca_hist (acao='liberou', sistema_alvo='s3')
       │                                     │
       ▼                                     ▼
Snackbar: "Saldo: S3 liberado"    S3 lê: SELECT ... WHERE usavel_em_peca = true
```

**Trilha de auditoria:** Toda alteração grava registro em `metadata.catalogo_governanca_hist` com: quem, quando, qual flag, valor anterior/novo, ação (liberou/retirou/alterou_bloco), sistema_alvo.

### Padrão de Consumo para S2 e S3

S2 e S3 **não** usam API do S1 — leem diretamente via GRANT SELECT. Queries recomendadas:

```sql
-- S2 (ClientView): quais campos exibir na Visão 360
SELECT caracteristica_id, campo_label, campo_fisico, tabela_fisica, bloco_visao360
FROM plataforma.metadata.catalogo_caracteristicas
WHERE usavel_em_visao360 = true
  AND ativo = true
ORDER BY bloco_visao360, campo_label

-- S3 (EngagementHub): quais campos usar para personalização de peças
SELECT caracteristica_id, campo_label, campo_fisico, tabela_fisica
FROM plataforma.metadata.catalogo_caracteristicas
WHERE usavel_em_peca = true
  AND ativo = true
ORDER BY tema, campo_label
```

> **Importante:** S2/S3 devem incluir `AND ativo = true` para respeitar campos desativados globalmente.

### Semântica do `ativo` (flag global)

O campo `ativo` controla a **visibilidade no S1** em 3 pontos:

| Ponto de uso | Filtro | Efeito quando `ativo = false` |
|---|---|---|
| TemaMenu do Builder (frontend) | `GET /metadata/temas-completos` → `WHERE ativo = true` | Campo **não aparece** para seleção |
| Estimativa (query_engine.py) | `_carregar_catalogo()` → `WHERE ativo = true` | **`ValueError`** — campo não encontrado |
| Job seg_exec (execução real) | `catalogo_df.filter("ativo = true")` | **`ValueError`** — campo não encontrado |

### Resolução de Campos: caracteristica_id → tabela_fisica.campo_fisico

O frontend grava `campo_id = caracteristica_id` (ex: `"caract_idade"`). Esse é um **identificador lógico** — não é o nome da coluna física. Ambas as engines de SQL resolvem via catálogo:

```
Frontend state:           { campo_id: "caract_idade", op: ">", value: 18 }
                                      │
                          catalogo_caracteristicas
                          WHERE caracteristica_id = 'caract_idade'
                                      │
                                      ▼
                          campo_fisico: "idade"
                          tabela_fisica: "plataforma.caracteristicas.customer_features_wide"
                          join_key: "cpf_cnpj"
                                      │
                                      ▼
            SQL gerado: plataforma.caracteristicas.customer_features_wide.idade > ?
```

**Comparação das engines:**

| Aspecto | seg_exec (Job — Spark) | query_engine (Estimativa — SQL Warehouse) |
|---|---|---|
| Resolve campo_id → físico | `catalogo_df.filter(F.col("caracteristica_id") == campo_id)` | `_resolver_campo()` via cache do catálogo |
| Monta JOINs dinâmicos | `extrair_tabelas()` recursivo | `_tabelas_usadas` (set acumulado em `_resolver_campo`) |
| Resolve público base | `catalogo_publicos` → `tabela_fisica` + `join_key` | `_cache_publicos` → `tabela_fisica` + `join_key` |
| Exclusão | `AND NOT (...)` | `AND NOT (...)` |
| Parametrização | Valores inline (escape via `sql_val()`) | Params posicionais (`?`) |
| Operadores extras | contains, starts_with | contains, starts_with |

**Tabelas envolvidas podem variar por regra:** Se o usuário combina campos de tabelas diferentes (ex: `customer_features_wide` + `customer_digital_behavior`), ambas engines geram LEFT JOINs dinâmicos automaticamente com base no `join_key` de cada campo no catálogo.

### Edge Case: Campo desativado após uso em regras

```
  Admin desativa campo "saldo"      Segmentação X já usa "saldo" em regras_json
  (ativo = false)                    │
       │                             │
       ▼                             ▼
  Campo some do TemaMenu       seg_exec tenta resolver "saldo" no catálogo
  (novas regras impossíveis)        └─▶ catalogo_df.filter("ativo = true").first() = None
                                        └─▶ ValueError("Campo saldo não encontrado")
                                            └─▶ Execução falha com erro_metadado
```

**Comportamento intencional** (segurança): impede que dados de campos revogados continuem sendo usados.

**Mitigação recomendada:** Antes de desativar, o admin deve consultar o endpoint `GET /api/metadata/caracteristicas-em-uso` que lista quais campos estão em segmentações ativas. Se o campo está em uso, as segmentações afetadas devem ser pausadas/editadas antes da desativação.

---

## 3. Dependências do S1

```
  ┌────────────────────────────────────┐   ┌───────────────────────────────────┐
  │ OBRIGATÓRIO                        │   │ OPCIONAL (IA/Chat)                 │
  │                                    │   │                                   │
  │ • Catálogo plataforma + schemas    │   │ • Vector Search endpoint + índice│
  │ • DDLs S1 criados                  │   │ • Foundation Model disponível    │
  │ • Seeds: features_wide, catálogo,  │   │ • Agent Framework configurado   │
  │   golden_record, públicos           │   │                                   │
  │ • RBAC: 1 admin + 1 analista      │   └───────────────────────────────────┘
  │ • SQL Warehouse Serverless        │
  └────────────────────────────────────┘
```

---

## 4. Fluxo de Integração (S1 → S3)

```
  S1 (SegmentHub)              Delta Lake                  S3 (EngagementHub)
  ───────────────                ──────────                  ──────────────────
       │                           │                             │
       ├─ MERGE seg_resultado ──▶  │                             │
       ├─ INSERT seg_eventos ───▶  │                             │
       │                           │                             │
       │                           │ ◀─ Lê seg_eventos ─────────┤
       │                           │ ◀─ Lê seg_resultado ───────┤
       │                           │ ◀─ Lê seg_destino ─────────┤
       │                           │                             ├─ Dispara campanha
       │                           │ ◀─ Marca processado=true ──┤
       ▼                           ▼                             ▼
```

---

## 5. Fluxo de Integração (S1 → S2)

```
  S2 (ClientView 360)             Delta Lake (tabelas S1)
  ─────────────────────             ──────────────────────────
       │                                  │
       ├─ Lê seg_resultado_corrente ────▶ │  (cliente em quais segs?)
       ├─ Lê seg_definicao ───────────▶ │  (objetivo, resumo)
       ├─ Lê seg_destino ─────────────▶ │  (tem_humano = true?)
       │                                  │
       ▼
  Monta bloco "Campanhas & Segmentações" na Visão 360
```

---

## 6. Decisões de Integração Relevantes ao S1

| # | Decisão | Impacto no S1 |
|---|---|---|
| 1 | Todo segmento sistema2 = atendimento humano | `seg_destino` é contrato-chave |
| 2 | `seg_destino` nasce no S1 | S1 é produtor da natureza |
| 3 | S3 publica `segmento_campanha_map` | S1 não precisa conhecer campanhas |
| 4 | S1 é guardião das flags (não consumidor) | Admin edita; lógica não usa |
| 5 | S4 mede eficiência por si só | S1 só fornece dados brutos |

---

*Baseado nos DDLs reais e no CONTRATOS-DADOS-EVENTOS.md do projeto.*