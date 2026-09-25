-- ============================================================
-- 08_governanca_acesso.sql
-- Tabela de perfis de acesso + View de campos em uso
-- Dependências de security.py e metadata_repository.py
-- ============================================================

-- Schema de governança (se não existir)
CREATE SCHEMA IF NOT EXISTS plataforma.governanca;

-- Tabela de perfis de acesso (usada por security.py para RBAC)
CREATE TABLE IF NOT EXISTS plataforma.governanca.usuarios_perfil (
    usuario_id    STRING    NOT NULL COMMENT 'Email do usuário',
    sistema       STRING    NOT NULL COMMENT 'Sistema: segmenthub | engagementhub | clientview',
    perfil        STRING    NOT NULL COMMENT 'Perfil de acesso: admin | analista',
    ativo         BOOLEAN   DEFAULT true COMMENT 'Se o acesso está ativo',
    criado_em     TIMESTAMP DEFAULT current_timestamp(),
    atualizado_em TIMESTAMP DEFAULT current_timestamp()
)
USING DELTA
COMMENT 'Perfis de acesso dos usuários aos sistemas da plataforma'
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');

-- View de campos em uso em segmentações ativas
-- Extrai campo_id de regras_json (árvore recursiva) via regex
CREATE OR REPLACE VIEW plataforma.metadata.campos_em_uso AS
WITH campos_raw AS (
    SELECT
        seg_id,
        nome,
        regexp_extract_all(regras_json, '"campo_id"\\s*:\\s*"([^"]+)"', 1) AS campo_ids
    FROM plataforma.segmentacao.seg_definicao
    WHERE status = 'ativa'
      AND habilitado = true
      AND regras_json IS NOT NULL
),
campos_exploded AS (
    SELECT seg_id, nome, explode(campo_ids) AS campo_id
    FROM campos_raw
)
SELECT
    campo_id,
    COUNT(DISTINCT seg_id) AS qtd_segmentacoes_ativas,
    collect_list(DISTINCT nome) AS segmentacoes
FROM campos_exploded
GROUP BY campo_id;
