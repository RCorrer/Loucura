-- s3_engagement/06 - Fila de disparo + tentativas + avulso + janela + retry
-- Depende de: s0_comum/01

CREATE TABLE IF NOT EXISTS plataforma.engagement.fila_disparo (
  fila_id STRING NOT NULL,
  cpf_cnpj STRING,
  campanha_id STRING,
  jornada_id STRING,
  no_id STRING,
  peca_id STRING,
  canal STRING,
  destinatario STRING COMMENT 'email ou telefone resolvido',
  agendado_para TIMESTAMP,
  prioridade INT,
  status STRING COMMENT 'pendente/enviado/falha/suprimido',
  tentativas INT DEFAULT 0,
  criado_em TIMESTAMP DEFAULT current_timestamp(),
  atualizado_em TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
CLUSTER BY (status, agendado_para)
COMMENT 'Fila única de disparo (jornada + avulso). Processada pelo motor_disparo';

CREATE TABLE IF NOT EXISTS plataforma.engagement.disparo_tentativa (
  tentativa_id STRING NOT NULL,
  fila_id STRING,
  cpf_cnpj STRING,
  numero_tentativa INT,
  resultado STRING COMMENT 'sucesso/falha_temporaria/falha_permanente',
  erro_detalhe STRING,
  provider_response STRING,
  executado_em TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Cada tentativa de envio (retry com backoff)';

CREATE TABLE IF NOT EXISTS plataforma.engagement.disparo_avulso (
  disparo_id STRING NOT NULL,
  disparo_codigo STRING COMMENT 'DAV-2025-00033',
  nome STRING,
  descricao STRING,
  seg_id STRING,
  peca_id STRING,
  canal STRING,
  campanha_id STRING COMMENT 'Opcional: standalone ou vinculado',
  tipo_envio STRING COMMENT 'imediato/agendado',
  agendado_para TIMESTAMP,
  status STRING,
  aprovado_por STRING,
  aprovado_em TIMESTAMP,
  qtd_publico BIGINT,
  qtd_elegivel BIGINT,
  qtd_enviado BIGINT,
  criado_por STRING,
  criado_em TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Disparo avulso (DAV). Respeita toda governança (capping/consentimento/janela)';

CREATE TABLE IF NOT EXISTS plataforma.engagement.config_janela_envio (
  config_id STRING NOT NULL,
  canal STRING,
  hora_inicio INT,
  hora_fim INT,
  dias_semana ARRAY<STRING>,
  timezone STRING,
  ativo BOOLEAN DEFAULT true,
  atualizado_por STRING,
  atualizado_em TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Horários/dias permitidos para envio (importante p/ banco)';

CREATE TABLE IF NOT EXISTS plataforma.engagement.config_retry (
  config_id STRING NOT NULL,
  canal STRING,
  max_tentativas INT,
  backoff_minutos ARRAY<INT> COMMENT 'ex: [1,5,30]',
  ativo BOOLEAN DEFAULT true,
  atualizado_por STRING,
  atualizado_em TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Política de retry por canal';