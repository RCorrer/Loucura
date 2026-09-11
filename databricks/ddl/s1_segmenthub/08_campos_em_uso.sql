-- ============================================================
-- DDL 08: plataforma.metadata.campos_em_uso
-- ============================================================
-- Tabela que registra quais características do catálogo estão
-- sendo usadas em segmentações ativas. Atualizada pelo job
-- seg_saude_consolidador ou por trigger no backend.
-- ============================================================

CREATE TABLE IF NOT EXISTS plataforma.metadata.campos_em_uso (
    campo_id            STRING      NOT NULL    COMMENT 'caracteristica_id do catálogo',
    qtd_segmentacoes_ativas INT     NOT NULL    COMMENT 'Quantidade de segmentações ativas usando este campo',
    segmentacoes        STRING                  COMMENT 'JSON array com IDs das segmentações que usam este campo',
    atualizado_em       TIMESTAMP               COMMENT 'Última atualização'
)
USING DELTA
COMMENT 'Campos do catálogo em uso por segmentações ativas'
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');
