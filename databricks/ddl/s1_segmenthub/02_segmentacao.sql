-- s1_segmenthub/02 - Núcleo produtor (segmentacao)
-- Depende de: s0_comum/01

CREATE TABLE IF NOT EXISTS plataforma.segmentacao.seg_definicao (
  seg_id                   STRING   NOT NULL COMMENT 'Chave única',
  seg_codigo               STRING   COMMENT 'Código amigável',
  seg_slug                 STRING,
  nome                     STRING,
  descricao                STRING,
  objetivo                 STRING   COMMENT 'AQUISICAO/RENTABILIZACAO/RETENCAO/ENGAJAMENTO/COBRANCA',
  seg_tags                 ARRAY<STRING>,
  resumo                   STRING   COMMENT 'Resumo funcional',
  objetivo_negocio         STRING   COMMENT 'Contexto de negócio',
  publico_alvo_descricao   STRING   COMMENT 'Descrição do público',
  observacoes              STRING,
  documentacao_md          STRING   COMMENT 'Markdown explicativo',
  owner                    STRING,
  area_responsavel         STRING,
  email_contato            STRING,
  criado_por               STRING,
  criado_em                TIMESTAMP DEFAULT current_timestamp(),
  seg_origem_id            STRING   COMMENT 'Link com pai',
  tipo_origem              STRING   COMMENT 'nova/clone/derivada',
  tipo                     STRING   COMMENT 'direta/composta',
  publico_base_id          STRING,
  regras_json              STRING   COMMENT 'Árvore de regras',
  status                   STRING   DEFAULT 'rascunho' COMMENT 'rascunho/em_aprovacao/ativa/pausada/arquivada',
  vigencia_inicio          TIMESTAMP,
  vigencia_fim             TIMESTAMP,
  agendamento_cron         STRING,
  recorrencia              STRING   COMMENT 'once/diaria/semanal/mensal',
  aprovado_por             STRING,
  aprovado_em              TIMESTAMP,
  checklist_validacao_json STRING,
  versao_atual             INT      DEFAULT 1,
  atualizado_em            TIMESTAMP DEFAULT current_timestamp(),
  habilitado               BOOLEAN  DEFAULT true
) USING DELTA
CLUSTER BY (status, objetivo, owner)
TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true',
  'delta.targetFileSize' = '128MB',
  'delta.tuneFileSizesForRewrites' = 'true'
)
COMMENT 'Natureza do segmento. CONTRATO-CHAVE: lido por S2, S3 e S4 (dimensão de eficiência)';

-- Bloom Filter Index para buscas rápidas
CREATE BLOOMFILTER INDEX IF NOT EXISTS ON plataforma.segmentacao.seg_definicao
FOR COLUMNS (seg_id, seg_codigo, seg_slug);

CREATE TABLE IF NOT EXISTS plataforma.segmentacao.seg_execucao (
  exec_id         STRING   NOT NULL COMMENT 'exec_YYYYMMDD_HHMM_xxxx',
  seg_id          STRING   NOT NULL,
  versao_usada    INT,
  origem_execucao STRING   COMMENT 'agendada/aprovacao/manual',
  executado_em    TIMESTAMP DEFAULT current_timestamp(),
  qtd_clientes    BIGINT   COMMENT 'COUNT exato',
  status          STRING   COMMENT 'sucesso/erro/erro_metadado/em_execucao',
  job_id          STRING,
  run_id          STRING,
  job_run_url     STRING
) USING DELTA
CLUSTER BY (seg_id, status)
TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true',
  'delta.targetFileSize' = '256MB',
  'delta.deletedFileRetentionDuration' = 'interval 30 days'
)
COMMENT 'Registro de cada execução/recálculo';

-- Bloom Filter Index para buscas rápidas
CREATE BLOOMFILTER INDEX IF NOT EXISTS ON plataforma.segmentacao.seg_execucao
FOR COLUMNS (exec_id, seg_id, job_id);

CREATE TABLE IF NOT EXISTS plataforma.segmentacao.seg_resultado_corrente (
  seg_id    STRING   NOT NULL,
  cpf_cnpj  STRING   NOT NULL,
  exec_id   STRING,
  entrou_em TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
CLUSTER BY (seg_id, cpf_cnpj)
TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true',
  'delta.targetFileSize' = '512MB',
  'delta.tuneFileSizesForRewrites' = 'true',
  'delta.checkpoint.writeStatsAsStruct' = 'true',
  'delta.checkpoint.writeStatsAsJson' = 'false'
)
COMMENT 'Estado ATUAL por segmento (MERGE). CONTRATO: lido por S2 e S3';

-- Bloom Filter Index CRÍTICO para lookups por CPF/ID
CREATE BLOOMFILTER INDEX IF NOT EXISTS ON plataforma.segmentacao.seg_resultado_corrente
FOR COLUMNS (cpf_cnpj, seg_id);

