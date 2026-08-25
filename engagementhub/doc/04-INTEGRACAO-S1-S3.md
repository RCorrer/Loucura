# Integração S1 (SegmentHub) ↔ S3 (EngagementHub)

> Como o S3 consome segmentações produzidas pelo S1.

---

## 1. Visão Geral

```
┌───────────────────────────────────────────────────────────────┐
│  S1 — SegmentHub                                              │
│  (Produtor de segmentos)                                      │
│                                                               │
│  Analista cria segmentação → Aprova → Job ativa               │
│  Job (seg_exec) roda no cron → MERGE seg_resultado_corrente   │
├───────────────────────────────────────────────────────────────┤
│  CONTRATO: plataforma.segmentacao.seg_resultado_corrente      │
│  Colunas: seg_id (PK composta), cpf_cnpj, exec_id, entrou_em  │
│  Semântica: MERGE com DELETE → sempre última população válida   │
├───────────────────────────────────────────────────────────────┤
│  S3 — EngagementHub                                            │
│  (Consumidor de segmentos)                                    │
│                                                               │
│  Orquestrador: valida seg ativo → carrega CPFs → enfileira    │
│  Avulso: valida seg ativo → carrega CPFs → governaça → envio │
└───────────────────────────────────────────────────────────────┘
```

---

## 2. Tabelas Consumidas (S1 → S3)

| Tabela S1 | Schema UC | Uso no S3 | Quem consome |
|---|---|---|---|
| `seg_resultado_corrente` | plataforma.segmentacao | CPFs do segmento | orquestrador, avulso |
| `seg_definicao` | plataforma.segmentacao | Validar status ativo | orquestrador, avulso |
| `seg_destino` | plataforma.segmentacao | Autorização de publicação | orquestrador, avulso |
| `catalogo_caracteristicas` | plataforma.metadata | View variaveis_disponiveis | frontend (editor peças) |

---

## 3. Fluxo de Execução Detalhado

### 3.1 S1 produz o segmento (Job `seg_exec`)

```sql
-- 1. Gera query dinâmica a partir de regras_json
-- (resolve campo_id → tabela_fisica.campo_fisico via catalogo_caracteristicas)
SELECT DISTINCT {tabela_base}.{join_key} AS cpf_cnpj
FROM {tabela_base}
LEFT JOIN {tabela_feat} ON ...
WHERE {condições_das_regras}

-- 2. MERGE no resultado corrente (snapshot atual do segmento)
MERGE INTO seg_resultado_corrente AS target
USING (SELECT :seg_id AS seg_id, cpf_cnpj FROM resultado) AS source
ON target.seg_id = source.seg_id AND target.cpf_cnpj = source.cpf_cnpj
WHEN NOT MATCHED THEN INSERT (seg_id, cpf_cnpj, exec_id, entrou_em)
  VALUES (source.seg_id, source.cpf_cnpj, :exec_id, current_timestamp())
WHEN NOT MATCHED BY SOURCE AND target.seg_id = :seg_id THEN DELETE;
```

**Semântica do MERGE+DELETE:** Quem saiu do segmento é deletado. A tabela sempre reflete a população **atual** do segmento.

### 3.2 S3 consome o segmento (Orquestrador)

```python
# core/orquestrador.py

# Passo 0: Validar que o segmento está ativo e autorizado
if not validar_segmento_ativo(seg_id, client):
    return set()  # Ignora silenciosamente (logga warning)

# Passo 1: Carregar população
SELECT cpf_cnpj FROM seg_resultado_corrente WHERE seg_id = ?

# Passo 2+: Aplicar governaça (consentimento, capping, waterfall)
```

### 3.3 S3 consome o segmento (Disparo Avulso)

```python
# api/avulso.py — POST /avulso/{id}/executar

# Passo 0: Validar segmento ativo + publicado
if not validar_segmento_ativo(seg_id):
    raise HTTPException(409, "Segmento não ativo ou não publicado para S3")

# Passo 1: SELECT cpf_cnpj FROM seg_resultado_corrente WHERE seg_id = ?
# Passo 2: Filtrar consentimento (status = 'opt_in')
# Passo 3: Enfileirar na fila_disparo
```

