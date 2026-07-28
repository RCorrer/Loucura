-- s0_comum/01 - Catálogo raiz + todos os schemas da plataforma
-- Rodar PRIMEIRO. Todos os demais DDLs dependem deste.

CREATE CATALOG IF NOT EXISTS plataforma
  COMMENT 'Plataforma Customer Data + Engagement';

-- Base compartilhada
CREATE SCHEMA IF NOT EXISTS plataforma.governanca     COMMENT 'RBAC + consentimento (transversal)';
CREATE SCHEMA IF NOT EXISTS plataforma.eventos        COMMENT 'Barramento de eventos entre sistemas';
CREATE SCHEMA IF NOT EXISTS plataforma.core_cliente   COMMENT 'Golden Record (POC)';

-- Dados de origem (existentes/simulados)
CREATE SCHEMA IF NOT EXISTS plataforma.caracteristicas COMMENT 'Features (wide + tb_*)';
CREATE SCHEMA IF NOT EXISTS plataforma.publico         COMMENT 'Públicos-base';
CREATE SCHEMA IF NOT EXISTS plataforma.analitico       COMMENT 'Fonte analítica externa (encarteiramento)';

-- Sistema 1 - SegmentHub
CREATE SCHEMA IF NOT EXISTS plataforma.metadata       COMMENT 'S1: catálogos no-code';
CREATE SCHEMA IF NOT EXISTS plataforma.segmentacao    COMMENT 'S1: produção de públicos';

-- Sistema 2 - ClientView 360
CREATE SCHEMA IF NOT EXISTS plataforma.config         COMMENT 'S2: config do app';
CREATE SCHEMA IF NOT EXISTS plataforma.encarteiramento COMMENT 'S2: função RLS';
CREATE SCHEMA IF NOT EXISTS plataforma.visao360       COMMENT 'S2: views + notificações';
CREATE SCHEMA IF NOT EXISTS plataforma.atendimento    COMMENT 'S2: ações do gerente';

-- Sistema 3 - EngagementHub
CREATE SCHEMA IF NOT EXISTS plataforma.engagement     COMMENT 'S3: campanhas/jornadas/disparos';

-- Sistema 4 - CompassHub
CREATE SCHEMA IF NOT EXISTS plataforma.analytics      COMMENT 'S4: KPIs/OKRs/análises';