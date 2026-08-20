# S3 — API Endpoints

> 70 endpoints REST | FastAPI | Autenticação: Service Principal + RBAC

---

## 1. Visão Geral

| Módulo | Prefix | Endpoints | Perfil mínimo |
|---|---|---|---|
| Campanha | `/api/campanhas` | 9 | analista |
| Peça | `/api/pecas` | 10 | analista |
| Canal | `/api/canais` | 6 | admin |
| Jornada | `/api/jornadas` | 10 | analista |
| Orquestrador | `/api/orquestrador` | 4 | admin |
| Disparo | `/api/disparos` | 4 | analista |
| Tracking | `/track` + `/webhook` | 6 | público |
| Avulso (DAV) | `/api/avulso` | 6 | analista |
| Admin/MAB | `/api/admin` | 7 | admin |
| Operação | `/api/operacao` | 8 | analista |
| **Total** | | **70** | |

---

## 2. Campanhas (`/api/campanhas`)

| Método | Path | Descrição | Perfil |
|---|---|---|---|
| GET | `/` | Listar campanhas (filtro status, limit) | analista |
| GET | `/{id}` | Detalhe da campanha | analista |
| POST | `/` | Criar campanha (rascunho) | analista |
| PUT | `/{id}` | Editar campanha (se rascunho) | analista |
| POST | `/{id}/aprovar` | Aprovar (rascunho → aprovada) | admin |
| POST | `/{id}/ativar` | Ativar (aprovada → ativa) | admin |
| POST | `/{id}/pausar` | Pausar (ativa → pausada) | admin |
| POST | `/{id}/encerrar` | Encerrar (qualquer → encerrada) | admin |
| PUT | `/{id}/limite` | Atualizar limite_envios + alerta_pct | admin |

**State machine:** rascunho → em_aprovacao → aprovada → ativa → pausada → encerrada/concluida

---

## 3. Peças (`/api/pecas`)

| Método | Path | Descrição | Perfil |
|---|---|---|---|
| GET | `/variaveis` | Listar variáveis disponíveis (view) | analista |
| GET | `/` | Listar peças (filtro canal, tipo, status) | analista |
| GET | `/{id}` | Detalhe da peça + versão atual | analista |
| POST | `/` | Criar peça (rascunho) | analista |
| PUT | `/{id}` | Editar peça (body HTML/template) | analista |
| POST | `/{id}/submeter` | Submeter para aprovação | analista |
| POST | `/{id}/aprovar` | Aprovar peça | admin |
| POST | `/{id}/reprovar` | Reprovar com motivo | admin |
| POST | `/{id}/preview` | Renderizar preview com dados fake | analista |
| POST | `/assets` | Upload de asset (imagem) | analista |

**State machine:** rascunho → em_aprovacao → aprovada / reprovada → arquivada

---

## 4. Canais (`/api/canais`)

| Método | Path | Descrição | Perfil |
|---|---|---|---|
| GET | `/providers` | Listar providers disponíveis | admin |
| GET | `/` | Listar canais configurados | admin |
| GET | `/{id}` | Detalhe do canal | admin |
| POST | `/` | Criar canal (config + provider) | admin |
| PUT | `/{id}` | Editar configuração | admin |
| POST | `/{id}/health` | Executar health check do provider | admin |

---

## 5. Jornadas (`/api/jornadas`)

| Método | Path | Descrição | Perfil |
|---|---|---|---|
| GET | `/` | Listar jornadas (filtro campanha, status) | analista |
| GET | `/{id}` | Detalhe + grafo JSON | analista |
| POST | `/` | Criar jornada (rascunho) | analista |
| PUT | `/{id}` | Editar (grafo_json, configs) | analista |
| POST | `/{id}/validar` | Validar grafo (8 checks) | analista |
| POST | `/{id}/preview` | Simular percurso com CPF fake | analista |
| POST | `/{id}/aprovar` | Aprovar jornada | admin |
| POST | `/{id}/ativar` | Ativar (cria estado para entrantes) | admin |
| POST | `/{id}/pausar` | Pausar processamento | admin |
| POST | `/{id}/encerrar` | Encerrar + mover todos para saída | admin |

**State machine:** rascunho → validada → aprovada → ativa → pausada → encerrada

---

## 6. Orquestrador (`/api/orquestrador`)

