# Contratos de Dados e Eventos — Plataforma CDP

> **Documento mestre de integração** entre os 4 sistemas.  
> Fonte de verdade dos contratos, eventos, payloads e decisões acordadas.  
> Sempre que um cartão fizer integração entre sistemas, referencie este documento.

---

## 1. Mapa de Dependências (Visão Geral)

```
  ┌─────────────────────────────────────────────────────────────────────────────────────┐
  │                    FLUXO DE DADOS — PLATAFORMA CDP                                  │
  └─────────────────────────────────────────────────────────────────────────────────────┘

  ╔═══════════════════╗         ╔═══════════════════╗         ╔═══════════════════╗
  ║ S1 — SEGMENTHUB  ║────────▶║ S3 — ENGAGEMENT  ║────────▶║ S2 — CLIENTVIEW  ║
  ║ (produz base)     ║         ║ (consome S1,      ║         ║ (consome S1       ║
  ║                   ║         ║  produz tracking) ║         ║  e S3)            ║
  ╚═══════════════════╝         ╚═══════════════════╝         ╚═══════════════════╝
         │                             │                             │
         │                             │                             │
         │         ╔═══════════════════════════════════╗              │
         └────────▶║      S4 — COMPASSHUB             ║◀─────────────┘
                   ║      (consome TODOS)              ║
                   ╚═══════════════════════════════════╝

  ┌───────────────────────────────────────────────────────────┐
  │  ORDEM DE DEPLOY (topológica):  S1 → S3 → S2 → S4       │
  │  Dependência forte S2→S3: engajamento/jornada            │
  │  Dependência fraca S3→S2: consentimento (funciona vazio) │
  └───────────────────────────────────────────────────────────┘
```

---

## 2. As 7 Decisões Acordadas

```
  ╔══════════════════════════════════════════════════════════════════════════════════╗
  ║  DECISÕES DE ARQUITETURA — IMUTÁVEIS                                           ║
  ╠══════════════════════════════════════════════════════════════════════════════════╣
  ║                                                                                ║
  ║  ① Segmento com destino S2 = atendimento humano (SEMPRE)                       ║
  ║     └─ S2 mostra como "ação do gerente"; se também digital, mostra engajamento ║
  ║                                                                                ║
  ║  ② seg_destino (S1) = controle de natureza (humano/digital/ambos)              ║
  ║     └─ Contrato-chave lido por S2, S3 e S4                                    ║
  ║                                                                                ║
  ║  ③ S3 publica segmento_campanha_map (view com seg→campanha)                    ║
  ║     └─ S2 consome para ligar seg_id→campanha                                   ║
  ║                                                                                ║
  ║  ④ View cliente_campanhas (S2) traz seg_destino com flags tem_humano/digital   ║
  ║     └─ Front decide o que renderizar                                           ║
  ║                                                                                ║
  ║  ⑤ S4 mede eficiência por si só (KPI/OKR); seg_destino é atributo de contexto ║
  ║     └─ Sem comparação humano-vs-digital como feature                           ║
  ║                                                                                ║
  ║  ⑥ Campanha mista: S2 mostra jornada + engajamento via views do S3             ║
  ║     └─ Views: segmento_campanha_map + cliente_jornada_status                   ║
  ║                                                                                ║
  ║  ⑦ Priorização (S2) configurável pelo admin; natureza = fator OPCIONAL         ║
  ║     └─ Fator em config.regras_priorizacao                                     ║
  ║                                                                                ║
  ╚══════════════════════════════════════════════════════════════════════════════════╝
```

---

## 3. Regras de Desacoplamento (Invioláveis)

