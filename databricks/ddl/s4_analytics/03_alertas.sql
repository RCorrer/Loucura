-- s4_analytics/03 — Alertas de KPI (regras configuráveis + disparados)
-- Depende de: s0_comum/01, 01_kpi

CREATE TABLE IF NOT EXISTS plataforma.analytics.alerta_regra (
  regra_id STRING NOT NULL,
  kpi_id STRING COMMENT 'KPI monitorado',
  escopo STRING,
  condicao STRING COMMENT 'menor_que/maior_que/variou_mais_que',
  limite DOUBLE,
  severidade STRING COMMENT 'info/alerta/critico',
  ativo BOOLEAN DEFAULT true,
  criado_por STRING,
  atualizado_em TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Regra de alerta configurável pelo admin';

CREATE TABLE IF NOT EXISTS plataforma.analytics.alerta_disparado (
  alerta_id STRING NOT NULL,
  regra_id STRING,
  kpi_id STRING,
  escopo_id STRING,
  valor_atual DOUBLE,
  limite DOUBLE,
  mensagem STRING,
  lida BOOLEAN DEFAULT false,
  disparado_em TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Alertas efetivamente disparados (in-app)';