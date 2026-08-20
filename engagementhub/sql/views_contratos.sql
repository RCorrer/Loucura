-- ==========================================================================
-- CONTRATOS DE SAÍDA S3 (EngagementHub) — Views para consumo externo
-- ==========================================================================
-- Consumidores: S2 (AtendimentoHub), S4 (Análise)
-- Deploy: executar no SQL Warehouse Serverless (catalog=plataforma)
-- BACK-13: validar views + GRANT SELECT
-- ==========================================================================

USE CATALOG plataforma;
USE SCHEMA engagement;

-- --------------------------------------------------------------------------
-- VIEW 1: segmento_campanha_map
-- Mapeia seg_id → campanha(s) digitais ativas
-- Consumidor: S2 (para saber quais campanhas estão rodando por segmento)
-- --------------------------------------------------------------------------
CREATE OR REPLACE VIEW segmento_campanha_map AS
SELECT
    j.seg_entrada_id                       AS seg_id,
    cj.campanha_id,
    c.campanha_codigo,
    c.nome                                 AS campanha_nome,
    c.status                               AS campanha_status,
    j.jornada_id,
    j.nome                                 AS jornada_nome,
    j.status                               AS jornada_status,
    j.canal_principal                      AS canal,
    c.vigencia_inicio,
    c.vigencia_fim
FROM campanha_jornada cj
INNER JOIN campanha c   ON c.campanha_id = cj.campanha_id
INNER JOIN jornada j    ON j.jornada_id = cj.jornada_id
WHERE c.status IN ('ativa', 'pausada')
  AND j.seg_entrada_id IS NOT NULL;

COMMENT ON VIEW segmento_campanha_map IS
  'Contrato S3→S2: mapeia segmentos para campanhas/jornadas digitais ativas';

-- --------------------------------------------------------------------------
-- VIEW 2: cliente_jornada_status
-- Posição atual de cada cliente nas jornadas
-- Consumidor: S2 (para evitar abordar cliente já em jornada ativa)
-- --------------------------------------------------------------------------
CREATE OR REPLACE VIEW cliente_jornada_status AS
SELECT
    ec.cpf_cnpj,
    ec.jornada_id,
    j.nome                                 AS jornada_nome,
    ec.no_atual_id,
    ec.status                              AS status_participacao,
    ec.entrou_em,
    ec.atualizado_em,
    jp.concluiu_em,
    jp.resultado
FROM jornada_estado_cliente ec
INNER JOIN jornada j ON j.jornada_id = ec.jornada_id
LEFT JOIN jornada_participacao jp
    ON jp.jornada_id = ec.jornada_id AND jp.cpf_cnpj = ec.cpf_cnpj
WHERE ec.status IN ('ativo', 'pausado', 'concluido');

COMMENT ON VIEW cliente_jornada_status IS
  'Contrato S3→S2: posição de cada cliente nas jornadas (evitar abordagem duplicada)';

-- --------------------------------------------------------------------------
-- VIEW 3: variaveis_disponiveis
-- Catálogo de variáveis disponíveis para personalização de peças
-- Consumidor: Frontend (editor de peças), S4 (analytics)
-- --------------------------------------------------------------------------
CREATE OR REPLACE VIEW variaveis_disponiveis AS
SELECT
    campo_id,
    campo_label,
    tipo_dado,
    descricao,
    tabela_origem,
    coluna_origem
FROM plataforma.metadata.catalogo_caracteristicas
WHERE ativo = 1;

COMMENT ON VIEW variaveis_disponiveis IS
  'Contrato S3→Frontend/S4: variáveis disponíveis para personalização';

-- ==========================================================================
-- GRANTs — Acesso para consumidores externos
-- ==========================================================================

-- S2 (AtendimentoHub) — Service Principal
GRANT SELECT ON VIEW plataforma.engagement.segmento_campanha_map
  TO `sp-s2-atendimentohub`;

GRANT SELECT ON VIEW plataforma.engagement.cliente_jornada_status
  TO `sp-s2-atendimentohub`;

GRANT SELECT ON TABLE plataforma.engagement.tracking_disparo
  TO `sp-s2-atendimentohub`;

GRANT SELECT ON TABLE plataforma.engagement.disparo_eventos
  TO `sp-s2-atendimentohub`;

-- S4 (Analytics) — Grupo
GRANT SELECT ON VIEW plataforma.engagement.segmento_campanha_map
  TO `grp-s4-analytics`;

GRANT SELECT ON VIEW plataforma.engagement.cliente_jornada_status
  TO `grp-s4-analytics`;

GRANT SELECT ON VIEW plataforma.engagement.variaveis_disponiveis
  TO `grp-s4-analytics`;

GRANT SELECT ON TABLE plataforma.engagement.tracking_disparo
  TO `grp-s4-analytics`;

GRANT SELECT ON TABLE plataforma.engagement.disparo_eventos
  TO `grp-s4-analytics`;

-- ==========================================================================
-- VALIDAÇÃO: queries de smoke test (executar após deploy)
-- ==========================================================================

-- Test 1: segmento_campanha_map retorna dados
-- SELECT COUNT(*) FROM segmento_campanha_map;

-- Test 2: cliente_jornada_status sem órfãos
-- SELECT * FROM cliente_jornada_status WHERE jornada_nome IS NULL;

-- Test 3: variaveis_disponiveis tem registros
-- SELECT COUNT(*) FROM variaveis_disponiveis;
