-- s2_clientview360/02 - Função RLS de carteira
-- Aplicada nas views da Visão 360 via SET ROW FILTER.
-- Depende de: 01_analitico. Requer OBO ativo (current_user() = usuário logado).

CREATE OR REPLACE FUNCTION plataforma.encarteiramento.rls_carteira(cpf_cnpj STRING)
RETURNS BOOLEAN
RETURN EXISTS (
    SELECT 1
    FROM plataforma.analitico.vinculo_cliente_responsavel v
    WHERE v.cpf_cnpj = cpf_cnpj
      AND v.responsavel_id = current_user()
);

-- Uso: ALTER VIEW ... SET ROW FILTER plataforma.encarteiramento.rls_carteira ON (cpf_cnpj);