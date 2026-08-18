# API REST — SegmentHub

> Referência completa dos endpoints. Base URL: `/api`

---

## Visão Geral dos Routers

```
  ┌───────────────────────────────────────────────────────────────────────────┐
  │  /api                                                                     │
  │                                                                           │
  │  Rota                               Acesso                                │
  │  ─────────────────────────────────   ────────────────────────────────   │
  │  /metadata/*                         ● analista + admin                   │
  │  /metadata/admin/*                   🔒 admin only                         │
  │  /segmentacoes/*                     ● analista + admin                   │
  │  /estimativa/*                       ● analista + admin                   │
  │  /segmentacoes/{id}/comentarios/*    ● analista + admin                   │
  │  /notificacoes/*                     ● analista + admin                   │
  │  /saude/*                            ● analista + admin                   │
  │  /chat/*                             ● analista + admin                   │
  │                                                                           │
  └───────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Metadata (Catálogo Público)

| Método | Rota | Descrição | Perfil |
|---|---|---|---|
| GET | `/api/metadata/temas` | Lista temas distintos (ordenados) | analista, admin |
| GET | `/api/metadata/temas/{tema}/campos` | Campos de um tema (ativo=true) | analista, admin |
| GET | `/api/metadata/campos/{campo_id}` | Detalhe de um campo | analista, admin |
| GET | `/api/metadata/publicos` | Públicos-base disponíveis | analista, admin |
| GET | `/api/metadata/campos-em-uso` | Campos referenciados por segs ativas | analista, admin |

**Nota:** Nenhum endpoint público expoe `usavel_em_peca`, `usavel_em_visao360`, `bloco_visao360`.

---

## 2. Metadata Admin (Governança de Catálogo)

| Método | Rota | Descrição | Perfil |
|---|---|---|---|
| GET | `/api/metadata/admin/campos` | Lista TODAS características (incl. inativas) + flags | admin |
| GET | `/api/metadata/admin/campos/{id}` | Detalhe completo + flags | admin |
| PUT | `/api/metadata/admin/campos/{id}/flags` | Altera flags S2/S3/bloco | admin |
| PUT | `/api/metadata/admin/campos/{id}/status` | Ativa/desativa globalmente | admin |
| GET | `/api/metadata/admin/historico` | Histórico geral de governança | admin |
| GET | `/api/metadata/admin/campos/{id}/historico` | Histórico por característica | admin |

### PUT `/api/metadata/admin/campos/{id}/flags`

**Request:**
```json
{
  "usavel_em_visao360": true,
  "usavel_em_peca": false,
  "bloco_visao360": "financeiro",
  "motivo": "Liberado para visão 360 após validação LGPD"
}
```

**Response:**
```json
{
  "ok": true,
  "alteracoes": [
    {"flag": "usavel_em_visao360", "de": "false", "para": "true"},
    {"flag": "bloco_visao360", "de": null, "para": "financeiro"}
  ]
}
```

**Regra:** `bloco_visao360` só aceito se `usavel_em_visao360=true` (422 caso contrário).

---

## 3. Segmentações (CRUD + Ciclo de Vida)

### CRUD

| Método | Rota | Descrição | Perfil |
|---|---|---|---|
| POST | `/api/segmentacoes` | Criar segmentação (rascunho) | analista, admin |
| GET | `/api/segmentacoes` | Listar com filtros e paginação | analista, admin |
| GET | `/api/segmentacoes/{seg_id}` | Detalhe completo | analista, admin |
| PUT | `/api/segmentacoes/{seg_id}` | Atualizar (se ativa → nova versão) | analista, admin |
| DELETE | `/api/segmentacoes/{seg_id}` | Arquivar (soft delete) | analista, admin |
| POST | `/api/segmentacoes/{seg_id}/clonar` | Clonar segmentação | analista, admin |

### Ciclo de Vida

| Método | Rota | Descrição | Perfil | Efeito |
|---|---|---|---|---|
| POST | `/{seg_id}/validar` | Validação completa | analista, admin | Verifica regras + estimativa |
| POST | `/{seg_id}/aprovar` | Aprovar (checklist) | **admin** | Cria Job + evento |
| POST | `/{seg_id}/ativar` | Ativar | analista, admin | Cria Job |
| POST | `/{seg_id}/pausar` | Pausar | analista, admin | Remove schedule |
| POST | `/{seg_id}/reativar` | Reativar | analista, admin | Restaura schedule |
| POST | `/{seg_id}/encerrar` | Encerrar | analista, admin | Deleta Job |
| POST | `/{seg_id}/executar` | Execução manual | analista, admin | Dispara run |

### Versões e Histórico

| Método | Rota | Descrição |
|---|---|---|
| GET | `/{seg_id}/versoes` | Lista versões |
| GET | `/{seg_id}/versoes/{versao}` | Regras de uma versão específica |
| GET | `/{seg_id}/execucoes` | Histórico de execuções |
| GET | `/{seg_id}/estados` | Histórico de transições |
| GET | `/{seg_id}/timeline` | Timeline unificada |

### Destinos e Vigência

| Método | Rota | Descrição |
|---|---|---|
| GET | `/{seg_id}/destinos` | Destinos atuais |
| PUT | `/{seg_id}/destinos` | Atualizar destinos (sistema2/sistema3) |
| PUT | `/{seg_id}/vigencia` | Atualizar vigência + cron |

### Parâmetros de Listagem (`GET /api/segmentacoes`)

| Parâmetro | Tipo | Descrição |
|---|---|---|
| `status` | string | Filtrar por status |
| `objetivo` | string | Filtrar por objetivo |
| `owner` | string | Filtrar por owner |
| `busca` | string | Busca textual (nome, código, tags) |
| `page` | int | Página (default: 1) |
| `size` | int | Itens/página (default: 50, max: 100) |

---

## 4. Estimativa

| Método | Rota | Descrição | Perfil |
|---|---|---|---|
| POST | `/api/estimativa/preview` | Estimativa de público (HyperLogLog) | analista, admin |

**Request:**
```json
{
  "publico_base": "pub_pf_ativos",
  "inclusao": {
    "operator": "AND",
    "rules": [
      {"campo_id": "renda_mensal", "op": ">=", "value": 5000},
      {"campo_id": "segmento", "op": "in", "value": ["uniclass", "private"]}
    ]
  },
  "exclusao": {
    "operator": "OR",
    "rules": [
      {"campo_id": "inadimplente", "op": "=", "value": true}
    ]
  }
}
```

**Response:**
```json
{
  "estimativa": 14832,
  "tempo_ms": 2100
}
```

**Nota:** Usa `approx_count_distinct` (HyperLogLog). Nunca retorna lista de CPFs.

---

## 5. Comentários e Notificações

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/segmentacoes/{seg_id}/comentarios` | Thread aninhada |
| POST | `/api/segmentacoes/{seg_id}/comentarios` | Novo comentário (menções → notificação) |
| PUT | `/api/comentarios/{id}` | Editar / marcar resolvido |
| GET | `/api/notificacoes` | Notificações do usuário |
| PUT | `/api/notificacoes/{id}/lida` | Marcar como lida |

