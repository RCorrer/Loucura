-- s3_engagement/03 - Catálogo de canais (conectores plugáveis)
-- Depende de: s0_comum/01

CREATE TABLE IF NOT EXISTS plataforma.engagement.catalogo_canais (
  canal_id STRING NOT NULL,
  nome_exibicao STRING,
  icone STRING,
  suporta_html BOOLEAN,
  suporta_imagem BOOLEAN,
  suporta_botoes BOOLEAN,
  suporta_video BOOLEAN,
  max_caracteres INT,
  formato_editor STRING COMMENT 'rico_html/mensagem_simples/card',
  campos_obrigatorios ARRAY<STRING>,
  provider_class STRING COMMENT 'Classe Python do provider (EmailProvider/WhatsAppProvider)',
  rate_limit_por_segundo INT,
  rate_limit_por_dia INT,
  ativo BOOLEAN DEFAULT true,
  atualizado_em TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Descreve capacidades de cada canal. Adicionar canal = 1 provider + 1 linha aqui';