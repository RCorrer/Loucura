-- s2_clientview360/05 - Views da Visão 360 + notificações
-- Depende de: core_cliente.golden_record, caracteristicas.customer_features_wide (S1),
--             segmentacao.seg_resultado_corrente + seg_definicao + seg_destino (S1),
--             engagement.tracking_disparo (S3 - ver nota).

-- VISÃO CONSOLIDADA (traz tudo; front filtra pela config N2)
CREATE OR REPLACE VIEW plataforma.visao360.cliente_visao AS
SELECT 
    c.cpf_cnpj, c.nome, c.segmento,
    f.renda_mensal, f.faixa_renda,
    f.saldo_medio, f.saldo_atual, f.faixa_saldo,
    f.score, f.faixa_score,
    f.valor_endividamento, f.comprometimento_renda_pct, f.inadimplente,
    f.idade, f.faixa_etaria, f.genero, f.estado, f.cidade, f.estado_civil,
    f.profissao, f.setor, f.tipo_vinculo, f.escolaridade,
    f.possui_conta, f.tempo_conta_meses, f.tipo_conta,
    f.possui_cartao, f.qtd_cartoes, f.limite_total, f.bandeira, f.fatura_media,
    f.possui_investimento, f.valor_investido, f.perfil_investidor,
    f.possui_seguro, f.tipos_seguro,
    f.possui_credito, f.valor_credito_contratado, f.tipo_credito,
    f.qtd_transacoes_mes, f.ticket_medio, f.valor_movimentado_mes,
    f.usa_app, f.usa_internet_banking, f.canal_preferido, f.frequencia_acesso,
    f.nps, f.churn_score, f.engajamento_score
FROM plataforma.core_cliente.golden_record c
LEFT JOIN plataforma.caracteristicas.customer_features_wide f USING (cpf_cnpj);

-- RLS (aplicar após validar OBO):
-- ALTER VIEW plataforma.visao360.cliente_visao SET ROW FILTER plataforma.encarteiramento.rls_carteira ON (cpf_cnpj);

-- CAMPANHAS/SEGMENTAÇÕES DO CLIENTE + contexto + seg_destino (decisão 4)
-- seg_destino informa a natureza: sempre atendimento humano (está no S2);
-- se houver linha 'sistema3', o front também busca engajamento/jornada (S3).
CREATE OR REPLACE VIEW plataforma.visao360.cliente_campanhas AS
SELECT 
    r.cpf_cnpj,
    r.seg_id,
    s.seg_codigo,
    s.nome,
    s.objetivo,
    s.objetivo_negocio,
    s.publico_alvo_descricao,
    s.resumo,
    s.owner,
    s.area_responsavel,
    s.seg_tags,
    -- natureza do segmento (agregada de seg_destino): true se também é digital (S3)
    MAX(CASE WHEN d.destino = 'sistema3' AND d.habilitado THEN true ELSE false END) AS tem_digital,
    MAX(CASE WHEN d.destino = 'sistema2' AND d.habilitado THEN true ELSE false END) AS tem_humano
FROM plataforma.segmentacao.seg_resultado_corrente r
JOIN plataforma.segmentacao.seg_definicao s USING (seg_id)
LEFT JOIN plataforma.segmentacao.seg_destino d ON d.seg_id = r.seg_id
WHERE s.status = 'ativa'
GROUP BY r.cpf_cnpj, r.seg_id, s.seg_codigo, s.nome, s.objetivo,
         s.objetivo_negocio, s.publico_alvo_descricao, s.resumo,
         s.owner, s.area_responsavel, s.seg_tags;

-- RLS:
-- ALTER VIEW plataforma.visao360.cliente_campanhas SET ROW FILTER plataforma.encarteiramento.rls_carteira ON (cpf_cnpj);

-- ENGAJAMENTO (briefing 90 dias). Depende de engagement.tracking_disparo (S3).
-- NOTA: se rodar antes do S3 existir, a view falha ao ser consultada.
-- Opção: adiar esta view para depois do DDL do S3 (rodar este bloco por último).
CREATE OR REPLACE VIEW plataforma.visao360.engajamento_campanha AS
SELECT 
    t.cpf_cnpj,
    t.campanha_id,
    t.peca_id,
    t.canal,
    t.enviado_em AS data_envio,
    (t.entregue_em IS NOT NULL) AS recebido,
    (t.visualizado_em IS NOT NULL) AS visualizado,
    (t.aberto_em IS NOT NULL) AS aberto,
    (t.clicou_em IS NOT NULL) AS clicou,
    CASE 
        WHEN t.clicou_em IS NOT NULL THEN 'demonstrou_interesse'
        WHEN t.aberto_em IS NOT NULL THEN 'engajou'
        WHEN t.entregue_em IS NOT NULL THEN 'nao_entregue'
        ELSE 'sem_engajamento'
    END AS insight
FROM plataforma.engagement.tracking_disparo t
WHERE t.enviado_em >= current_date() - INTERVAL 90 DAYS;

-- RLS:
-- ALTER VIEW plataforma.visao360.engajamento_campanha SET ROW FILTER plataforma.encarteiramento.rls_carteira ON (cpf_cnpj);

-- NOTIFICAÇÕES in-app
CREATE TABLE IF NOT EXISTS plataforma.visao360.notificacao (
    notif_id        STRING    NOT NULL,
    destinatario    STRING    NOT NULL COMMENT 'responsavel_id',
    tipo            STRING             COMMENT 'follow_up/alerta/sistema',
    cpf_cnpj        STRING,
    titulo          STRING,
    mensagem        STRING,
    lida            BOOLEAN   DEFAULT false,
    criado_em       TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Notificações in-app do S2';