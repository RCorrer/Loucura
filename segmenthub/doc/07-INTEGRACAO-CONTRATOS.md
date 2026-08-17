# Integração e Contratos — SegmentHub

> Contratos de dados, eventos e dependências com outros sistemas da plataforma.

---

## 1. Posição na Plataforma CDP

```
  ╔═══════════════════╗         ┌───────────────────┐         ┌───────────────────┐
  ║ S1 — SEGMENTHUB  ║───────▶│ S3 — ENGAGEMENT │───────▶│ S2 — CLIENTVIEW │
  ║ (produz base)     ║         │ (consome S1,   │         │ (consome S1     │
  ╚═══════════════════╝         │  produz track.)│         │  e S3)          │
         │                       └───────────────────┘         └───────────────────┘
         │                              │                        │
         │        ┌───────────────────┤                        │
         └───────▶│ S4 — COMPASSHUB │◀───────────────────────┘
                  │ (consome todos)  │
                  └───────────────────┘
```

**Ordem de deploy:** S1 → S3 → S2 → S4 (topológica pelo fluxo de dados)

---

## 2. Contratos de Dados Produzidos pelo S1 (GRANT SELECT)

Tabelas/views que o S1 expõe para outros sistemas lerem.

| Tabela/View | Consumidores | Colunas-chave | Uso |
|---|---|---|---|
| `segmentacao.seg_resultado_corrente` | S2, S3 | seg_id, cpf_cnpj | Público atual do segmento |
| `segmentacao.seg_definicao` | S2, S3, S4 | seg_id, seg_codigo, nome, objetivo, status, owner, area | Contexto e metadados |
| `segmentacao.seg_destino` | S2, S3, S4 | seg_id, destino, habilitado | Natureza (humano/digital) |
| `metadata.catalogo_caracteristicas` | S2, S3 | caracteristica_id, campo_label, usavel_em_*, bloco_visao360 | S2: Visão 360; S3: peças |
| `caracteristicas.customer_features_wide` | S2, S3 | cpf_cnpj + colunas | S2: Visão 360; S3: personalização |
| `segmentacao.seg_execucao`, `seg_saude` | S4 | — | Métricas de segmentação |

---

## 3. Eventos Produzidos (`eventos.seg_eventos`)

```
  S1 (produz) ─▶ INSERT ─▶ eventos.seg_eventos ─┬─▶ S3 (sabe que há público novo)
                                                └─▶ S4 (acompanhamento)
```

| tipo_evento | Consumidor | Ação |
|---|---|---|
| `publicada` | S3 | Sabe que há público novo |
| `executada` | S3 | Público atualizado |
| `aprovada` | S4 | Acompanhamento |
| `pausada` | S4 | Acompanhamento |
| `encerrada` | S4 | Acompanhamento |
| `reativada` | S4 | Acompanhamento |

**Payload JSON:**
```json
{
  "seg_id": "seg_abc123",
  "seg_codigo": "SEG-ALTA-RENDA-3F2A",
  "versao_usada": 2,
  "qtd_clientes": 15000,
  "destino": "sistema2"
}
```

---

## 4. Dados Consumidos pelo S1

| Schema.Tabela | Produção | Uso no S1 |
|---|---|---|
| `publico.pub_*` | Equipe de dados | Públicos-base (SELECT no query_engine) |
| `caracteristicas.customer_features_wide` | Equipe de dados | Features para filtragem |
| `metadata.catalogo_caracteristicas` | S1 (admin) | Catálogo no-code |
| `metadata.catalogo_publicos` | S1 (admin) | Lista de públicos |
| `governanca.usuarios_perfil` | Admin global | RBAC |

---

## 5. Regras de Desacoplamento

```
  ┌───────────────────────────────────────────────────────────────────────────┐
  │  REGRAS DE DESACOPLAMENTO                                                 │
  │                                                                           │
  │  1️⃣  Nenhum sistema lê tabela INTERNA de outro                            │
  │       └─▶ Só GRANT SELECT no Unity Catalog                                │
  │  2️⃣  Produtor não conhece consumidores                                    │
  │  3️⃣  Comunicação via eventos (processado=false → true)                    │
  │  4️⃣  S1 é guardião/editor das flags S2/S3, mas NÃO as consome            │
  │       └─▶ Admin edita flags; S2/S3 leem via GRANT SELECT                  │
  │  5️⃣  Contratos publicados por quem cria a relação                          │
  └───────────────────────────────────────────────────────────────────────────┘
```

**Regra #4 detalhada:** O S1 hospeda as flags `usavel_em_peca`, `usavel_em_visao360`, `bloco_visao360` e o admin as edita via `/api/metadata/admin/campos/{id}/flags`. Porém, a lógica de segmentação do S1 **nunca** consulta essas flags. S2 e S3 as acessam diretamente via GRANT SELECT na tabela.

### Governança de Campos — Fluxo Completo

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
| Estimativa (query_engine.py) | Não filtra (usa `campo_id` do JSON salvo) | Funciona se a regra já existia |
| Job seg_exec (execução real) | `catalogo_df.filter("ativo = true")` | **`ValueError`** — campo não encontrado |

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

## 6. Dependências do S1

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

## 7. Fluxo de Integração (S1 → S3)

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

## 8. Fluxo de Integração (S1 → S2)

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

## 9. Decisões de Integração Relevantes ao S1

| # | Decisão | Impacto no S1 |
|---|---|---|
| 1 | Todo segmento sistema2 = atendimento humano | `seg_destino` é contrato-chave |
| 2 | `seg_destino` nasce no S1 | S1 é produtor da natureza |
| 3 | S3 publica `segmento_campanha_map` | S1 não precisa conhecer campanhas |
| 4 | S1 é guardião das flags (não consumidor) | Admin edita; lógica não usa |
| 5 | S4 mede eficiência por si só | S1 só fornece dados brutos |

---

*Baseado nos DDLs reais e no CONTRATOS-DADOS-EVENTOS.md do projeto.*