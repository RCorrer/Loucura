-- s3_engagement/04 - Peças + versões + aprovação + templates WhatsApp + assets
-- Depende de: s0_comum/01, metadata.catalogo_caracteristicas (S1)

CREATE TABLE IF NOT EXISTS plataforma.engagement.peca (
  peca_id STRING NOT NULL,
  peca_codigo STRING COMMENT 'PEC-2025-EMAIL-00087 (canal no código)',
  nome STRING,
  descricao STRING,
  canal STRING,
  tags ARRAY<STRING>,
  conteudo_json STRING COMMENT 'Estrutura do editor (GrapesJS/mensagem)',
  html_renderizado STRING,
  assunto STRING COMMENT 'Email',
  template_meta_id STRING COMMENT 'WhatsApp HSM',
  variaveis_usadas ARRAY<STRING>,
  status_aprovacao STRING COMMENT 'rascunho/em_aprovacao/aprovada/reprovada',
  aprovado_por STRING,
  aprovado_em TIMESTAMP,
  motivo_reprovacao STRING,
  criado_por STRING,
  criado_em TIMESTAMP DEFAULT current_timestamp(),
  owner STRING,
  area_responsavel STRING,
  versao_atual INT DEFAULT 1,
  atualizado_em TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Peça (arma). Reutilizável entre campanhas. Versionada';

CREATE TABLE IF NOT EXISTS plataforma.engagement.peca_versao (
  peca_id STRING NOT NULL,
  versao INT NOT NULL,
  conteudo_json STRING,
  html_renderizado STRING,
  alterado_por STRING,
  alterado_em TIMESTAMP DEFAULT current_timestamp(),
  motivo STRING
) USING DELTA
COMMENT 'Versões da peça';

CREATE TABLE IF NOT EXISTS plataforma.engagement.peca_aprovacao (
  aprovacao_id STRING NOT NULL,
  peca_id STRING NOT NULL,
  versao INT,
  etapa STRING COMMENT 'conteudo/compliance/juridico/marca (multi-etapa futura)',
  perfil_aprovador STRING,
  status STRING COMMENT 'pendente/aprovado/reprovado',
  aprovado_por STRING,
  aprovado_em TIMESTAMP,
  comentario STRING
) USING DELTA
COMMENT 'Aprovação individual da peça. Estrutura pronta p/ múltiplas etapas';

CREATE TABLE IF NOT EXISTS plataforma.engagement.whatsapp_templates (
  template_id STRING NOT NULL,
  template_meta_id STRING COMMENT 'ID aprovado na Meta',
  nome STRING,
  categoria STRING,
  corpo STRING,
  variaveis_posicionais ARRAY<STRING>,
  status_meta STRING COMMENT 'submetido/aprovado/rejeitado',
  submetido_em TIMESTAMP,
  aprovado_em TIMESTAMP
) USING DELTA
COMMENT 'Templates HSM do WhatsApp (aprovação pela Meta leva horas/dias)';

CREATE TABLE IF NOT EXISTS plataforma.engagement.asset (
  asset_id STRING NOT NULL,
  nome STRING,
  tipo STRING COMMENT 'imagem/logo/banner',
  caminho_volume STRING COMMENT 'Unity Catalog Volume',
  tags ARRAY<STRING>,
  tamanho_kb INT,
  criado_por STRING,
  criado_em TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Asset manager (imagens) em Unity Catalog Volumes';

-- Variáveis disponíveis p/ personalização: só normal + usavel_em_peca (contrato com S1)
CREATE OR REPLACE VIEW plataforma.engagement.variaveis_disponiveis AS
SELECT caracteristica_id AS campo_id, campo_label, tipo_dado, descricao
FROM plataforma.metadata.catalogo_caracteristicas
WHERE ativo = true AND sensibilidade = 'normal' AND usavel_em_peca = true;
