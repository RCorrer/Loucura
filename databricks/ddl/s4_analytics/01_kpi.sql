-- s4_analytics/01 — KPIs (definição configurável + valores calculados)
-- Depende de: s0_comum/01

CREATE TABLE IF NOT EXISTS plataforma.analytics.kpi_definicao (
  kpi_id STRING NOT NULL,
  nome STRING,
  descricao STRING,
  categoria STRING COMMENT 'segmentacao/campanha/peca/jornada/canal/atendimento',
  formula_json STRING COMMENT 'fonte + agregação (técnico define)',
  unidade STRING,
  formato STRING,
  meta_padrao DOUBLE,
  direcao_melhor STRING COMMENT 'maior_melhor/menor_melhor',
  ativo BOOLEAN DEFAULT true,
  criado_por STRING,
  atualizado_em TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Definição configurável de KPI. Valores pré-calculados por Job';

CREATE TABLE IF NOT EXISTS plataforma.analytics.kpi_valor (
  kpi_id STRING NOT NULL,
  escopo STRING COMMENT 'global/campanha/segmento/canal/etc',
  escopo_id STRING,
  periodo DATE,
  valor DOUBLE,
  meta DOUBLE,
  atingiu_meta BOOLEAN,
  calculado_em TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Valores de KPI por escopo/período (eficiência vs meta — não comparativo entre estratégias)';