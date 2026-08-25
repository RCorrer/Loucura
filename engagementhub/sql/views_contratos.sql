-- ==========================================================================
-- CONTRATOS DE SAÍDA S3 (EngagementHub) — Views para consumo externo
-- ==========================================================================
-- Alinhado com DDL oficial: databricks/ddl/s3_engagement/10_contratos_saida.sql
-- Consumidores: S2 (ClientView 360), S4 (CompassHub)
-- Deploy: executar no SQL Warehouse Serverless (catalog=plataforma)
-- ==========================================================================

USE CATALOG plataforma;
USE SCHEMA engagement;

-- --------------------------------------------------------------------------
-- VIEW 1: segmento_campanha_map (DECISÃO 3)
-- Mapeia seg_id → campanha(s) digitais
-- Ponte: seg_id → jornada.seg_entrada_id → jornada.campanha_id → campanha
-- --------------------------------------------------------------------------
CREATE OR REPLACE VIEW plataforma.engagement.segmento_campanha_map AS
SELECT DISTINCT
  j.seg_entrada_id AS seg_id,
  c.campanha_id,
  c.campanha_codigo,
  c.nome AS campanha_nome,
  c.objetivo AS campanha_objetivo,
  c.status AS campanha_status,
  j.jornada_id,
  j.jornada_codigo,
  j.nome AS jornada_nome
FROM plataforma.engagement.jornada j
JOIN plataforma.engagement.campanha c ON c.campanha_id = j.campanha_id
WHERE j.seg_entrada_id IS NOT NULL;

-- --------------------------------------------------------------------------
-- VIEW 2: cliente_jornada_status (DECISÃO 6)
-- Posição do cliente na jornada (contrato limpo para S2)
-- --------------------------------------------------------------------------
CREATE OR REPLACE VIEW plataforma.engagement.cliente_jornada_status AS
SELECT
  e.cpf_cnpj,
  e.jornada_id,
  j.jornada_codigo,
  j.nome AS jornada_nome,
  e.campanha_id,
  c.campanha_codigo,
  c.nome AS campanha_nome,
  e.no_atual,
  e.status AS status_jornada,
  e.entrou_em,
  e.ultimo_processamento,
  e.historico_nos,
  size(e.historico_nos) AS qtd_nos_percorridos
FROM plataforma.engagement.jornada_estado_cliente e
JOIN plataforma.engagement.jornada j ON j.jornada_id = e.jornada_id
LEFT JOIN plataforma.engagement.campanha c ON c.campanha_id = e.campanha_id;

-- --------------------------------------------------------------------------
-- VIEW 3: variaveis_disponiveis (contrato com S1/metadata)
-- --------------------------------------------------------------------------
CREATE OR REPLACE VIEW plataforma.engagement.variaveis_disponiveis AS
SELECT caracteristica_id AS campo_id, campo_label, tipo_dado, descricao
FROM plataforma.metadata.catalogo_caracteristicas
WHERE ativo = true AND sensibilidade = 'normal' AND usavel_em_peca = true;

-- ==========================================================================
-- GRANTs — Acesso para S2 (ClientView 360)
-- ==========================================================================
GRANT SELECT ON VIEW plataforma.engagement.segmento_campanha_map TO `sp_clientview_s2`;
GRANT SELECT ON VIEW plataforma.engagement.cliente_jornada_status TO `sp_clientview_s2`;
GRANT SELECT ON TABLE plataforma.engagement.tracking_disparo TO `sp_clientview_s2`;

-- ==========================================================================
-- VALIDAÇÃO (smoke test após deploy)
-- ==========================================================================
-- SELECT COUNT(*) FROM plataforma.engagement.segmento_campanha_map;
-- SELECT * FROM plataforma.engagement.cliente_jornada_status WHERE jornada_nome IS NULL;
-- SELECT COUNT(*) FROM plataforma.engagement.variaveis_disponiveis;
