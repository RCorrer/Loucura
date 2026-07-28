-- s3_engagement/08 - Otimização MAB (Thompson Sampling)
-- Depende de: s0_comum/01

CREATE TABLE IF NOT EXISTS plataforma.engagement.config_otimizacao (
  config_id STRING NOT NULL,
  escopo STRING COMMENT 'global/por_jornada',
  metrica_alvo STRING COMMENT 'abertura/clique/conversao/custom',
  metrica_custom_json STRING,
  janela_avaliacao_horas INT,
  trafego_minimo_pct DOUBLE COMMENT 'Garante exploração (não mata variante cedo)',
  min_amostras_por_variante INT,
  frequencia_recalculo STRING COMMENT 'diario na POC',
  otimizacao_ativa BOOLEAN COMMENT 'false = pesos manuais',
  ativo BOOLEAN DEFAULT true,
  atualizado_por STRING,
  atualizado_em TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Config do MAB (global + por jornada)';

CREATE TABLE IF NOT EXISTS plataforma.engagement.otimizacao_variante (
  variante_id STRING NOT NULL,
  jornada_id STRING,
  no_id STRING COMMENT 'Nó A/B Split',
  peca_id STRING,
  rotulo STRING,
  peso_atual DOUBLE,
  ativo BOOLEAN DEFAULT true,
  criado_em TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Variantes de teste A/B (arms do bandit)';

CREATE TABLE IF NOT EXISTS plataforma.engagement.otimizacao_resultado (
  variante_id STRING NOT NULL,
  janela TIMESTAMP,
  envios BIGINT,
  aberturas BIGINT,
  cliques BIGINT,
  conversoes BIGINT,
  taxa_metrica_alvo DOUBLE,
  atualizado_em TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Resultado acumulado por variante (alimenta o cálculo)';

CREATE TABLE IF NOT EXISTS plataforma.engagement.otimizacao_historico (
  hist_id STRING NOT NULL,
  variante_id STRING,
  jornada_id STRING,
  peso_anterior DOUBLE,
  peso_novo DOUBLE,
  motivo STRING,
  recalculado_em TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Evolução dos pesos (transparência do MAB)';