# S3 — Ciclo de Vida e Estados

> State machines das entidades principais do EngagementHub

---

## 1. Campanha

```
  ┌───────────┐    aprovar     ┌───────────┐    ativar     ┌─────────┐
  │ rascunho  │ ────────▶ │  aprovada │ ────────▶ │  ativa  │
  └─────┬─────┘               └───────────┘               └────┬────┘
        │                                                    │
        │ (editar)                               pausar │ encerrar
        ▼                                            ▼        │
  ┌───────────┐                              ┌──────────┐     │
  │ rascunho  │ (loop de edição)            │ pausada  │     │
  └───────────┘                              └────┬─────┘     │
                                                 │ reativar    │
                                                 ▼            ▼
                                           ┌─────────┐  ┌────────────┐
                                           │  ativa  │  │ encerrada  │
                                           └─────────┘  └────────────┘

  Automático (Guardião):
    ativa + vigencia_fim < now() → concluida
    ativa + envios_realizados >= limite_envios → concluida + alerta
```

### Transições

| De | Para | Trigger | Validação |
|---|---|---|---|
| rascunho | aprovada | `POST /aprovar` (admin) | Tem jornada válida |
| aprovada | ativa | `POST /ativar` (admin) | Tem vigência futura |
| ativa | pausada | `POST /pausar` (admin) | — |
| pausada | ativa | `POST /ativar` (admin) | Vigência ainda válida |
| ativa | encerrada | `POST /encerrar` (admin) | — |
| ativa | concluida | Job guardião | `vigencia_fim < now()` OU limite atingido |
| qualquer | encerrada | `POST /encerrar` (admin) | Força encerramento |

### Side-effects

| Transição | Efeito |
|---|---|
| → ativa | Jornadas vinculadas ficam disponíveis para orquestrador |
| → pausada | Orquestrador ignora jornadas da campanha |
| → encerrada | Todos clientes na jornada são movidos para saída |
| → concluida | Notificação criada + campanha_historico_estado |

---

## 2. Jornada

```
  ┌───────────┐   validar   ┌───────────┐   aprovar   ┌───────────┐   ativar   ┌─────────┐
  │ rascunho  │ ─────▶ │ validada  │ ─────▶ │ aprovada  │ ────▶ │  ativa  │
  └───────────┘             └───────────┘             └───────────┘            └────┬────┘
                                                                          │
                                                              pausar │ encerrar
                                                                ▼        │
                                                          ┌──────────┐   ▼
                                                          │ pausada  │ ┌────────────┐
                                                          └────┬─────┘ │ encerrada  │
                                                               │       └────────────┘
                                                               └─▶ ativa (reativar)
```

### Validação (`POST /validar` — 8 checks)

| # | Check | Resultado |
|---|---|---|
| 1 | Exatamente 1 nó `entrada` | PASS/FAIL |
| 2 | Pelo menos 1 nó `saida` | PASS/FAIL |
| 3 | Todos nós conectados | PASS/FAIL |
| 4 | Sem ciclos infinitos | PASS/FAIL |
| 5 | Peças referenciadas existem | PASS/FAIL |
| 6 | Condições têm ambas saídas | PASS/FAIL |
| 7 | AB split tem ≥2 variantes | PASS/FAIL |
| 8 | Esperas com duração > 0 | PASS/FAIL |

### Políticas (`config_jornada_politica`)

| Parâmetro | Valores | Efeito |
|---|---|---|
| `ao_sair_segmento` | continua / remove | O que fazer se CPF sai do seg S1 |
| `reentrada` | bloqueada / permitida / apos_dias | Permite re-ingresso? |
| `reentrada_dias` | INT | Dias mínimos entre saída e reentrada |
| `max_reentradas` | INT | Limite de vezes (NULL = infinito) |

---

## 3. Peça

```
  ┌───────────┐   submeter   ┌───────────────┐    aprovar    ┌───────────┐
  │ rascunho  │ ──────▶ │ em_aprovacao  │ ───────▶ │ aprovada  │
  └───────────┘              └───────┬───────┘               └───────────┘
       ▲                           │                          │
       │                    reprovar │                          │ arquivar
       │                           ▼                          ▼
       │                    ┌─────────────┐             ┌────────────┐
       └──────────────── │  reprovada  │             │ arquivada  │
         (corrigir)        └─────────────┘             └────────────┘
```

