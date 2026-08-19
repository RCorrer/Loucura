-- s3_engagement/02 - Waterfall (prioridade) + Frequency Capping + Supressão
-- Depende de: s0_comum/01

CREATE TABLE IF NOT EXISTS plataforma.engagement.campanha_prioridade (
  campanha_id STRING NOT NULL,
  prioridade INT COMMENT 'Menor = maior prioridade',
  dias_espera_cascata INT COMMENT 'Dias até liberar próxima campanha',
  atualizado_por STRING,
  atualizado_em TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Ordem do waterfall (drag-drop na tela). Cliente entra na de maior prioridade';

CREATE TABLE IF NOT EXISTS plataforma.engagement.regras_capping (
  regra_id STRING NOT NULL,
  canal STRING,
  max_mensagens INT,
  periodo STRING COMMENT 'dia/semana/mes',
  intervalo_minimo_horas INT,
  escopo STRING COMMENT 'global/por_campanha',
  prioritaria_ignora_cap BOOLEAN DEFAULT false,
  ativo BOOLEAN DEFAULT true,
  atualizado_por STRING,
  atualizado_em TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Frequency capping (anti-fadiga). Global ou por canal';

CREATE TABLE IF NOT EXISTS plataforma.engagement.config_conversao (
  config_id STRING NOT NULL,
  escopo STRING COMMENT 'global/por_campanha',
  evento_conversao STRING COMMENT 'abriu/clicou/converteu',
  janela_dias INT,
  ativo BOOLEAN DEFAULT true,
  atualizado_por STRING,
  atualizado_em TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Critério de conversão da cascata (configurável)';

CREATE TABLE IF NOT EXISTS plataforma.engagement.supressao_log (
  supressao_id STRING NOT NULL,
  cpf_cnpj STRING,
  campanha_id STRING,
  canal STRING,
  motivo STRING COMMENT 'opt_out/capping/waterfall/blacklisted/janela',
  detalhe STRING,
  data_execucao TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Registra CADA não-envio e o porquê (transparência). Consultável via admin';