---

## 4. Validação `validar_segmento_ativo()`

Função centralizada em `core/orquestrador.py`:

```python
def validar_segmento_ativo(seg_id: str, client=None) -> bool:
```

**Check 1 — Segmento ativo em S1:**
```sql
SELECT status FROM seg_definicao
WHERE seg_id = ? AND habilitado = true
-- Aceita: status IN ('ativa', 'aprovada')
-- Rejeita: rascunho, pausada, arquivada, em_aprovacao
```

**Check 2 — Publicado para S3 (seg_destino):**
```sql
SELECT habilitado FROM seg_destino
WHERE seg_id = ? AND destino = 'S3'
-- Se registro existe E habilitado = false → rejeita
-- Se registro NÃO existe → permite (backward compatibility)
-- Se registro existe E habilitado = true → permite
```

**Backward compatibility:** Enquanto `seg_destino` não for populada pelo S1, a ausência de registro é interpretada como "permitido" (não bloqueia fluxos existentes).

---

## 5. Chave de Integração: `seg_id`

| Aspecto | Valor |
|---|---|
| Formato | `seg_{uuid4().hex[:12]}` (ex: `seg_7a3bc1d2e4f0`) |
| Gerado por | S1 (SegmentacaoService._gerar_seg_id()) |
| Armazenado em S3 | `jornada.seg_entrada_id` |
| Imutável | Sim — nunca muda após criação |

---

## 6. View `variaveis_disponiveis` (S1 metadata → S3 frontend)

```sql
CREATE OR REPLACE VIEW plataforma.engagement.variaveis_disponiveis AS
SELECT caracteristica_id AS campo_id, campo_label, tipo_dado, descricao
FROM plataforma.metadata.catalogo_caracteristicas
WHERE ativo = true
  AND sensibilidade = 'normal'
  AND usavel_em_peca = true;
```

O S1 mantém o `catalogo_caracteristicas` com a flag `usavel_em_peca = true` para campos que podem ser usados em templates de peça (personalização).

---

## 7. Cenários de Borda

| Cenário | Comportamento S3 |
|---|---|
| S1 pausa o segmento | Orquestrador ignora (log info), DAV retorna 409 |
| S1 arquiva o segmento | Idem acima (habilitado=false) |
| S1 nunca executou o segmento | seg_resultado_corrente vazio → 0 candidatos → nenhum envio |
| seg_destino não tem registro para seg_id | Permite (backward compat) |
| seg_destino.habilitado = false | Bloqueia (segmento não autorizado) |
| S1 deleta CPFs do segmento (MERGE DELETE) | Próxima execução do orquestrador não os encontra |

---

## 8. SLAs e Latência

| Etapa | Latência típica |
|---|---|
| S1 Job executa (cron) | Diário ou semanal (config por segmento) |
| MERGE em seg_resultado_corrente | \~30s-5min (depende do volume) |
| S3 orquestrador consome | \~5min após job S3 disparar |
| **Latência total S1→S3** | **Até 24h (cron diário)** |

O S3 consome o estado **point-in-time** da última execução do S1. Não há streaming/CDC entre sistemas.

---

## 9. Permissões Necessárias

O Service Principal do S3 precisa de:

```sql
GRANT SELECT ON TABLE plataforma.segmentacao.seg_resultado_corrente TO `sp-s3-engagementhub`;
GRANT SELECT ON TABLE plataforma.segmentacao.seg_definicao TO `sp-s3-engagementhub`;
GRANT SELECT ON TABLE plataforma.segmentacao.seg_destino TO `sp-s3-engagementhub`;
GRANT SELECT ON TABLE plataforma.metadata.catalogo_caracteristicas TO `sp-s3-engagementhub`;
```

---

*Implementação: `src/core/orquestrador.py` → `validar_segmento_ativo()`*
