-- s4_analytics/04 — Insights visuais (Opção 1: sistema mostra, humano decide)
-- Depende de: s0_comum/01

CREATE TABLE IF NOT EXISTS plataforma.analytics.insight (
  insight_id STRING NOT NULL,
  tipo STRING COMMENT 'melhor_segmento/melhor_canal/melhor_peca/alto_abandono',
  titulo STRING,
  descricao STRING,
  entidade_tipo STRING,
  entidade_id STRING,
  metrica_valor DOUBLE,
  relevancia INT,
  gerado_em TIMESTAMP DEFAULT current_timestamp(),
  valido_ate TIMESTAMP
) USING DELTA
COMMENT 'Descobertas do sistema (não voltam automaticamente aos outros — humano decide)';