```
  ┌───────────────────────────────────────────────────────────────────────────────────┐
  │  REGRAS DE DESACOPLAMENTO                                                         │
  │                                                                                   │
  │  ❶ Nenhum sistema lê tabela INTERNA de outro                                     │
  │     └─▶ Só tabelas/views-contrato via GRANT SELECT no Unity Catalog               │
  │                                                                                   │
  │  ❷ Produtor não conhece consumidores                                              │
  │     └─▶ Consumo é unilateral (GRANT SELECT)                                      │
  │                                                                                   │
  │  ❸ Comunicação assíncrona via EVENTOS                                             │
  │     └─▶ Padrão: processado=false → job consome → processado=true                 │
  │                                                                                   │
  │  ❹ S1 é GUARDIÃO/EDITOR das flags S2/S3, mas NÃO as consome                      │
  │     └─▶ Admin edita (usavel_em_peca, usavel_em_visao360, bloco_visao360)          │
  │     └─▶ S2/S3 leem por GRANT SELECT direto na tabela                             │
  │     └─▶ Lógica de segmentação do S1 NUNCA consulta essas flags                   │
  │                                                                                   │
  │  ❺ Contratos publicados por QUEM CRIA A RELAÇÃO                                  │
  │     └─▶ Ex: seg↔campanha criada no S3 → S3 publica segmento_campanha_map         │
  │                                                                                   │
  └───────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Contratos de Dados (GRANT SELECT)

Cada linha = uma permissão de leitura. Consumidor NUNCA acessa estrutura interna além do listado.

### 4.1 Produzido pelo S1 (SegmentHub)

| Tabela/View-contrato | Consumidores | Colunas-chave | Uso |
|---|---|---|---|
| `segmentacao.seg_resultado_corrente` | S2, S3 | seg_id, cpf_cnpj | Público atual do segmento |
| `segmentacao.seg_definicao` | S2, S3, S4 | seg_id, seg_codigo, nome, objetivo, objetivo_negocio, publico_alvo_descricao, resumo, owner, area_responsavel, seg_tags, status | Contexto e metadados |
| `segmentacao.seg_destino` | S2, S3, S4 | seg_id, destino, habilitado | Natureza humano/digital (decisão ②) |
| `metadata.catalogo_caracteristicas` | S2, S3 | caracteristica_id, campo_label, tipo_dado, sensibilidade, usavel_em_peca, usavel_em_visao360, bloco_visao360 | S2: Visão 360; S3: variáveis de peça |
| `caracteristicas.customer_features_wide` | S2, S3 | cpf_cnpj + colunas | S2: Visão 360; S3: personalização |
| `segmentacao.seg_execucao`, `seg_saude` | S4 | — | Métricas de segmentação |

### 4.2 Produzido pelo S3 (EngagementHub)

| Tabela/View-contrato | Consumidores | Colunas-chave | Uso |
|---|---|---|---|
| `engagement.tracking_disparo` | S2, S4 | cpf_cnpj, campanha_id, canal, *_em, status_atual | S2: engajamento; S4: funil/KPI |
| `engagement.segmento_campanha_map` (view) | S2 | seg_id, campanha_id, campanha_codigo, campanha_nome, campanha_status, jornada_id | Liga seg→campanha (decisão ③) |
| `engagement.cliente_jornada_status` (view) | S2 | cpf_cnpj, jornada_id, campanha_id, no_atual, status_jornada, historico_nos, qtd_nos_percorridos | Até onde foi na jornada (decisão ⑥) |
| `engagement.campanha`, `jornada`, `peca`, `otimizacao_resultado` | S4 | — | Métricas de campanha/jornada/peça |

### 4.3 Produzido pelo S2 (ClientView 360)

| Tabela/View-contrato | Consumidores | Colunas-chave | Uso |
|---|---|---|---|
| `atendimento.interacao` | S4 | tipo, resultado, responsavel_id, criado_em | Métricas de atendimento |
| (via evento) `retorno_atendimento` | S3, S4, governança | ver seção 5 | Conversão real, opt-out |

### 4.4 Produzido pelo S4 (CompassHub)

```
  ┌─────────────────────────────────────────────────────────┐
  │  S4 é quase 100% CONSUMIDOR.                            │
  │  Não publica contratos de dados para os outros          │
  │  (só insights visuais que não voltam automaticamente).  │
  └─────────────────────────────────────────────────────────┘
```

### 4.5 Compartilhado (Governança)

| Tabela | Escrita por | Lida por | Uso |
|---|---|---|---|
| `governanca.consentimento` | S2 (não-perturbe) | S3 (filtro de disparo) | Opt-out por canal |
| `governanca.usuarios_perfil` | bootstrap/admin | Todos | RBAC |

### 4.6 Dados Consumidos (o que cada sistema lê)

```
  ┌───────────────────────────────────────────────────────────────────────────┐
  │  MAPA DE CONSUMO                                                           │
  │                                                                            │
  │  S1 lê:  publico.*, caracteristicas.*, metadata.*, governanca.*            │
  │  S2 lê:  S1 (seg_resultado, seg_definicao, seg_destino, catalogo, feat.)  │
  │          S3 (tracking, segmento_campanha_map, cliente_jornada_status)      │
  │          Externo (golden_record, vinculo_cliente_responsavel)              │
  │  S3 lê:  S1 (seg_resultado, seg_definicao, seg_destino, catalogo, feat.)  │
  │          Governança (consentimento)                                        │
  │          Externo (golden_record)                                           │
  │  S4 lê:  S1 (seg_definicao, seg_destino, seg_execucao, seg_saude)         │
  │          S2 (interacao)                                                    │
  │          S3 (tracking, campanha, jornada, peca, otimizacao)                │
  └───────────────────────────────────────────────────────────────────────────┘
