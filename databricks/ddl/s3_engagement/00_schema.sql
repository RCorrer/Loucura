-- s3_engagement/00 - Schema + barramento de eventos
-- Executar PRIMEIRO, antes de qualquer outro DDL do S3.
-- Depende de: catálogo 'plataforma' existir (criado pelo S0).

-- Schema principal do EngagementHub
CREATE SCHEMA IF NOT EXISTS plataforma.engagement
COMMENT 'Marketing Cloud: campanhas, jornadas, peças, disparos, tracking, MAB';

-- Schema de eventos (barramento entre sistemas)
-- Se o S0 já cria este schema, remover daqui.
CREATE SCHEMA IF NOT EXISTS plataforma.eventos
COMMENT 'Barramento de eventos entre sistemas (S1↔S3, S3→S2, S3→S4)';

-- Tabela de eventos (usada por _emitir_evento em campanha/jornada/disparo)
CREATE TABLE IF NOT EXISTS plataforma.eventos.disparo_eventos (
  evento_id STRING NOT NULL,
  tipo_evento STRING COMMENT 'campanha_ativada/campanha_concluida/disparo_finalizado/jornada_encerrada',
  entidade_tipo STRING COMMENT 'campanha/jornada/disparo',
  entidade_id STRING,
  payload_json STRING,
  emitido_por STRING,
  emitido_em TIMESTAMP DEFAULT current_timestamp(),
  processado BOOLEAN DEFAULT false
) USING DELTA
CLUSTER BY (processado, tipo_evento)
COMMENT 'Barramento de eventos assíncrono. Producers: S3 (engagement). Consumers: jobs S3/S4';
