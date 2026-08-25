# S3 — Arquitetura Backend

> Camadas, módulos core, padrões e dependências

---

## 1. Camadas da Aplicação

```
  ┌────────────────────────────────────────────────────────────────────┐
  │                       REQUESTS (HTTP)                              │
  ├────────────────────────────────────────────────────────────────────┤
  │  CAMADA 1 — API LAYER (src/api/)                                    │
  │                                                                    │
  │  Responsável por: roteamento, validação Pydantic, RBAC, responses   │
  │  Não contém: lógica de negócio, SQL, acesso a dados                 │
  │                                                                    │
  │  campanha.py │ peca.py │ jornada.py │ canal.py │ orquestrador.py   │
  │  disparo.py  │ avulso.py │ operacao.py │ admin.py                   │
  ├────────────────────────────────────────────────────────────────────┤
  │  CAMADA 2 — CORE LAYER (src/core/)                                  │
  │                                                                    │
  │  Responsável por: lógica de negócio, regras, estado                 │
  │  Chamado por: API Layer (diretamente) e Jobs (via import)           │
  │                                                                    │
  │  orquestrador.py │ motor_jornada.py │ motor_disparo.py              │
  │  render_engine.py │ mab.py │ grafo_validator.py                     │
  │  config.py │ security.py                                           │
  ├────────────────────────────────────────────────────────────────────┤
  │  CAMADA 3 — DATA LAYER (src/db/)                                    │
  │                                                                    │
  │  Responsável por: conexão SQL, execução parametrizada               │
  │  databricks_client.py (produção) │ fake_client.py (teste/local)    │
  ├────────────────────────────────────────────────────────────────────┤
  │  CAMADA 4 — PROVIDERS (src/providers/)     [NB: fase FRONT]         │
  │                                                                    │
  │  Responsável por: integração com canais externos                    │
  │  base.py (ABC) │ email_provider.py │ whatsapp_provider.py           │
  └────────────────────────────────────────────────────────────────────┘
```

---

## 2. Módulos Core (Detalhe)

### 2.1 `core/orquestrador.py` — Pipeline de Elegibilidade

Motor principal que seleciona QUEM recebe comunicação. Executado pelo Job periódico.

```
  Etapa 1: Elegibilidade          Etapa 2: Consentimento
  ┌──────────────────────┐       ┌──────────────────────┐
  │ Para cada jornada ativa: │       │ Para cada candidato:  │
  │ 1. Validar seg ativo(S1) │  ──▶  │ 1. Check opt_out canal │
  │ 2. Carregar CPFs seg     │       │ 2. Suprimir + logar   │
  │ 3. Expandir candidatos   │       └──────────┬───────────┘
  └──────────────────────┘                │
                                           ▼
  Etapa 3: Waterfall              Etapa 4: Capping
  ┌──────────────────────┐       ┌──────────────────────┐
  │ Mesmo CPF em N jornadas:│       │ Limites diário/semanal:│
  │ Mantém só a de MAIOR   │  ──▶  │ 1. Count 7d/30d       │
  │ prioridade (waterfall) │       │ 2. Excede? suprime    │
  └──────────────────────┘       └──────────┬───────────┘
                                           │
                                           ▼
  Etapa 5: Janela de Envio        Etapa 6: Enfileirar
  ┌──────────────────────┐       ┌──────────────────────┐
  │ Horário permitido?      │       │ INSERT fila_disparo   │
  │ Ex: 08h-20h dias úteis │  ──▶  │ status='pendente'     │
  │ Fora? adia para próx.  │       │ pronto para motor     │
  └──────────────────────┘       └──────────────────────┘
```

**Funções exportadas:**

| Função | Descrição |
|---|---|
| `validar_segmento_ativo(seg_id)` | Check S1: seg_definicao.status + seg_destino.habilitado |
| `carregar_elegiveis_segmento(seg_id)` | Retorna set[cpf_cnpj] do segmento |
| `etapa_elegibilidade()` | Expande jornadas ativas em candidatos |
| `etapa_consentimento(candidatos)` | Filtra opt_out, loga supressão |
| `etapa_waterfall(candidatos)` | Mantém só maior prioridade por CPF |
| `etapa_capping(candidatos)` | Aplica freq. capping (7d/30d) |
| `etapa_janela(candidatos)` | Verifica horário permitido |
| `etapa_enfileirar(candidatos)` | INSERT na fila_disparo |

