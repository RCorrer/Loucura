-- s3_engagement/05 - Jornadas (grafo) + estado por cliente + participação + logs + política
-- Depende de: s0_comum/01, segmentacao.seg_resultado_corrente (S1)

CREATE TABLE IF NOT EXISTS plataforma.engagement.jornada (
  jornada_id STRING NOT NULL,
  jornada_codigo STRING COMMENT 'JOR-2025-00015-01 (hierárquico)',
  campanha_id STRING,
  nome STRING,
  descricao STRING,
  grafo_json STRING COMMENT 'Grafo React Flow (nós + arestas + loops)',
  seg_entrada_id STRING COMMENT 'seg_id do S1. PONTE seg->campanha (contrato p/ mapa)',
  resumo STRING,
  objetivo_negocio STRING,
  observacoes STRING,
  status STRING COMMENT 'rascunho/aprovada/ativa/pausada/encerrada',
  ao_sair_segmento STRING COMMENT 'continua/remove (sobrescreve política global)',
  ao_pausar_campanha STRING,
  cap_estourado STRING,
  aprovado_por STRING,
  aprovado_em TIMESTAMP,
  criado_por STRING,
  criado_em TIMESTAMP DEFAULT current_timestamp(),
  owner STRING,
  versao_atual INT DEFAULT 1,
  atualizado_em TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Jornada (batalha): fluxo sobre 1 segmento de entrada';

CREATE TABLE IF NOT EXISTS plataforma.engagement.jornada_versao (
  jornada_id STRING NOT NULL,
  versao INT NOT NULL,
  grafo_json STRING,
  alterado_por STRING,
  alterado_em TIMESTAMP DEFAULT current_timestamp(),
  motivo STRING
) USING DELTA
COMMENT 'Versões da jornada (edição ativa = versão congelada p/ quem está no meio)';

CREATE TABLE IF NOT EXISTS plataforma.engagement.jornada_estado_cliente (
  estado_id STRING NOT NULL,
  jornada_id STRING NOT NULL,
  campanha_id STRING,
  cpf_cnpj STRING NOT NULL,
  no_atual STRING COMMENT 'Nó em que o cliente está',
  status STRING COMMENT 'ativo/aguardando/concluido/saiu',
  proxima_acao_em TIMESTAMP COMMENT 'Quando o motor processa de novo',
  entrou_em TIMESTAMP,
  ultimo_processamento TIMESTAMP,
  historico_nos ARRAY<STRING> COMMENT 'Nós percorridos',
  contexto_json STRING
) USING DELTA
COMMENT 'Estado de cada cliente na jornada. Base do contrato cliente_jornada_status (S2)';

CREATE TABLE IF NOT EXISTS plataforma.engagement.jornada_participacao (
  cpf_cnpj STRING NOT NULL,
  jornada_id STRING NOT NULL,
  campanha_id STRING,
  entrou_em TIMESTAMP,
  saiu_em TIMESTAMP,
  status_final STRING,
  vezes_participou INT DEFAULT 1
) USING DELTA
COMMENT 'Histórico de participação (controle de reentrada)';

CREATE TABLE IF NOT EXISTS plataforma.engagement.jornada_log (
  log_id STRING NOT NULL,
  jornada_id STRING,
  cpf_cnpj STRING,
  no_id STRING,
  no_tipo STRING,
  acao STRING,
  resultado STRING,
  executado_em TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Auditoria de execução da jornada por cliente/nó';

CREATE TABLE IF NOT EXISTS plataforma.engagement.jornada_teste (
  teste_id STRING NOT NULL,
  jornada_id STRING,
  tipo STRING COMMENT 'simulacao_logica/teste_real',
  lista_teste ARRAY<STRING>,
  resultado_json STRING,
  executado_por STRING,
  executado_em TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Preview de jornada (simulação sem enviar / teste real p/ lista interna)';

CREATE TABLE IF NOT EXISTS plataforma.engagement.config_jornada_politica (
  politica_id STRING NOT NULL,
  escopo STRING COMMENT 'global/por_jornada',
  ao_sair_segmento STRING COMMENT 'continua/remove',
  ao_pausar_campanha STRING COMMENT 'para_tudo/termina_quem_entrou',
  cap_estourado STRING COMMENT 'adia/pula',
  reentrada STRING COMMENT 'bloqueada/permitida/apos_dias',
  reentrada_dias INT,
  ao_editar_ativa STRING COMMENT 'versao_congelada/migra',
  permite_loop BOOLEAN,
  loop_max_iteracoes_teto INT COMMENT 'Teto global que o analista não ultrapassa',
  loop_max_dias_teto INT,
  ativo BOOLEAN DEFAULT true,
  atualizado_por STRING,
  atualizado_em TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Políticas de jornada (global + sobrescrita por jornada)';