### Aprovação multi-etapa

| Campo | Descrição |
|---|---|
| `peca_aprovacao.aprovador` | Quem aprovou/reprovou |
| `peca_aprovacao.decisao` | aprovada / reprovada |
| `peca_aprovacao.motivo` | Justificativa (obrigatória se reprovada) |
| `peca_aprovacao.aprovado_em` | Timestamp |

### Versionamento

Cada edição cria nova versão em `peca_versao`:
- `versao` (INT auto-increment)
- `conteudo_html` (snapshot do body)
- `variaveis_usadas` (ARRAY extraidas do template)
- `alterado_por`, `alterado_em`

---

## 4. Disparo Avulso (DAV)

```
  ┌───────────┐   aprovar   ┌───────────┐   executar   ┌────────────┐
  │ rascunho  │ ─────▶ │ aprovado  │ ──────▶ │ executando │
  └─────┬─────┘             └───────────┘             └──────┬─────┘
        │                                                  │
   cancelar │                                         sucesso │ falha
        ▼                                              ▼        │
  ┌───────────┐                                  ┌───────────┐   ▼
  │ cancelado │                                  │ executado │ ┌───────┐
  └───────────┘                                  └───────────┘ │ falha │
                                                               └───────┘
```

### Fluxo de execução (`POST /{id}/executar`)

```
  1. Validar segmento ativo (S1) ───▶ 409 se inativo
  2. Carregar CPFs (seg_resultado_corrente)
  3. Filtrar consentimento (opt_out)
  4. Aplicar capping
  5. Enfileirar na fila_disparo
  6. Atualizar métricas: qtd_publico, qtd_elegivel, qtd_enviado
  7. Status → 'executado'
```

**Rollback:** Se validação falha após marcar 'executando', status volta para 'aprovado'.

---

## 5. Estado do Cliente na Jornada

```
  ┌───────────┐   motor processa   ┌─────────────┐   nó saída   ┌───────────┐
  │   ativo   │ ──────────▶ │  aguardando │ ──────▶ │ concluido │
  └─────┬─────┘                  └───────┬─────┘              └───────────┘
        │                           │
        │  sai do seg               │ timeout/evento
        ▼                           ▼
  ┌───────────┐               ┌───────────┐
  │   saiu    │               │   ativo   │ (avança para próximo nó)
  └───────────┘               └───────────┘
```

### Tabela `jornada_estado_cliente`

| Campo | Descrição |
|---|---|
| `no_atual` | ID do nó onde o cliente está agora |
| `status` | ativo / aguardando / concluido / saiu |
| `proxima_acao_em` | Quando o motor deve revisitar (espera/timeout) |
| `historico_nos` | ARRAY com todos os nós percorridos |
| `contexto_json` | Dados acumulados durante a jornada |

### Tabela `jornada_participacao` (consolidação)

| Campo | Descrição |
|---|---|
| `entrou_em` | Primeira entrada nesta jornada |
| `saiu_em` | NULL se ainda ativo |
| `status_final` | concluido / saiu_segmento / encerrado_admin |
| `vezes_participou` | Contador de reentradas |

---

## 6. Tracking (funil de envio)

```
  enviado ──▶ entregue ──▶ aberto ──▶ clicou ──▶ converteu
     │          │
     │          └─▶ bounce (hard/soft)
     │
     └─▶ falha (provider error / timeout)
```

| Status | Registrado por | Detalhe |
|---|---|---|
| enviado | motor_disparo | Provider aceitou a requisição |
| entregue | webhook (provider) | Confirmou entrega na caixa |
| aberto | pixel `/track/open/{id}.gif` | Imagem 1x1 carregada |
| clicou | redirect `/track/click/{id}` | Link trackado clicado |
| converteu | S2 retorno_atendimento / manual | Conversão real |
| bounce | webhook | Hard bounce (email inválido) |
| falha | motor_disparo | Provider rejeitou / timeout |

---

*State machines extraídas do código fonte e DDLs | Agosto/2026*