---

### 2.2 `core/motor_jornada.py` — Percurso do Grafo

Movimenta clientes pelo grafo da jornada. Executado pelo Job a cada ~5min.

```
  Para cada cliente com estado ativo:

  ┌───────────────────────────────────────────────────┐
  │ 1. Lê no_atual do estado_cliente                  │
  │ 2. Resolve tipo do nó (entrada/enviar/esperar/...) │
  │ 3. Executa lógica do nó:                           │
  │    • entrada: avançar para próximo                  │
  │    • enviar_peca: INSERT fila_disparo + avançar    │
  │    • esperar: verifica timeout/proxima_acao_em     │
  │    • condicao: avalia expressão → branch true/false│
  │    • ab_split: usa pesos MAB para escolher ramo    │
  │    • acao: executa side-effect (tag, notif)        │
  │    • saida: marca concluído + participacao          │
  │ 4. Atualiza no_atual + historico_nos               │
  │ 5. Registra em jornada_log                         │
  └───────────────────────────────────────────────────┘
```

**Tipos de nó suportados (7):**

| Tipo | Comportamento | Próximo nó |
|---|---|---|
| `entrada` | Ponto de entrada do grafo | next |
| `enviar_peca` | Enfileira peça para disparo | next |
| `esperar` | Pausa N horas/dias | next (após timeout) |
| `condicao` | Avalia expressão booleana | next_true / next_false |
| `ab_split` | Distribui por pesos MAB | branch_a / branch_b |
| `acao` | Tag, notificação, side-effect | next |
| `saida` | Finaliza jornada do cliente | — |

---

### 2.3 `core/motor_disparo.py` — Envio Efetivo

Consome `fila_disparo` e despacha para providers. Executado pelo Job a cada ~5min.

```
  Para cada item na fila (status='pendente'):

  1. Busca golden_record → email/telefone
  2. Re-valida consentimento (double-check)
  3. Renderiza peça (render_engine) com variáveis do cliente
  4. Despacha para provider (email/wpp)
  5. Registra em tracking_disparo (status=enviado)
  6. Se falha:
     a. Conta tentativas em disparo_tentativa
     b. Se < max_retry (config_retry) → status='retry'
     c. Se >= max_retry → status='falha_permanente'
```

---

### 2.4 `core/render_engine.py` — Personalização

Resolve variáveis (`{{nome}}`, `{{agencia}}`) usando dados do cliente (golden_record + features).

| Tipo | Fonte | Exemplo |
|---|---|---|
| Cadastro | golden_record | `{{nome}}`, `{{email}}`, `{{agencia}}` |
| Features | catalogo_caracteristicas | `{{renda_mensal}}`, `{{score_credito}}` |
| Campanha | contexto runtime | `{{campanha_nome}}`, `{{link_opt_out}}` |

Engine: Jinja2 (Python) com fallback para valor default quando variável ausente.

---

### 2.5 `core/mab.py` — Otimização Multi-Armed Bandit

Thompson Sampling para testes A/B com convergência automática.

```
  Configuração (config_otimizacao):
    metrica_alvo: 'abertura' | 'clique' | 'conversao'
    trafego_exploracao_pct: 10  (% reservado para explorar)
    min_envios_convergencia: 500
    confianca_convergencia: 0.95

  Ciclo (Job diário):
    1. Busca resultados por variante (otimizacao_resultado)
    2. Calcula posterior Beta(a=sucessos+1, b=fracassos+1)
    3. Amostra Thompson → gera pesos
    4. Verifica convergência (P(melhor) > 95%)
    5. Se convergiu → status='convergida', fixa vencedora
    6. Salva pesos em otimizacao_variante
    7. Registra snapshot em otimizacao_historico
```

---

