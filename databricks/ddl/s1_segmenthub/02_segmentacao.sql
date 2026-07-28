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
COMMENT 'Natureza do segmento. CONTRATO-CHAVE: lido por S2, S3 e S4 (dimensão de eficiência)';

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
COMMENT 'Registro de cada execução/recálculo';

CREATE TABLE IF NOT EXISTS plataforma.segmentacao.seg_resultado_corrente (
  seg_id    STRING   NOT NULL,
  cpf_cnpj  STRING   NOT NULL,
  exec_id   STRING,
  entrou_em TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
CLUSTER BY (seg_id)
COMMENT 'Estado ATUAL por segmento (MERGE). CONTRATO: lido por S2 e S3';

CREATE TABLE IF NOT EXISTS plataforma.segmentacao.seg_resultado_historico (
  exec_id      STRING   NOT NULL,
  seg_id       STRING   NOT NULL,
  versao_usada INT,
  cpf_cnpj     STRING   NOT NULL,
  snapshot_em  TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Append-only: snapshot por execução (auditoria/overlap)';

CREATE TABLE IF NOT EXISTS plataforma.segmentacao.seg_overlap (
  seg_id_a          STRING   NOT NULL,
  seg_id_b          STRING   NOT NULL,
  clientes_em_comum BIGINT,
  pct_sobre_a       DOUBLE,
  pct_sobre_b       DOUBLE,
  calculado_em      TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
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
COMMENT 'Estado de saúde por segmentação (populado por Job)';