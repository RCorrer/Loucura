-- ============================================================
-- GRANTS PARA SERVICE PRINCIPAL ÚNICO: ce1447db-9248-47ad-821a-6718da1c2cef
-- Display Name: app-5k1ms5 segment-hub
-- Usado por todos os sistemas (S1, S2, S3, S4) na POC
-- ============================================================

-- 1. PERMISSÕES DE CATÁLOGO E SCHEMAS (base)
GRANT USE CATALOG ON CATALOG plataforma TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT USE SCHEMA ON SCHEMA plataforma.segmentacao TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT USE SCHEMA ON SCHEMA plataforma.core_cliente TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT USE SCHEMA ON SCHEMA plataforma.engagement TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT USE SCHEMA ON SCHEMA plataforma.eventos TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT USE SCHEMA ON SCHEMA plataforma.governanca TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT USE SCHEMA ON SCHEMA plataforma.metadata TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT USE SCHEMA ON SCHEMA plataforma.caracteristicas TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT USE SCHEMA ON SCHEMA plataforma.publico TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT USE SCHEMA ON SCHEMA plataforma.visao360 TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT USE SCHEMA ON SCHEMA plataforma.atendimento TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT USE SCHEMA ON SCHEMA plataforma.analytics TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT USE SCHEMA ON SCHEMA plataforma.config TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT USE SCHEMA ON SCHEMA plataforma.analitico TO `ce1447db-9248-47ad-821a-6718da1c2cef`;

-- 2. LEITURA UNIVERSAL (todas as tabelas)
-- S1, S2, S3, S4 compartilham o mesmo SP, então precisa ler tudo

-- Core (s0_comum)
GRANT SELECT ON TABLE plataforma.core_cliente.golden_record TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.governanca.consentimento TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.governanca.usuarios_perfil TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.eventos.seg_eventos TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.eventos.disparo_eventos TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.eventos.retorno_atendimento TO `ce1447db-9248-47ad-821a-6718da1c2cef`;

-- Segmentação (s1_segmenthub) - LIDAS POR S2 e S3
GRANT SELECT ON TABLE plataforma.segmentacao.seg_definicao TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.segmentacao.seg_resultado_corrente TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.segmentacao.seg_execucao TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.segmentacao.seg_versao TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.segmentacao.seg_saude TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.segmentacao.seg_historico_estado TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.segmentacao.seg_comentario TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.segmentacao.seg_notificacao TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.segmentacao.seg_destino TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.segmentacao.seg_resultado_historico TO `ce1447db-9248-47ad-821a-6718da1c2cef`;

-- Metadata (s1)
GRANT SELECT ON TABLE plataforma.metadata.catalogo_caracteristicas TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.metadata.catalogo_publicos TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.metadata.catalogo_governanca_hist TO `ce1447db-9248-47ad-821a-6718da1c2cef`;

-- Públicos (s1)
GRANT SELECT ON TABLE plataforma.publico.pub_varejo TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.publico.pub_uniclass TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.publico.pub_private TO `ce1447db-9248-47ad-821a-6718da1c2cef`;

-- Características (s1)
GRANT SELECT ON TABLE plataforma.caracteristicas.customer_features_wide TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.caracteristicas.tb_renda TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.caracteristicas.tb_demografico TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.caracteristicas.tb_saldo_conta TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.caracteristicas.tb_score_credito TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.caracteristicas.tb_transacional TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.caracteristicas.tb_credito TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.caracteristicas.tb_investimentos TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.caracteristicas.tb_cartao TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.caracteristicas.tb_seguros TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.caracteristicas.tb_engajamento TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.caracteristicas.tb_canais_digitais TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.caracteristicas.tb_profissao TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.caracteristicas.tb_escolaridade TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.caracteristicas.tb_endividamento TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.caracteristicas.tb_conta_corrente TO `ce1447db-9248-47ad-821a-6718da1c2cef`;

-- Visão360 (s2) - Views
GRANT SELECT ON VIEW plataforma.visao360.cliente_visao TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON VIEW plataforma.visao360.segmentacoes_ativas_cliente TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON VIEW plataforma.visao360.engajamento_cliente TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.visao360.notificacao TO `ce1447db-9248-47ad-821a-6718da1c2cef`;

-- Atendimento (s2)
GRANT SELECT ON TABLE plataforma.atendimento.interacao TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON VIEW plataforma.atendimento.follow_ups TO `ce1447db-9248-47ad-821a-6718da1c2cef`;

-- Config (s2)
GRANT SELECT ON TABLE plataforma.config.visao360_blocos TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.config.visao360_campos TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.config.visao360_contexto_segmentacao TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.config.catalogo_metricas TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.config.regras_priorizacao TO `ce1447db-9248-47ad-821a-6718da1c2cef`;

-- Analítico (s2)
GRANT SELECT ON TABLE plataforma.analitico.vinculo_cliente_responsavel TO `ce1447db-9248-47ad-821a-6718da1c2cef`;