### 2.6 `core/grafo_validator.py` — Validação de Jornadas

Valida o JSON do grafo React Flow em 8 etapas:

| # | Validação | Erro se falhar |
|---|---|---|
| 1 | Exatamente 1 nó `entrada` | "Jornada deve ter 1 nó de entrada" |
| 2 | Pelo menos 1 nó `saida` | "Jornada deve ter nó de saída" |
| 3 | Todos os nós conectáveis | "Nó {id} sem conexão" |
| 4 | Sem ciclos infinitos | "Ciclo detectado (sem limite)" |
| 5 | `enviar_peca` referencia peça existente | "Peça {id} não encontrada" |
| 6 | `condicao` tem ambas saídas (true/false) | "Condição sem branch" |
| 7 | `ab_split` tem >=2 variantes | "Split precisa de variantes" |
| 8 | `esperar` tem duração válida (>0) | "Espera com duração inválida" |

---

### 2.7 `core/security.py` — Autenticação + RBAC

```
  Request ──▶ Header X-Forwarded-Email ──▶ Lookup governanca.usuarios_perfil
                                              WHERE sistema = 'engagement'
                                                AND ativo = true
                                           ──▶ perfil: 'admin' | 'analista'

  require_perfil(["admin"])       → Decorator que valida acesso
  require_perfil(["admin","analista"]) → Aceita ambos
```

---

## 3. Data Layer — Padrões

### 3.1 Cliente SQL (databricks_client.py)

| Método | Uso |
|---|---|
| `fetch_all(sql, params)` | SELECT → list[tuple] |
| `fetch_one(sql, params)` | SELECT → tuple ou None |
| `execute_insert(sql, params)` | INSERT/UPDATE/DELETE |

**Regras:**
- SQL SEMPRE parametrizado (`?` placeholders para valores)
- Nomes de tabela via f-string (vindo de config.py, nunca de input)
- LIMIT via `{int(n)}` (bind param não suporta LIMIT no Databricks SQL)
- Booleanos: `true/false` (não `0/1`)

### 3.2 Fake Client (fake_client.py)

Implementação SQLite para desenvolvimento local/testes sem Databricks:

- `_normalize_sql()`: remove prefixos `plataforma.schema.`
- `_convert_params()`: `list` → `json.dumps()`, `bool` → `int()`
- `seed.py`: popula 33 tabelas + 3 views com dados reais para smoke test

---

## 4. Dependências entre Módulos

```
  api/campanha.py ──▶ core/config.py, core/security.py, db/
  api/jornada.py  ──▶ core/grafo_validator.py, core/config.py
  api/avulso.py   ──▶ core/orquestrador.py (validar_segmento_ativo)
  api/admin.py    ──▶ core/mab.py
  api/operacao.py ──▶ core/config.py

  core/orquestrador.py ──▶ core/config.py (todas as TABLE_*)
  core/motor_jornada.py ─▶ core/config.py, core/render_engine.py
  core/motor_disparo.py ─▶ core/config.py, core/render_engine.py, providers/
  core/mab.py ─────────▶ core/config.py (tabelas otimizacao_*)

  Jobs (notebooks) ────▶ core/orquestrador.py, core/motor_jornada.py,
                          core/motor_disparo.py, core/mab.py
```

---

## 5. Padrões e Convenções

| Padrão | Descrição |
|---|---|
| IDs | `uuid4().hex[:12]` com prefixo (cam\_, jor\_, pec\_, dav\_) |
| Códigos | `CAM-2025-CROSSSELL-00015` (auto-increment último-5-dígitos) |
| Timestamps | UTC sempre (`datetime.now(timezone.utc)`) |
| Responses | `{"data": {...}}` ou `{"data": [...]}` (envelope padrão) |
| Erros | HTTPException com detail textual |
| Logs | `logging.getLogger(__name__)` por módulo |
| Config | `os.getenv()` com defaults para local |
| Chunking | Queries IN com chunks de 500 (`WHERE x IN (?,?,...?)`) |

---

*Referência: src/ completo + DDLs validados em Agosto/2026.*
