# ROADMAP-S3-ENGAGEMENTHUB.md

> **29 cartões** (13 BACK + 7 JOBS + 9 FRONT) | Plataforma CDP Bradesco
> Status: Roadmap completo — implementação pendente

---

## Resumo do Sistema

* **Papel:** Marketing Cloud — campanhas, jornadas, peças, disparos (email/WhatsApp reais), waterfall/capping, tracking, otimização MAB.
* **Perfis:** analista, admin (via `governanca.usuarios_perfil`, sistema=`engagement`).
* **Consome:** `seg_resultado_corrente` + `seg_definicao` + `seg_destino` (S1), `governanca.consentimento`, `customer_features_wide`, `golden_record`, `eventos.retorno_atendimento` (S2).
* **Produz:** `tracking_disparo`, `disparo_eventos`, contratos `segmento_campanha_map` + `cliente_jornada_status` (views).
* **Sem chatbot** (fora de escopo).
* **Hierarquia:** Campanha (1) → (N) Jornada → (N) Peça; Jornada (1) → (1) Segmento de entrada.

---

## Checklist Completo

```
BACK (13):
[ ] S3-BACK-01  Fundação (db + security + main)
[ ] S3-BACK-02  Campanha (CRUD + ciclo de vida)
[ ] S3-BACK-03  Peças (CRUD + aprovação + variáveis + assets)
[ ] S3-BACK-04  Canais + Providers (Email + WhatsApp reais)
[ ] S3-BACK-05  Jornada (CRUD + grafo + validações + preview)
[ ] S3-BACK-06  Orquestrador (Waterfall + Capping + Consentimento)
[ ] S3-BACK-07  Motor de Jornada (lógica core)
[ ] S3-BACK-08  Motor de Disparo + Fila + Render Engine
[ ] S3-BACK-09  Tracking + Webhooks
[ ] S3-BACK-10  Disparo Avulso (DAV)
[ ] S3-BACK-11  Otimização MAB (Thompson Sampling)
[ ] S3-BACK-12  Operação (dashboard + alertas) + Admin
[ ] S3-BACK-13  Contratos de saída (validação + GRANTs)

JOBS (7):
[ ] S3-JOB-01   engagement_orquestrador
[ ] S3-JOB-02   motor_jornada
[ ] S3-JOB-03   motor_disparo
[ ] S3-JOB-04   otimizador_mab
[ ] S3-JOB-05   guardiao_campanha
[ ] S3-JOB-06   saude_operacional
[ ] S3-JOB-07   consumidor_conversao

FRONT (9):
[ ] S3-FRONT-01 Shell + navegação
[ ] S3-FRONT-02 Campanha (CRUD + ciclo)
[ ] S3-FRONT-03 Peça Email (GrapesJS + MJML)
[ ] S3-FRONT-04 Peça WhatsApp + Aprovação
[ ] S3-FRONT-05 Jornada (React Flow)
[ ] S3-FRONT-06 Disparo/Avulso
[ ] S3-FRONT-07 Otimização (MAB)
[ ] S3-FRONT-08 Operação
[ ] S3-FRONT-09 Admin
```

---

## Ordem de Implementação

```
BACK: 01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 09 → 10 → 11 → 12 → 13
  Dependências: 03 antes de ativar(02); 04 antes de disparo(08);
               06 antes de 07/08; 09 antes de 11(MAB); 13 por último

JOBS: 05(guardião) + 01(orquestrador) → 02(motor jornada) → 03(motor disparo)
      → 04(MAB, após tracking) → 06(saúde) → 07(consumidor_conversao)

FRONT: 01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 09
  Peças(03/04) antes de campanha ativar; Jornada(05) depois de peças
```

---

## Cartões Detalhados

### BACK-01: Fundação
* **Gera:** `db/databricks_client.py`, `core/security.py`, `main.py`, `app.yaml`, `requirements.txt`
* **DoD:** app sobe; `/docs`; RBAC bloqueia sem perfil; query parametrizada roda

### BACK-02: Campanha CRUD + Ciclo de Vida
* **Gera:** `api/campanha.py`, `models/campanha.py`
* **Ciclo:** RASCUNHO → EM_APROVACAO → APROVADA → ATIVA → {PAUSADA, ENCERRADA, CONCLUIDA}
* **DoD:** ciclo transita e audita; ativar bloqueia se peça não aprovada; limite configurável

### BACK-03: Peças + Aprovação + Variáveis + Assets
* **Gera:** `api/peca.py`, `models/peca.py`
* **DoD:** cria/versiona; variáveis só as permitidas (view); aprovação muda status; preview com dados fictícios

### BACK-04: Canais + Providers
* **Gera:** `providers/base.py`, `providers/email_provider.py`, `providers/whatsapp_provider.py`
* **Interface:** `ChannelProvider(ABC): validar_peca | renderizar | disparar | consultar_status`
* **DoD:** email real (Mailtrap); WhatsApp via template aprovado; catálogo reflete capacidades

