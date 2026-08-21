-- s0_comum/03 - Barramento de eventos (contratos assíncronos entre sistemas)
-- Padrão: produtor grava processado=false; job consumidor lê e marca true.

-- Produzido pelo S1 (SegmentHub)
CREATE TABLE IF NOT EXISTS plataforma.eventos.seg_eventos (
  evento_id    STRING   NOT NULL,
  seg_id       STRING,
  exec_id      STRING,
  tipo_evento  STRING   COMMENT 'publicada/executada/aprovada/pausada/encerrada/reativada',
  destino      STRING,
  payload_json STRING,
  criado_em    TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Eventos do S1. Consumido por S3 (novo público) e S4 (acompanhamento)';

-- Produzido pelo S2 (ClientView 360)
CREATE TABLE IF NOT EXISTS plataforma.eventos.retorno_atendimento (
  evento_id    STRING   NOT NULL,
  interacao_id STRING,
  cpf_cnpj     STRING   NOT NULL,
  tipo_evento  STRING   COMMENT 'desfecho_oferta/nao_perturbe/atendimento_realizado/tent',
  campanha_id  STRING,
  canal        STRING,
  payload_json STRING,
  destino      STRING   COMMENT 'engagement/analytics/governanca',
  processado   BOOLEAN  DEFAULT false,
  criado_em    TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Eventos do S2. Consumido por S3 (conversão real), S4 (métricas), governanca (opt-out)';

-- Produzido pelo S3 (EngagementHub)
CREATE TABLE IF NOT EXISTS plataforma.eventos.disparo_eventos (
  evento_id    STRING   NOT NULL,
  tipo_evento  STRING   COMMENT 'disparo_realizado/entregue/aberto/clicou/campanha_ativa_concluida',
  cpf_cnpj     STRING,
  campanha_id  STRING,
  jornada_id   STRING,
  peca_id      STRING,
  canal        STRING,
  envio_id     STRING,
  payload_json STRING,
  destino      STRING   COMMENT 'clientview360/analytics',
  processado   BOOLEAN  DEFAULT false,
  criado_em    TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Eventos do S3. Consumido por S2 (engajamento) e S4 (KPIs)';