-- Engagement (s3) - LIDAS POR S2
GRANT SELECT ON TABLE plataforma.engagement.campanha TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.engagement.jornada TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.engagement.peca TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.engagement.tracking_disparo TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.engagement.fila_disparo TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.engagement.disparo_avulso TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.engagement.disparo_tentativa TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.engagement.notificacao TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.engagement.asset TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.engagement.catalogo_canais TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.engagement.config_conversao TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.engagement.config_janela_envio TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.engagement.config_jornada_politica TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.engagement.config_otimizacao TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.engagement.config_retry TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.engagement.regras_capping TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.engagement.supressao_log TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.engagement.campanha_historico_estado TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.engagement.campanha_jornada TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.engagement.campanha_prioridade TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.engagement.campanha_versao TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.engagement.peca_aprovacao TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.engagement.peca_versao TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.engagement.jornada_estado_cliente TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.engagement.jornada_log TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.engagement.jornada_participacao TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.engagement.jornada_teste TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.engagement.jornada_versao TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.engagement.otimizacao_historico TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.engagement.otimizacao_resultado TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.engagement.otimizacao_variante TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.engagement.saude_operacional TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.engagement.whatsapp_templates TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON VIEW plataforma.engagement.cliente_jornada_status TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON VIEW plataforma.engagement.segmento_campanha_map TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON VIEW plataforma.engagement.variaveis_disponiveis TO `ce1447db-9248-47ad-821a-6718da1c2cef`;

-- Analytics (s4)
GRANT SELECT ON TABLE plataforma.analytics.performance_campanha TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.analytics.performance_jornada TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.analytics.performance_peca TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.analytics.performance_segmento TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.analytics.funil_campanha TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.analytics.valor_conversao TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.analytics.custo_canal TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.analytics.kpi_definicao TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.analytics.kpi_valor TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.analytics.okr_objetivo TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.analytics.okr_campanha TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.analytics.okr_keyresult TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.analytics.alerta_regra TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.analytics.alerta_disparado TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.analytics.insight TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT SELECT ON TABLE plataforma.analytics.relatorio_gerado TO `ce1447db-9248-47ad-821a-6718da1c2cef`;

-- Metadata views
GRANT SELECT ON VIEW plataforma.metadata.campos_em_uso TO `ce1447db-9248-47ad-821a-6718da1c2cef`;

-- 3. PERMISSÕES DE ESCRITA (MODIFY para Unity Catalog v1.0)
-- MODIFY engloba INSERT, UPDATE, DELETE em Unity Catalog

-- S1 grava em segmentação
GRANT MODIFY ON TABLE plataforma.segmentacao.seg_definicao TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.segmentacao.seg_resultado_corrente TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.segmentacao.seg_execucao TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.segmentacao.seg_versao TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.segmentacao.seg_saude TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.segmentacao.seg_historico_estado TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.segmentacao.seg_comentario TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.segmentacao.seg_notificacao TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.segmentacao.seg_destino TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.segmentacao.seg_resultado_historico TO `ce1447db-9248-47ad-821a-6718da1c2cef`;

-- S2 grava em atendimento, config e visao360
GRANT MODIFY ON TABLE plataforma.atendimento.interacao TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.visao360.notificacao TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.config.visao360_blocos TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.config.visao360_campos TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.config.visao360_contexto_segmentacao TO `ce1447db-9248-47ad-821a-6718da1c2cef`;

-- S2 pode gravar opt-outs em consentimento
GRANT MODIFY ON TABLE plataforma.governanca.consentimento TO `ce1447db-9248-47ad-821a-6718da1c2cef`;

-- S3 grava em engagement
GRANT MODIFY ON TABLE plataforma.engagement.campanha TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.engagement.jornada TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.engagement.peca TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.engagement.tracking_disparo TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.engagement.fila_disparo TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.engagement.disparo_avulso TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.engagement.disparo_tentativa TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.engagement.notificacao TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.engagement.asset TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.engagement.campanha_historico_estado TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.engagement.campanha_jornada TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.engagement.campanha_prioridade TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.engagement.campanha_versao TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.engagement.peca_aprovacao TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.engagement.peca_versao TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.engagement.jornada_estado_cliente TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.engagement.jornada_log TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.engagement.jornada_participacao TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.engagement.jornada_teste TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.engagement.jornada_versao TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.engagement.otimizacao_historico TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.engagement.otimizacao_resultado TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.engagement.otimizacao_variante TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.engagement.saude_operacional TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.engagement.supressao_log TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.engagement.whatsapp_templates TO `ce1447db-9248-47ad-821a-6718da1c2cef`;

-- S4 grava em analytics
GRANT MODIFY ON TABLE plataforma.analytics.performance_campanha TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.analytics.performance_jornada TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.analytics.performance_peca TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.analytics.performance_segmento TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.analytics.funil_campanha TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.analytics.valor_conversao TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.analytics.custo_canal TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.analytics.kpi_valor TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.analytics.alerta_disparado TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.analytics.insight TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.analytics.relatorio_gerado TO `ce1447db-9248-47ad-821a-6718da1c2cef`;

-- Todos os sistemas gravam eventos
GRANT MODIFY ON TABLE plataforma.eventos.seg_eventos TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.eventos.disparo_eventos TO `ce1447db-9248-47ad-821a-6718da1c2cef`;
GRANT MODIFY ON TABLE plataforma.eventos.retorno_atendimento TO `ce1447db-9248-47ad-821a-6718da1c2cef`;

-- ============================================================
-- TOTAL: ~180 GRANTs configurados
-- ============================================================