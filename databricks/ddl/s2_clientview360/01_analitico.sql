-- s2_clientview360/01 - Fonte externa (analítico): encarteiramento
-- Produção: tabela do analítico, imutável, só leitura. POC: criada + populada por seed.
-- Depende de: s0_comum/01

CREATE TABLE IF NOT EXISTS plataforma.analitico.vinculo_cliente_responsavel (
    cpf_cnpj        STRING NOT NULL,
    responsavel_id  STRING NOT NULL COMMENT 'ID do gerente/vendedor (bate com current_user())',
    tipo_responsavel STRING        COMMENT 'gerente/vendedor'
) USING DELTA
COMMENT 'Encarteiramento. Suporta 1:1 e 1:N. Sem hierarquia na POC';