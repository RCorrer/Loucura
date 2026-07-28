-- s1_segmenthub/03 - Dataset sintético (estrutura vazia; populado por seed_faker.py)
-- Depende de: s0_comum/01. Chave universal: cpf_cnpj

-- PÚBLICOS-BASE
CREATE TABLE IF NOT EXISTS plataforma.publico.pub_varejo   (cpf_cnpj STRING NOT NULL) USING DELTA;
CREATE TABLE IF NOT EXISTS plataforma.publico.pub_uniclass  (cpf_cnpj STRING NOT NULL) USING DELTA;
CREATE TABLE IF NOT EXISTS plataforma.publico.pub_private  (cpf_cnpj STRING NOT NULL) USING DELTA;

-- FINANCEIRO
CREATE TABLE IF NOT EXISTS plataforma.caracteristicas.tb_renda (
  cpf_cnpj STRING NOT NULL, renda_mensal DOUBLE, faixa_renda STRING, comprovada BOOLEAN
) USING DELTA;

CREATE TABLE IF NOT EXISTS plataforma.caracteristicas.tb_saldo_conta (
  cpf_cnpj STRING NOT NULL, saldo_medio DOUBLE, saldo_atual DOUBLE, faixa_saldo STRING
) USING DELTA;

CREATE TABLE IF NOT EXISTS plataforma.caracteristicas.tb_score_credito (
  cpf_cnpj STRING NOT NULL, score INT, faixa_score STRING
) USING DELTA;

CREATE TABLE IF NOT EXISTS plataforma.caracteristicas.tb_endividamento (
  cpf_cnpj STRING NOT NULL, valor_endividamento DOUBLE, comprometimento_renda_pct DOUBLE, inadimplente BOOLEAN
) USING DELTA;

-- SOCIOECONÔMICO
CREATE TABLE IF NOT EXISTS plataforma.caracteristicas.tb_demografico (
  cpf_cnpj STRING NOT NULL, idade INT, faixa_etaria STRING, genero STRING, estado STRING, cidade STRING, estado_civil STRING
) USING DELTA;

CREATE TABLE IF NOT EXISTS plataforma.caracteristicas.tb_profissao (
  cpf_cnpj STRING NOT NULL, profissao STRING, setor STRING, tipo_vinculo STRING
) USING DELTA;

CREATE TABLE IF NOT EXISTS plataforma.caracteristicas.tb_escolaridade (
  cpf_cnpj STRING NOT NULL, escolaridade STRING
) USING DELTA;

-- PRODUTOS
CREATE TABLE IF NOT EXISTS plataforma.caracteristicas.tb_conta_corrente (
  cpf_cnpj STRING NOT NULL, possui_conta BOOLEAN, tempo_conta_meses INT, tipo_conta STRING
) USING DELTA;

CREATE TABLE IF NOT EXISTS plataforma.caracteristicas.tb_cartao (
  cpf_cnpj STRING NOT NULL, possui_cartao BOOLEAN, qtd_cartoes INT, limite_total DOUBLE, bandeira STRING, fatura_media DOUBLE
) USING DELTA;

CREATE TABLE IF NOT EXISTS plataforma.caracteristicas.tb_investimentos (
  cpf_cnpj STRING NOT NULL, possui_investimento BOOLEAN, valor_investido DOUBLE, perfil_investidor STRING
) USING DELTA;

CREATE TABLE IF NOT EXISTS plataforma.caracteristicas.tb_seguros (
  cpf_cnpj STRING NOT NULL, possui_seguro BOOLEAN, tipos_seguro ARRAY<STRING>
) USING DELTA;

CREATE TABLE IF NOT EXISTS plataforma.caracteristicas.tb_credito (
  cpf_cnpj STRING NOT NULL, possui_credito BOOLEAN, valor_credito_contratado DOUBLE, tipo_credito STRING
) USING DELTA;

-- COMPORTAMENTO
CREATE TABLE IF NOT EXISTS plataforma.caracteristicas.tb_transacional (
  cpf_cnpj STRING NOT NULL, qtd_transacoes_mes INT, ticket_medio DOUBLE, valor_movimentado_mes DOUBLE
) USING DELTA;

CREATE TABLE IF NOT EXISTS plataforma.caracteristicas.tb_canais_digitais (
  cpf_cnpj STRING NOT NULL, usa_app BOOLEAN, usa_internet_banking BOOLEAN, canal_preferido STRING, frequencia_acesso STRING
) USING DELTA;

CREATE TABLE IF NOT EXISTS plataforma.caracteristicas.tb_engajamento (
  cpf_cnpj STRING NOT NULL, nps INT, churn_score DOUBLE, engajamento_score DOUBLE
) USING DELTA;

-- WIDE (one-big-table): estimativa rápida + personalização + Visão 360.
-- Produção: materializada via DLT. POC: populada por seed.
CREATE TABLE IF NOT EXISTS plataforma.caracteristicas.customer_features_wide (
  cpf_cnpj                      STRING NOT NULL,
  renda_mensal                  DOUBLE,
  faixa_renda                   STRING,
  renda_comprovada              BOOLEAN,
  saldo_medio                   DOUBLE,
  saldo_atual                   DOUBLE,
  faixa_saldo                   STRING,
  score                         INT,
  faixa_score                   STRING,
  valor_endividamento           DOUBLE,
  comprometimento_renda_pct     DOUBLE,
  inadimplente                  BOOLEAN,
  idade                         INT,
  faixa_etaria                  STRING,
  genero                        STRING,
  estado                        STRING,
  cidade                        STRING,
  estado_civil                  STRING,
  profissao                     STRING,
  setor                         STRING,
  tipo_vinculo                  STRING,
  escolaridade                  STRING,
  possui_conta                  BOOLEAN,
  tempo_conta_meses             INT,
  tipo_conta                    STRING,
  possui_cartao                 BOOLEAN,
  qtd_cartoes                   INT,
  limite_total                  DOUBLE,
  bandeira                      STRING,
  fatura_media                  DOUBLE,
  possui_investimento           BOOLEAN,
  valor_investido               DOUBLE,
  perfil_investidor             STRING,
  possui_seguro                 BOOLEAN,
  tipos_seguro                  ARRAY<STRING>,
  possui_credito                BOOLEAN,
  valor_credito_contratado      DOUBLE,
  tipo_credito                  STRING,
  qtd_transacoes_mes            INT,
  ticket_medio                  DOUBLE,
  valor_movimentado_mes         DOUBLE,
  usa_app                       BOOLEAN,
  usa_internet_banking          BOOLEAN,
  canal_preferido               STRING,
  frequencia_acesso             STRING,
  nps                           INT,
  churn_score                   DOUBLE,
  engajamento_score             DOUBLE,
  atualizado_em                 TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
CLUSTER BY (cpf_cnpj)
COMMENT 'One-big-table desnormalizada para estimativa e personalização';