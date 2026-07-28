-- s4_analytics/05 — Tabelas agregadas (pré-cálculo p/ dashboards + funil)
-- Populadas por Job agregador_analytics (batch 1h). Depende de: s0_comum/01

CREATE TABLE IF NOT EXISTS plataforma.analytics.funil_campanha (
  campanha_id STRING NOT NULL,
  periodo DATE,
  enviados BIGINT,
  entregues BIGINT,
  abertos BIGINT,
  clicaram BIGINT,
  converteram BIGINT,
  taxa_entrega DOUBLE,
  taxa_abertura DOUBLE,
  taxa_clique DOUBLE,
  taxa_conversao DOUBLE,
  calculado_em TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Funil por campanha/período (onde a campanha perde clientes)';

CREATE TABLE IF NOT EXISTS plataforma.analytics.performance_campanha (
  campanha_id STRING NOT NULL,
  periodo DATE,
  publico_total BIGINT,
  alcance BIGINT,
  conversoes BIGINT,
  custo_estimado DOUBLE,
  roi DOUBLE,
  por_canal_json STRING,
  calculado_em TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Performance da campanha (inclui ROI)';

CREATE TABLE IF NOT EXISTS plataforma.analytics.performance_peca (
  peca_id STRING NOT NULL,
  periodo DATE,
  envios BIGINT,
  aberturas BIGINT,
  cliques BIGINT,
  conversoes BIGINT,
  calculado_em TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Performance por peça (qual conteúdo converte mais)';

CREATE TABLE IF NOT EXISTS plataforma.analytics.performance_jornada (
  jornada_id STRING NOT NULL,
  periodo DATE,
  entraram BIGINT,
  concluiram BIGINT,
  abandono_por_no_json STRING,
  calculado_em TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Performance por jornada (abandono por passo)';

CREATE TABLE IF NOT EXISTS plataforma.analytics.performance_segmento (
  seg_id STRING NOT NULL,
  periodo DATE,
  tamanho BIGINT,
  usado_em_campanhas INT,
  conversao_media DOUBLE,
  calculado_em TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Performance por segmento. Pode cruzar com seg_destino (S1) como atributo de contexto';