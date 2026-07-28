-- s3_engagement/07 - Tracking do funil (contrato consumido por S2 e S4)
-- Depende de: s0_comum/01
CREATE TABLE IF NOT EXISTS plataforma.engagement.tracking_disparo (
  envio_id STRING NOT NULL COMMENT 'Único (idempotência)',
  cpf_cnpj STRING,
  campanha_id STRING,
  jornada_id STRING,
  peca_id STRING,
  canal STRING,
  enviado_em TIMESTAMP,
  entregue_em TIMESTAMP,
  visualizado_em TIMESTAMP,
  aberto_em TIMESTAMP,
  clicou_em TIMESTAMP,
  converteu_em TIMESTAMP COMMENT 'Preenchido por evento desfecho_oferta (S2): conversão real',
  status_atual STRING COMMENT 'enviado/entregue/visualizado/aberto/clicou/converteu/falha',
  erro_detalhe STRING,
  provider_message_id STRING,
  atualizado_em TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
CLUSTER BY (cpf_cnpj)
COMMENT 'Funil por envio. CONTRATO: lido por S2 (engajamento) e S4 (KPIs). converteu_em vem do S2';