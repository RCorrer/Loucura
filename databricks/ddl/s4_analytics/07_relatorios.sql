-- s4_analytics/07 — Relatórios PDF gerados
-- Depende de: s0_comum/01. PDFs em Unity Catalog Volume.

CREATE TABLE IF NOT EXISTS plataforma.analytics.relatorio_gerado (
  relatorio_id STRING NOT NULL,
  tipo STRING COMMENT 'executivo/campanha',
  escopo_id STRING,
  periodo STRING,
  caminho_pdf STRING COMMENT 'Unity Catalog Volume',
  gerado_por STRING,
  gerado_em TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Registro de relatórios PDF gerados';