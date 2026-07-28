-- s3_engagement/09 - Operação: saúde + notificações
-- Depende de: s0_comum/01

CREATE TABLE IF NOT EXISTS plataforma.engagement.saude_operacional (
  metrica_id STRING NOT NULL,
  escopo STRING,
  valor DOUBLE,
  status STRING COMMENT 'verde/amarelo/vermelho',
  detalhe STRING,
  ultima_verificacao TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Health checks operacionais (filas travadas, rate limit, falhas)';

CREATE TABLE IF NOT EXISTS plataforma.engagement.notificacao (
  notif_id STRING NOT NULL,
  destinatario STRING,
  tipo STRING,
  entidade_tipo STRING,
  entidade_id STRING,
  titulo STRING,
  mensagem STRING,
  severidade STRING COMMENT 'info/alerta/critico',
  lida BOOLEAN DEFAULT false,
  criado_em TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Notificações/alertas operacionais in-app do S3';