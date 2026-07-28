-- s0_comum/04 - Golden Record (POC)
-- Em produção: já existe (fora de escopo). Na POC: criado e populado por seed.
-- Referenciado pela view visao360.cliente_visao (S2) e pelo S3 (email/telefone).

CREATE TABLE IF NOT EXISTS plataforma.core_cliente.golden_record (
  cpf_cnpj                   STRING   NOT NULL COMMENT 'Chave universal',
  nome                       STRING,
  email                      STRING   COMMENT 'Para disparo de email (S3)',
  telefone                   STRING   COMMENT 'Para disparo WhatsApp (S3)',
  segmento                   STRING   COMMENT 'varejo/uniclass/private',
  data_nascimento            DATE,
  agencia                    STRING,
  gerente_nome               STRING,
  tempo_relacionamento_meses INT,
  atualizado_em              TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Golden Record consolidado (POC). Fonte de dados cadastrais + contato';