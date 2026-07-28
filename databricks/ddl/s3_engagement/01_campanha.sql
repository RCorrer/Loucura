-- s3_engagement/01 - Campanha (topo da hierarquia) + versões + histórico + vínculo jornada
-- Depende de: s0_comum/01

CREATE TABLE IF NOT EXISTS plataforma.engagement.campanha (
  campanha_id STRING NOT NULL,
  campanha_codigo STRING COMMENT 'CAM-2025-CROSSSELL-00015',
  nome STRING,
  descricao STRING,
  objetivo STRING,
  tags ARRAY<STRING>,
  resumo STRING,
  objetivo_negocio STRING,
  observacoes STRING,
  owner STRING,
  area_responsavel STRING,
  email_contato STRING,
  criado_por STRING,
  criado_em TIMESTAMP DEFAULT current_timestamp(),
  status STRING DEFAULT 'rascunho' COMMENT 'rascunho/em_aprovacao/aprovada/ativa/pausada/encerrada/concluida',
  vigencia_inicio TIMESTAMP,
  vigencia_fim TIMESTAMP,
  aprovado_por STRING,
  aprovado_em TIMESTAMP,
  limite_envios BIGINT COMMENT 'NULL = ilimitado',
  alerta_pct_limite INT COMMENT 'Alerta ao aproximar do limite',
  envios_realizados BIGINT DEFAULT 0,
  versao_atual INT DEFAULT 1,
  atualizado_em TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Campanha: iniciativa de negócio (topo). Contém N jornadas';

CREATE TABLE IF NOT EXISTS plataforma.engagement.campanha_versao (
  campanha_id STRING NOT NULL,
  versao INT NOT NULL,
  snapshot_json STRING,
  alterado_por STRING,
  alterado_em TIMESTAMP DEFAULT current_timestamp(),
  motivo STRING
) USING DELTA
COMMENT 'Versões da campanha';

CREATE TABLE IF NOT EXISTS plataforma.engagement.campanha_historico_estado (
  hist_id STRING NOT NULL,
  campanha_id STRING NOT NULL,
  estado_anterior STRING,
  estado_novo STRING,
  motivo STRING,
  alterado_por STRING,
  alterado_em TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Auditoria de transições de estado da campanha';

CREATE TABLE IF NOT EXISTS plataforma.engagement.campanha_jornada (
  campanha_id STRING NOT NULL,
  jornada_id STRING NOT NULL,
  ordem INT,
  ativo BOOLEAN DEFAULT true
) USING DELTA
COMMENT 'Relação campanha (1) -> (N) jornadas';