| Método | Path | Descrição | Perfil |
|---|---|---|---|
| POST | `/executar` | Executa pipeline completo (6 etapas) | admin |
| GET | `/status` | Status da última execução | analista |
| GET | `/historico` | Histórico de execuções (limit) | analista |
| POST | `/simular` | Simula sem enfileirar (dry-run) | admin |

---

## 7. Disparos (`/api/disparos`)

| Método | Path | Descrição | Perfil |
|---|---|---|---|
| GET | `/fila` | Listar fila_disparo (filtro status, canal) | analista |
| GET | `/fila/{id}` | Detalhe de item na fila + tentativas | analista |
| POST | `/reprocessar` | Reprocessar itens com falha | admin |
| GET | `/metricas` | Métricas de disparo (enviados/falhas/retry) | analista |

---

## 8. Tracking (`/track` + `/webhook`)

| Método | Path | Descrição | Perfil |
|---|---|---|---|
| GET | `/track/open/{envio_id}.gif` | Pixel 1x1 (registra abertura) | público |
| GET | `/track/click/{envio_id}` | Redirect + registra clique | público |
| POST | `/webhook/email` | Callback do provider email | público |
| POST | `/webhook/whatsapp` | Callback Meta Cloud API | público |
| POST | `/track/conversao` | Registra conversão manual | admin |
| GET | `/track/funil/{campanha_id}` | Funil (enviado→entregue→aberto→clicou→converteu) | analista |

**Nota:** Endpoints de tracking são públicos (sem auth) — protegidos por token no envio_id.

---

## 9. Avulso — DAV (`/api/avulso`)

| Método | Path | Descrição | Perfil |
|---|---|---|---|
| POST | `/` | Criar DAV (rascunho) | analista |
| GET | `/` | Listar DAVs (filtro status) | analista |
| GET | `/{id}` | Detalhe + métricas | analista |
| POST | `/{id}/aprovar` | Aprovar DAV | admin |
| POST | `/{id}/executar` | Executar (valida seg + governança + enfileira) | admin |
| DELETE | `/{id}` | Cancelar (se não executado) | analista |

**State machine:** rascunho → aprovado → executando → executado / cancelado

**Validação pré-execução:** `validar_segmento_ativo()` — verifica seg_definicao.status + seg_destino

---

## 10. Admin / MAB (`/api/admin`)

| Método | Path | Descrição | Perfil |
|---|---|---|---|
| GET | `/config/otimizacao` | Ler config MAB ativa | admin |
| PUT | `/config/otimizacao` | Atualizar config MAB | admin |
| POST | `/mab/recalcular` | Forçar recálculo de pesos | admin |
| POST | `/mab/fixar` | Fixar variante vencedora (manual) | admin |
| GET | `/mab/historico` | Histórico de pesos/convergência | admin |
| PUT | `/config/capping` | Atualizar regras de capping | admin |
| PUT | `/config/janela` | Atualizar janela de envio | admin |

---

## 11. Operação (`/api/operacao`)

| Método | Path | Descrição | Perfil |
|---|---|---|---|
| GET | `/saude` | Status de saúde operacional (mais recente por escopo) | analista |
| POST | `/verificar` | Executar health check sob demanda | admin |
| GET | `/notificacoes` | Listar notificações (filtro severidade, lida) | analista |
| PUT | `/notificacoes/{id}/lida` | Marcar como lida | analista |
| POST | `/alertas` | Criar alerta manual | admin |
| GET | `/metricas` | Métricas consolidadas (hoje vs ontem) | analista |
| POST | `/pausar-automatico` | Pausar campanha por falha crítica | admin |
| GET | `/dashboard` | Dados para dashboard operacional | analista |

---

## 12. Padrões de Request/Response

### Response envelope padrão

```json
// Sucesso (item)
{"data": {"campanha_id": "cam_7a3bc1d2e4f0", "status": "ativa"}}

// Sucesso (lista)
{"data": [{...}, {...}]}

// Erro
HTTP 4xx {"detail": "Mensagem de erro legível"}
```

### Códigos HTTP utilizados

| Código | Uso |
|---|---|
| 200 | Sucesso (GET, PUT, POST ação) |
| 400 | Validação falhou (Pydantic, regra de negócio) |
| 403 | Perfil insuficiente (RBAC) |
| 404 | Entidade não encontrada |
| 409 | Conflito de estado (transição inválida, seg inativo) |

---

*70 endpoints documentados | Agosto/2026*
