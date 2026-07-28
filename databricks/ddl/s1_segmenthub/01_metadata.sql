-- s1_segmenthub/01 - Catálogos no-code (metadata)
-- Depende de: s0_comum/01 (schemas)

CREATE TABLE IF NOT EXISTS plataforma.metadata.catalogo_caracteristicas (
  caracteristica_id STRING        NOT NULL COMMENT 'ID do campo (campo_id)',
  tema              STRING        NOT NULL COMMENT 'Tema de agrupamento no menu',
  tema_ordem        INT,
  tabela_fisica     STRING        NOT NULL,
  tabela_label      STRING,
  campo_fisico      STRING        NOT NULL,
  campo_label       STRING,
  tipo_dado         STRING        NOT NULL COMMENT 'numeric/categorical/date/boolean',
  operadores        ARRAY<STRING> COMMENT 'Operadores válidos (inclui negação)',
  valores_dominio   ARRAY<STRING> COMMENT 'Domínio de valores (se categórico)',
  join_key          STRING        COMMENT 'cpf_cnpj',
  sensibilidade     STRING        COMMENT 'normal/sensível/lgpd',
  usavel_em_peca    BOOLEAN       COMMENT 'Flag consumida pelo S3 (variável de peça)',
  usavel_em_visao360 BOOLEAN      COMMENT 'Flag consumida pelo S2 (campo na Visão 360)',
  bloco_visao360    STRING        COMMENT 'Bloco sugerido p/ S2: cadastral/financeiro/produtos/comportamento',
  ativo             BOOLEAN,
  descricao         STRING
) USING DELTA
COMMENT 'Mapeia campo amigável -> coluna física (RuleBuilder). Hospeda flags de outros sistemas (desacoplado)';

CREATE TABLE IF NOT EXISTS plataforma.metadata.catalogo_publicos (
  publico_id     STRING   NOT NULL,
  nome           STRING,
  descricao      STRING,
  tabela_fisica  STRING   NOT NULL,
  criado_por_time STRING,
  ativo          BOOLEAN
) USING DELTA
COMMENT 'Públicos-base pré-definidos (ponto de partida da segmentação)';

-- View: campos em uso por segmentações ativas (proteção de metadado).
-- Extrai todos os campo_id do regras_json via regex (árvore aninhada, sem schema fixo).
CREATE OR REPLACE VIEW plataforma.metadata.campos_em_uso AS
WITH defs AS (
  SELECT seg_id, seg_codigo, status,
         regexp_extract_all(regras_json, '"campo_id"\s*:\s*"([^"]+)"', 1) AS campos
  FROM plataforma.segmentacao.seg_definicao
  WHERE status IN ('ativa', 'pausada', 'agendada')
),
exploded AS (
  SELECT seg_id, seg_codigo, explode(campos) AS campo_id FROM defs
)
SELECT campo_id,
       COUNT(DISTINCT seg_id)     AS qtd_segmentacoes_ativas,
       collect_list(DISTINCT seg_codigo) AS segmentacoes
FROM exploded
GROUP BY campo_id;