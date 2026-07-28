-- s2_clientview360/03 - Config do app (métricas, priorização, Visão 360 N2)
-- Depende de: s0_comum/01

-- MÉTRICAS (dashboard pessoal do gerente)
CREATE TABLE IF NOT EXISTS plataforma.config.catalogo_metricas (
    metrica_id      STRING    NOT NULL,
    nome_exibicao   STRING,
    descricao       STRING,
    icone           STRING,
    categoria       STRING              COMMENT 'carteira/atendimento/conversao',
    tipo_valor      STRING              COMMENT 'numero/percentual/moeda',
    query_template  STRING              COMMENT 'SQL parametrizado por :responsavel_id (técnico cadastra)',
    formato         STRING,
    ordem           INT,
    ativo           BOOLEAN   DEFAULT true,
    destaque        BOOLEAN   DEFAULT false,
    criado_por      STRING,
    atualizado_em   TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Catálogo de métricas. Query pelo técnico; exibição pelo admin';

-- PRIORIZAÇÃO (score ponderado)
CREATE TABLE IF NOT EXISTS plataforma.config.regras_priorizacao (
    fator_id        STRING    NOT NULL,
    nome_exibicao   STRING,
    descricao       STRING,
    peso            INT                 COMMENT 'Admin ajusta peso',
    condicao_sql    STRING              COMMENT 'Condição do fator no SQL (decisão 7)',
    mensagem_insight STRING,
    ativo           BOOLEAN   DEFAULT true,
    atualizado_por  STRING,
    atualizado_em   TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Fatores de priorização. Condição pelo técnico; peso/ativo pelo admin';

-- VISÃO 360 CONFIGURÁVEL (N2) - BLOCOS
CREATE TABLE IF NOT EXISTS plataforma.config.visao360_blocos (
    bloco_id        STRING    NOT NULL COMMENT 'ex: cadastral, financeiro',
    nome            STRING,
    icone           STRING,
    ordem           INT,
    visivel         BOOLEAN   DEFAULT true,
    tipo            STRING    DEFAULT 'fixo' COMMENT 'fixo/customizavel',
    atualizado_por  STRING,
    atualizado_em   TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Blocos da Visão 360 (N2). Admin controla visibilidade e ordem';

-- VISÃO 360 CONFIGURÁVEL (N2) - CAMPOS
CREATE TABLE IF NOT EXISTS plataforma.config.visao360_campos (
    campo_id        STRING    NOT NULL COMMENT 'Referencia metrica/atributo',
    bloco_id        STRING             COMMENT 'Bloco (admin pode mover)',
    visivel         BOOLEAN   DEFAULT false COMMENT 'Default oculta',
    ordem           INT,
    label_override  STRING,
    atualizado_por  STRING,
    atualizado_em   TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Campos da Visão 360. Só liga se catalogo.usavel_em_v360 = true';

-- CONTEXTO DA SEGMENTAÇÃO CONFIGURÁVEL
CREATE TABLE IF NOT EXISTS plataforma.config.visao360_contexto_segmentacao (
    campo_seg       STRING    NOT NULL COMMENT 'objetivo_negocio, publico_alvo, g_tags',
    visivel         BOOLEAN   DEFAULT false,
    ordem           INT,
    label_override  STRING,
    atualizado_por  STRING,
    atualizado_em   TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Campos de contexto da segmentação exibidos ao gerente';