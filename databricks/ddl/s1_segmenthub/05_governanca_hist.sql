-- DDL COMPLEMENTAR — Governança de Catálogo (histórico auditável)
-- Anexar ao s1_segmenthub/01_metadata.sql ou criar como arquivo separado

CREATE TABLE IF NOT EXISTS plataforma.metadata.catalogo_governanca_hist (
    hist_id           STRING NOT NULL,
    caracteristica_id STRING NOT NULL,
    campo_label       STRING,
    flag_alterada     STRING NOT NULL,   -- 'usavel_em_visao360' | 'usavel_em_peca' | 'bloco_visao360' | 'ativo'
    sistema_alvo      STRING,            -- 's2' | 's3' | 'global'
    valor_anterior    STRING,
    valor_novo        STRING NOT NULL,
    acao              STRING NOT NULL,   -- 'liberou' | 'retirou' | 'alterou_bloco'
    alterado_por      STRING NOT NULL,
    alterado_em       TIMESTAMP NOT NULL
) USING DELTA
CLUSTER BY (caracteristica_id)
TBLPROPERTIES ('delta.autoOptimize.optimizeWrite' = 'true')
COMMENT 'Histórico de governança do catálogo: quem liberou/retirou acesso de característica ao S2/S3 e quando';