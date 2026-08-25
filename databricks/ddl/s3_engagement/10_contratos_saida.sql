-- s3_engagement/10 - CONTRATOS DE SAÍDA para o S2 (decisões 3 e 6)
-- Depende de: 01_campanha, 05_jornadas. Consumido pelo ClientView 360 via GRANT SELECT.

-- DECISÃO 3 - Mapa segmento <-> campanha (Opção B).
-- Só existe linha quando o segmento (S1) foi usado numa jornada/campanha digital (S3).
-- Ponte: seg_id -> jornada.seg_entrada_id -> jornada.campanha_id -> campanha.
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
-- COMMENT lógico: mapeia quais campanhas digitais consumiram cada segmento.
-- S2 usa para, dado o seg_id (vindo do S1), descobrir a(s) campanha(s) do S3.

-- DECISÃO 6 - Status do cliente na jornada (contrato limpo para o S2).
-- Evita o S2 ler jornada_estado_cliente cru (desacoplamento).
-- Mostra ao gerente "até onde o cliente foi" na régua digital.
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
-- S2 cruza por cpf_cnpj (RLS aplicada no lado do S2 ao consultar via cliente).

-- GRANTs para o S2 (ClientView 360) consumir os contratos
-- Ajustar <S2_PRINCIPAL> para o Service Principal do S2 no deploy
GRANT SELECT ON VIEW plataforma.engagement.segmento_campanha_map TO `sp_clientview_s2`;
GRANT SELECT ON VIEW plataforma.engagement.cliente_jornada_status TO `sp_clientview_s2`;
GRANT SELECT ON TABLE plataforma.engagement.tracking_disparo TO `sp_clientview_s2`;