```

> Detalhes de implementação do consumo S1: ver [07-INTEGRACAO-CONTRATOS.md §1](./07-INTEGRACAO-CONTRATOS.md).

### 4.7 Dados de Origem (Externos)

| Tabela | Lida por | Uso |
|---|---|---|
| `core_cliente.golden_record` | S2, S3 | Cadastro + email/telefone |
| `analitico.vinculo_cliente_responsavel` | S2 | Encarteiramento (RLS) |
| `publico.pub_*` | S1 | Públicos-base |

---

## 5. Barramento de Eventos

```
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │  PADRÃO DE EVENTOS                                                          │
  │                                                                             │
  │  Produtor grava:  processado = false                                        │
  │       │                                                                     │
  │       ▼                                                                     │
  │  Job consumidor (destino) lê WHERE processado = false                       │
  │       │                                                                     │
  │       ▼                                                                     │
  │  Processa + marca:  processado = true                                       │
  └─────────────────────────────────────────────────────────────────────────────┘
```

### 5.1 `eventos.seg_eventos` (produz: S1)

| tipo_evento | Consumidor | Ação |
|---|---|---|
| `publicada` / `executada` | S3 | Sabe que há público novo/atualizado |
| `aprovada` / `pausada` / `encerrada` / `reativada` | S4 | Acompanhamento |

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

### 5.2 `eventos.retorno_atendimento` (produz: S2)

| tipo_evento | Consumidor (destino) | Ação |
|---|---|---|
| `desfecho_oferta` | S3 + S4 | Conversão real → tracking_disparo.converteu_em + MAB + KPI |
| `nao_perturbe` | governança | MERGE opt-out por canal |
| `atendimento_realizado` / `tentativa_contato` | S4 | Métrica de atendimento |

**Payload por tipo:**
```
  desfecho_oferta:
  ┌────────────────────────────────────────────────────────┐
  │ cpf_cnpj, campanha_id, resultado (aceitou|recusou|    │
  │ pensar), motivo, canal                                 │
  └────────────────────────────────────────────────────────┘

  nao_perturbe:
  ┌────────────────────────────────────────────────────────┐
  │ cpf_cnpj, canal (email|whatsapp|push|todos)            │
  └────────────────────────────────────────────────────────┘

  atendimento_*:
  ┌────────────────────────────────────────────────────────┐
  │ cpf_cnpj, canal, resultado                             │
  └────────────────────────────────────────────────────────┘
```

### 5.3 `eventos.disparo_eventos` (produz: S3)

| tipo_evento | Consumidor (destino) | Ação |
|---|---|---|
| `disparo_realizado` / `entregue` / `aberto` / `clicou` | S2 + S4 | Engajamento + KPI |
| `campanha_ativada` / `concluida` / `jornada_concluida` | S4 | Acompanhamento |

**Payload JSON:**
```json
{
  "cpf_cnpj": "12345678901",
  "campanha_id": "camp_xyz",
  "jornada_id": "jorn_abc",
  "peca_id": "peca_001",
  "canal": "email",
  "envio_id": "env_uuid",
  "timestamp": "2026-08-15T10:30:00Z"
}
```

---

## 6. Fluxo de Conversão (Ciclo Completo)

```
  ┌─────────────────────────────────────────────────────────────────────────────────────┐
  │                         CICLO DE CONVERSÃO                                          │
  └─────────────────────────────────────────────────────────────────────────────────────┘

  S3 dispara peça                                          S2 mostra ao gerente
  ┌──────────────┐    tracking_disparo    ┌──────────────┐    ┌──────────────────────┐
  │  ENVIO       │───(enviado/entregue/──▶│ ENGAJAMENTO  │───▶│ Bloco "Campanhas"    │
  │  (automático)│    aberto/clicou)       │ (registrado) │    │ no ClientView 360    │
  └──────────────┘                        └──────────────┘    └──────────┬───────────┘
                                                                         │
                                                               Gerente registra
                                                               desfecho (aceitou)
                                                                         │
                                                                         ▼
  ┌──────────────┐    retorno_atendimento  ┌──────────────┐    ┌──────────────────────┐
  │  CONVERSÃO   │◀──(destino: S3 + S4)───│ DESFECHO     │◀───│ Formulário           │
  │  REAL (KPI)  │                         │ (confirmado) │    │ interação (S2)       │
  └──────────────┘                         └──────────────┘    └──────────────────────┘
       │
       ├─▶ S3: preenche tracking_disparo.converteu_em + alimenta MAB
       └─▶ S4: registra conversão real no funil/KPI

  ┌───────────────────────────────────────────────────────────────┐
  │  SINAL FRACO (clique):  S3 → S2, automático                  │
  │  SINAL FORTE (venda):   S2 → S3, manual (confirmado humano)  │
  └───────────────────────────────────────────────────────────────┘