CREATE TABLE IF NOT EXISTS plataforma.segmentacao.seg_resultado_historico (
  exec_id      STRING   NOT NULL,
  seg_id       STRING   NOT NULL,
  versao_usada INT,
  cpf_cnpj     STRING   NOT NULL,
  snapshot_em  TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
CLUSTER BY (seg_id, exec_id)
TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true',
  'delta.targetFileSize' = '1GB',
  'delta.tuneFileSizesForRewrites' = 'true',
  'delta.deletedFileRetentionDuration' = 'interval 90 days',
  'delta.logRetentionDuration' = 'interval 365 days'
)
COMMENT 'Append-only: snapshot por execução (auditoria/overlap)';

-- Bloom Filter Index para auditoria rápida
CREATE BLOOMFILTER INDEX IF NOT EXISTS ON plataforma.segmentacao.seg_resultado_historico
FOR COLUMNS (exec_id, seg_id);

CREATE TABLE IF NOT EXISTS plataforma.segmentacao.seg_overlap (
  seg_id_a          STRING   NOT NULL,
  seg_id_b          STRING   NOT NULL,
  clientes_em_comum BIGINT,
  pct_sobre_a       DOUBLE,
  pct_sobre_b       DOUBLE,
  calculado_em      TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
CLUSTER BY (seg_id_a)
COMMENT 'Sobreposição entre segmentos (alerta de fadiga)';

CREATE TABLE IF NOT EXISTS plataforma.segmentacao.seg_comentario (
  comentario_id    STRING   NOT NULL,
  seg_id           STRING   NOT NULL,
  versao_referencia INT,
  tipo             STRING,
  autor            STRING,
  texto            STRING,
  respondendo_a    STRING   COMMENT 'comentario_id pai (thread)',
  mencoes          ARRAY<STRING>,
  resolvido        BOOLEAN  DEFAULT false,
  criado_em        TIMESTAMP DEFAULT current_timestamp(),
  editado_em       TIMESTAMP
) USING DELTA
CLUSTER BY (seg_id)
COMMENT 'Thread de comentários colaborativos';

CREATE TABLE IF NOT EXISTS plataforma.segmentacao.seg_notificacao (
  notif_id     STRING   NOT NULL,
  destinatario STRING   NOT NULL,
  tipo         STRING   COMMENT 'mencao/saude/mudanca_estado',
  seg_id       STRING,
  titulo       STRING,
  mensagem     STRING,
  lida         BOOLEAN  DEFAULT false,
  criado_em    TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
CLUSTER BY (destinatario)
COMMENT 'Notificações in-app do S1';

CREATE TABLE IF NOT EXISTS plataforma.segmentacao.seg_saude (
  seg_id               STRING   NOT NULL,
  health_status        STRING   COMMENT 'verde/amarelo/vermelho',
  ultima_verificacao   TIMESTAMP DEFAULT current_timestamp(),
  variacao_publico_pct DOUBLE,
  taxa_sucesso_exec    DOUBLE,
  tempo_medio_exec_seg INT,
  alertas_json         STRING,
  publico_atual        BIGINT
) USING DELTA
CLUSTER BY (health_status)
COMMENT 'Estado de saúde por segmentação (populado por Job)';

-- =====================================================
-- TABELAS ADICIONAIS (versionamento e destinos)
-- =====================================================

CREATE TABLE IF NOT EXISTS plataforma.segmentacao.seg_versao (
  versao_id   STRING NOT NULL,
  seg_id      STRING NOT NULL,
  versao      INT NOT NULL,
  regras_json STRING,
  motivo      STRING,
  alterado_por STRING,
  alterado_em TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
CLUSTER BY (seg_id, versao)
TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.targetFileSize' = '64MB'
)
COMMENT 'Histórico de versões da segmentação (cada alteração de regras gera nova versão)';

CREATE TABLE IF NOT EXISTS plataforma.segmentacao.seg_historico_estado (
  hist_id         STRING NOT NULL,
  seg_id          STRING NOT NULL,
  estado_anterior STRING,
  estado_novo     STRING,
  motivo          STRING,
  alterado_por    STRING,
  alterado_em     TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
CLUSTER BY (seg_id)
TBLPROPERTIES ('delta.autoOptimize.optimizeWrite' = 'true')
COMMENT 'Auditoria de mudanças de status da segmentação';

CREATE TABLE IF NOT EXISTS plataforma.segmentacao.seg_destino (
  seg_id     STRING NOT NULL,
  destino    STRING NOT NULL,
  habilitado BOOLEAN DEFAULT true,
  criado_em  TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
CLUSTER BY (seg_id)
COMMENT 'Destinos de publicação da segmentação (S2, S3, S4)';

-- =====================================================
-- MANUTENÇÃO PERIÓDICA (executar mensalmente)
-- =====================================================
-- OPTIMIZE plataforma.segmentacao.seg_resultado_corrente;
-- OPTIMIZE plataforma.segmentacao.seg_resultado_historico;
-- VACUUM plataforma.segmentacao.seg_resultado_historico RETAIN 90 HOURS;
-- VACUUM plataforma.segmentacao.seg_execucao RETAIN 720 HOURS;