---

## 6. Saúde e Overlap

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/saude` | Dashboard consolidado (todas) |
| GET | `/api/saude/{seg_id}` | Saúde detalhada + alertas |
| GET | `/api/overlap/{seg_id}` | Sobreposições do segmento |

---

## 7. Chat (IA)

| Método | Rota | Descrição |
|---|---|---|
| POST | `/api/chat/mensagem` | Enviar mensagem ao chatbot |

**Request:**
```json
{
  "mensagem": "Quero clientes com renda acima de 10k que não são inadimplentes",
  "contexto": {}
}
```

**Response:**
```json
{
  "resposta": "Montei uma segmentação com ~8.200 clientes...",
  "regras_json": { ... },
  "acao": "abrir_builder"
}
```

---

## 8. Utilitários

| Método | Rota | Descrição |
|---|---|---|
| GET | `/health` | Health check (sem auth) |
| GET | `/api/me` | Usuário atual (debug) |
| GET | `/api/debug-headers` | Visualizar headers (debug) |
| GET | `/api/test-db` | Testar conexão com banco |

---

## 9. Padrões de Resposta

### Sucesso (lista paginada)
```json
{
  "data": [...],
  "meta": {"page": 1, "size": 50, "total": 342}
}
```

### Erro de validação (422)
```json
{
  "detail": "Campo 'renda_mensal' não encontrado no catálogo."
}
```

### Erro de autorização (403)
```json
{
  "detail": "Acesso negado. Perfil 'analista' não permitido. Permitidos: ['admin']"
}
```

---

*Baseado nos routers reais em `/segmenthub/src/api/`.*