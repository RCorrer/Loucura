-- s4_analytics/02 — OKRs (objetivos + key results + vínculo com campanhas)
-- Depende de: s0_comum/01

CREATE TABLE IF NOT EXISTS plataforma.analytics.okr_objetivo (
  objetivo_id STRING NOT NULL,
  titulo STRING,
  descricao STRING,
  periodo STRING COMMENT 'trimestral/anual',
  periodo_inicio DATE,
  periodo_fim DATE,
  owner STRING,
  area STRING,
  status STRING COMMENT 'ativo/concluido/cancelado',
  criado_por STRING,
  criado_em TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Objetivo (qualitativo) do OKR';

CREATE TABLE IF NOT EXISTS plataforma.analytics.okr_keyresult (
  kr_id STRING NOT NULL,
  objetivo_id STRING NOT NULL,
  descricao STRING,
  metrica STRING,
  valor_meta DOUBLE,
  valor_atual DOUBLE,
  unidade STRING,
  progresso_pct DOUBLE,
  atualizacao STRING COMMENT 'automatica (via kpi)/manual',
  kpi_vinculado STRING COMMENT 'kpi_id se automática',
  atualizado_em TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Key Result (mensurável). Automático via KPI ou manual';

CREATE TABLE IF NOT EXISTS plataforma.analytics.okr_campanha (
  objetivo_id STRING NOT NULL,
  campanha_id STRING NOT NULL,
  contribricao_descricao STRING
) USING DELTA
COMMENT 'Vínculo OKR <-> campanha (rastreabilidade da contribuição)';