-- ============================================================
-- Migration: Remoção do Step 4 (Metadados) da seg_definicao
-- Data: 2026-08-31
-- Ticket: Remoção do step "Metadados" do Builder de Segmentação
--
-- Campos removidos (9 colunas):
--   seg_tags, resumo, objetivo_negocio, publico_alvo_descricao,
--   observacoes, documentacao_md, email_contato, tipo
--
-- Impacto:
--   Frontend:  BuilderSegmentacao, DetalheSegmentacao, DocumentacaoSegmentacao
--   Backend:   segmentacao_dto, segmentacao_service, segmentacao_repository
--   Jobs:      job_manager_service, seg_saude_consolidador, JOBS_MANIFEST
--   Doc:       02-SCHEMAS-TABELAS.md
--
-- ATENÇÃO: DROP COLUMN em Delta é irreversível. Faça backup antes.
--          Requer delta.minReaderVersion >= 2, delta.minWriterVersion >= 5.
-- ============================================================

-- Passo 1: Backup de segurança (opcional — descomente se necessário)
-- CREATE TABLE plataforma.segmentacao.seg_definicao_bkp_20260831
-- AS SELECT * FROM plataforma.segmentacao.seg_definicao;

-- Passo 2: Remover colunas do Step 4 (Metadados)
ALTER TABLE plataforma.segmentacao.seg_definicao DROP COLUMN seg_tags;
ALTER TABLE plataforma.segmentacao.seg_definicao DROP COLUMN resumo;
ALTER TABLE plataforma.segmentacao.seg_definicao DROP COLUMN objetivo_negocio;
ALTER TABLE plataforma.segmentacao.seg_definicao DROP COLUMN publico_alvo_descricao;
ALTER TABLE plataforma.segmentacao.seg_definicao DROP COLUMN observacoes;
ALTER TABLE plataforma.segmentacao.seg_definicao DROP COLUMN documentacao_md;
ALTER TABLE plataforma.segmentacao.seg_definicao DROP COLUMN email_contato;
ALTER TABLE plataforma.segmentacao.seg_definicao DROP COLUMN tipo;

-- Passo 3: Verificação pós-migration
DESCRIBE TABLE plataforma.segmentacao.seg_definicao;

-- Passo 4: Atualizar DDL base (02_segmentacao.sql) para refletir o novo schema
-- A definição CREATE TABLE em 02_segmentacao.sql deve ser atualizada manualmente
-- para remover as 8 colunas, mantendo consistência entre DDL e banco.