```

---

## 7. Como o S2 Monta o Bloco "Campanhas & Segmentações"

Consolidação das decisões ①, ③, ④, ⑥:

```
  Para cada seg_id do cliente (via seg_resultado_corrente + seg_definicao):

  ┌─────────────────────────────────────────────────────────────────────────────┐
  │  FONTE 1 — [S1] SEMPRE                                                     │
  │  seg_definicao: objetivo_negocio, resumo, publico_alvo_descricao            │
  │  → Mostra: contexto + "ação do gerente" (tem_humano = sempre true)          │
  └─────────────────────────────────────────────────────────────────────────────┘
         │
         │  SE tem_digital = true (seg_destino inclui 'sistema3'):
         ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │  FONTE 2a — [S3] segmento_campanha_map                                     │
  │  → Descobre campanha(s) vinculada(s) ao segmento                            │
  ├─────────────────────────────────────────────────────────────────────────────┤
  │  FONTE 2b — [S3] cliente_jornada_status                                    │
  │  → Até onde o cliente foi na jornada (nó atual, qtd percorridos)            │
  ├─────────────────────────────────────────────────────────────────────────────┤
  │  FONTE 2c — [S3] tracking_disparo                                          │
  │  → Aberturas/cliques (briefing de engajamento)                              │
  └─────────────────────────────────────────────────────────────────────────────┘

  ┌────────────────────────────────────────────────────────┐
  │  Segmento SÓ-HUMANO (tem_digital=false):              │
  │  → Mostra só Fonte 1 (sem engajamento — não houve     │
  │    disparo digital)                                    │
  │                                                        │
  │  Segmento MISTO (ambos):                               │
  │  → Mostra Fonte 1 + Fonte 2 (contexto + ação +        │
  │    jornada + engajamento)                              │
  └────────────────────────────────────────────────────────┘
```

---

## 8. Mapa Visual dos Contratos

```
  ┌─────────────────────────────────────────────────────────────────────────────────────────┐
  │                                                                                         │
  │           S1                        S3                        S2                        │
  │    ┌─────────────┐            ┌─────────────┐           ┌─────────────┐                │
  │    │ seg_definicao│───────────▶│ (lê)        │           │ (lê)        │                │
  │    │ seg_destino  │───────────▶│             │───────────▶│             │                │
  │    │ seg_resultado│───────────▶│             │           │             │                │
  │    │ catalogo_car.│───────────▶│ segmento_   │───────────▶│ cliente_    │                │
  │    │ features_wide│───────────▶│ campanha_map│           │ jornada_st. │                │
  │    └─────────────┘            │ tracking_   │───────────▶│ interacao   │────────┐      │
  │                                │ disparo     │           └─────────────┘        │      │
  │                                └─────────────┘                                  ▼      │
  │                                                                          ┌───────────┐ │
  │                                                                          │    S4     │ │
  │                                                                          │(consome   │ │
  │                                                                          │ todos)    │ │
  │                                                                          └───────────┘ │
  │                                                                                         │
  └─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Resumo

Este documento fixa: **7 decisões**, **5 regras de desacoplamento**, todos os **contratos de dados** (GRANT SELECT), todos os **eventos com payloads**, o **ciclo de conversão**, a montagem do **bloco de campanhas do S2** e a **ordem de dependência**. É a referência de integração para todos os roadmaps.

---

*Referência cruzada: para contratos específicos do S1, ver [07-INTEGRACAO-CONTRATOS.md](./07-INTEGRACAO-CONTRATOS.md).*