### BACK-05: Jornada CRUD + Grafo
* **Gera:** `api/jornada.py`, `models/jornada.py`
* **Nós:** entrada, enviar_peca, esperar, condicao/split, ab_split, acao, saida
* **DoD:** cria/versiona grafo; validação detecta erros; simulação percorre sem enviar; teste real só lista interna

### BACK-06: Orquestrador (Waterfall + Capping + Consentimento)
* **Gera:** `core/orquestrador.py`, admin endpoints
* **Fluxo 6 etapas:** elegível → consentimento → múltipla elegibilidade → waterfall → capping → fila
* **DoD:** `orquestrador.py` produz fila respeitando governança; supressões registradas com motivo

### BACK-07: Motor de Jornada (lógica)
* **Gera:** `core/motor_jornada.py`
* **DoD:** cria estado para novos; avança nós; loops respeitam limite; alimenta `cliente_jornada_status`

### BACK-08: Motor de Disparo + Render Engine
* **Gera:** `core/motor_disparo.py`, `core/render_engine.py`, `api/disparo.py`
* **DoD:** envia email/whatsapp reais da fila; re-valida governança; renderiza com fallback; retry/idempotência

### BACK-09: Tracking + Webhooks
* **Gera:** `track/open.py`, `track/click.py`, `track/webhooks.py`
* **DoD:** pixel marca abertura; click redireciona; webhooks atualizam funil; cada update emite `disparo_eventos`

### BACK-10: Disparo Avulso (DAV)
* **Gera:** `api/avulso.py`, `models/avulso.py`
* **DoD:** cria DAV; passa governança; enfileira e envia; contadores refletem público/elegível/enviado

### BACK-11: Otimização MAB
* **Gera:** `core/mab.py`, admin endpoints
* **DoD:** recalcula pesos por Thompson; respeita tráfego mínimo; pausar/fixar vencedora funcionam

### BACK-12: Operação + Admin
* **Gera:** `api/operacao.py`, complementa `api/admin.py`
* **DoD:** dashboard lê saúde/fila/tracking; alertas; admin edita janela/retry/políticas

### BACK-13: Contratos de Saída
* **Ações:** validar views + GRANT SELECT para S2
* **DoD:** views retornam dados reais; S2 consegue consultar

---

### JOB-01: engagement_orquestrador
* **Gatilho:** periódico
* **Passos:** elegível → consentimento → waterfall → capping → enfileira entrada

### JOB-02: motor_jornada
* **Gatilho:** ~5min
* **Passos:** cria estado novos → processa prontos → log + atualiza estado

### JOB-03: motor_disparo
* **Gatilho:** ~5min
* **Passos:** lê fila → re-valida → renderiza → dispara via Provider → tracking

### JOB-04: otimizador_mab
* **Gatilho:** diário
* **Passos:** lê resultados → Thompson Sampling → atualiza pesos → histórico

### JOB-05: guardiao_campanha
* **Gatilho:** periódico
* **Passos:** vigencia_inicio→ATIVA; vigencia_fim→CONCLUIDA; eventos emitidos

### JOB-06: saude_operacional
* **Gatilho:** periódico
* **Checks:** filas travadas, rate limit, taxa falha, template rejeitado, job parado

### JOB-07: consumidor_conversao
* **Gatilho:** batch periódico
* **Passos:** lê retorno_atendimento → seta converteu_em → alimenta MAB
* **Atenção:** processado multi-consumidor (S3+S4) — usar controle por destino

---

### FRONT-01 a FRONT-09
Ver seção completa no roadmap original (shell, campanha, peça email/whatsapp, jornada React Flow, disparo/avulso, otimização, operação, admin).

---

## Mapa Tela → API

| Tela | Rota | APIs |
|---|---|---|
| Campanhas | `/campanhas` | GET/POST/PUT /campanhas; ciclo; limite |
| Peça Email | `/pecas/email/*` | /pecas; /variaveis; /preview; /assets |
| Peça WhatsApp | `/pecas/whatsapp/*` | /pecas; /whatsapp-templates; /aprovar |
| Jornada | `/jornadas/*` | /jornadas; /validar; /preview/* |
| Disparos | `/disparos*` | /disparo/fila; /avulso |
| Otimização | `/otimizacao` | /admin/otimizacao* |
| Operação | `/operacao` | /operacao/dashboard; /alertas |
| Admin | `/admin` | /admin/* |

---

## Validação DDL

| Status | Observação |
|---|---|
| ✅ | 10 DDLs com 33 tabelas + 3 views: 100% alinhados com os 29 cartões |
| ⚠️ | Naming: `supressao_optout` → recomendar renomear para `supressao_log` |
| ✅ | Dependências S1/S0 corretamente referenciadas |
| ✅ | Contratos de saída (views) com lógica validada |

---

*Roadmap consolidado — Agosto 2026.*
