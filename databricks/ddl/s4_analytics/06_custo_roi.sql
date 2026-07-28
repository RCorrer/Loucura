-- s4_analytics/06 — Custo/ROI (inventado na POC, pronto p/ dado real)
-- Depende de: s0_comum/01

CREATE TABLE IF NOT EXISTS plataforma.analytics.custo_canal (
  canal STRING NOT NULL,
  custo_por_envio DOUBLE,
  custo_por_conversao DOUBLE,
  moeda STRING,
  vigencia_inicio DATE,
  vigencia_fim DATE,
  fonte STRING COMMENT 'manual_poc/automatico',
  atualizado_por STRING,
  atualizado_em TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Custo por canal (futuro: preço real da API Meta por envio)';

CREATE TABLE IF NOT EXISTS plataforma.analytics.valor_conversao (
  tipo_conversao STRING NOT NULL COMMENT 'cartao/investimento/seguro',
  valor_medio DOUBLE,
  moeda STRING,
  fonte STRING,
  atualizado_em TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Valor médio por tipo de conversão (base do cálculo de ROI)';