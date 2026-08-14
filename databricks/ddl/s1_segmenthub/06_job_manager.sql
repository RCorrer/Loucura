-- ============================================================
-- S1 SegmentHub — DDL para arquitetura Job-per-Segment
-- ============================================================
-- Adiciona suporte ao gerenciamento de jobs individuais por segmentação.
-- Cada segmentação ativa possui seu próprio Databricks Job.
-- ============================================================

-- 1. Coluna para armazenar o ID do Job no Databricks
ALTER TABLE plataforma.segmentacao.seg_definicao
ADD COLUMN IF NOT EXISTS job_id_databricks STRING
COMMENT 'ID do Databricks Job criado para esta segmentação (preenchido pelo JobManagerService)';

-- 2. Tabela de log de operações do Job Manager (auditoria)
CREATE TABLE IF NOT EXISTS plataforma.segmentacao.seg_job_log (
  log_id          STRING    NOT NULL COMMENT 'ID único do log',
  seg_id          STRING    NOT NULL COMMENT 'FK para seg_definicao',
  acao            STRING    NOT NULL COMMENT 'criar|pausar|reativar|deletar|executar|atualizar_schedule',
  job_id          STRING             COMMENT 'Databricks Job ID',
  run_id          STRING             COMMENT 'Run ID (quando execução manual)',
  status          STRING    NOT NULL COMMENT 'sucesso|erro',
  detalhes        STRING             COMMENT 'Mensagem de erro ou detalhes adicionais (JSON)',
  executado_por   STRING             COMMENT 'Usuário que disparou a ação',
  criado_em       TIMESTAMP NOT NULL DEFAULT current_timestamp()
)
COMMENT 'Log de auditoria de todas as operações do JobManagerService'
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');

-- 3. Índices para consultas frequentes
-- (Delta Lake não suporta CREATE INDEX, mas otimizamos com ZORDER)
-- OPTIMIZE plataforma.segmentacao.seg_job_log ZORDER BY (seg_id, criado_em);
