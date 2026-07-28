-- s2_clientview360/04 - Ações do gerente
-- Depende de: s0_comum/01

CREATE TABLE IF NOT EXISTS plataforma.atendimento.interacao (
    interacao_id           STRING    NOT NULL,
    cpf_cnpj               STRING    NOT NULL,
    responsavel_id         STRING    NOT NULL COMMENT 'current_user()',
    tipo                   STRING    COMMENT 'atendimento_realizado/tentativa_contato/desfecho_oferta/follow_up_agendado/anotacao/nao_perturbe',
    canal                  STRING    COMMENT 'presencial/telefone/app/whatsapp/email',
    campanha_id            STRING,
    seg_id                 STRING,
    resultado              STRING    COMMENT 'aceitou/recusou/pensar (desfecho_oferta)',
    motivo                 STRING,
    anotacao               STRING,
    data_agendada_retorno  TIMESTAMP,
    criado_em              TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Ações do gerente. Gera eventos em eventos.retorno_atendimento';

-- Follow-ups pendentes (a partir de hoje). RLS por cpf_cnpj cobre carteira;
-- filtro adicional por responsavel_id = current_user() aplicado no engine.
CREATE OR REPLACE VIEW plataforma.atendimento.follow_ups AS
SELECT *
FROM plataforma.atendimento.interacao
WHERE tipo = 'follow_up_agendado'
  AND data_agendada_retorno >= current_date();