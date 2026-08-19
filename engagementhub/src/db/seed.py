"""Seed database for local development (S3 EngagementHub).

Cria tabelas SQLite + dados sintéticos consistentes que se cruzam
para validar o fluxo E2E: campanha → jornada → peça → fila → tracking.

Execução automática via FakeSQLiteClient quando ENV=local e local.db não existe.
"""

import sqlite3
import json
import logging

logger = logging.getLogger(__name__)

# ============================================================
# IDs consistentes (cruzam entre tabelas)
# ============================================================
CAMPANHA_1 = "cam_001aaabbb111"
CAMPANHA_2 = "cam_002cccddd222"
JORNADA_1 = "jor_001aaa111"
JORNADA_2 = "jor_002bbb222"
PECA_EMAIL_1 = "pec_email_001"
PECA_WPP_1 = "pec_wpp_001"
SEG_ID_1 = "seg_alta_renda_01"  # S1 (consumido)
SEG_ID_2 = "seg_jovens_digital"  # S1 (consumido)
USER_ADMIN = "admin@bradesco.com.br"
USER_ANALISTA = "analista@bradesco.com.br"


def seed_database(db_path: str):
    """Cria schema + dados sintéticos."""
    logger.info(f"Seeding database: {db_path}")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # --- Schema (simplificado para SQLite) ---
    _create_tables(c)

    # --- Dados ---
    _seed_governanca(c)
    _seed_campanhas(c)
    _seed_pecas(c)
    _seed_jornadas(c)
    _seed_canais(c)
    _seed_waterfall_capping(c)
    _seed_fila_tracking(c)
    _seed_otimizacao(c)
    _seed_operacao(c)
    _seed_contratos_s1(c)

    conn.commit()
    conn.close()
    logger.info(f"\u2705 Seed completo: {db_path}")


def _create_tables(c):
    """Cria tabelas (subset para testes locais)."""
    c.executescript("""
    -- Governança (S0 consumido)
    CREATE TABLE IF NOT EXISTS usuarios_perfil (
        usuario_id TEXT, perfil TEXT, sistema TEXT, ativo INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS consentimento (
        cpf_cnpj TEXT, canal TEXT, status TEXT, atualizado_em TEXT
    );

    -- S1 consumido
    CREATE TABLE IF NOT EXISTS seg_resultado_corrente (
        seg_id TEXT, cpf_cnpj TEXT, exec_id TEXT, entrou_em TEXT
    );
    CREATE TABLE IF NOT EXISTS seg_definicao (
        seg_id TEXT, nome TEXT, status TEXT, habilitado INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS seg_destino (
        seg_id TEXT, destino_sistema TEXT
    );

    -- Campanha
    CREATE TABLE IF NOT EXISTS campanha (
        campanha_id TEXT PRIMARY KEY, campanha_codigo TEXT, nome TEXT,
        descricao TEXT, objetivo TEXT, tags TEXT, resumo TEXT,
        objetivo_negocio TEXT, observacoes TEXT, owner TEXT,
        area_responsavel TEXT, email_contato TEXT, criado_por TEXT,
        criado_em TEXT, status TEXT DEFAULT 'rascunho',
        vigencia_inicio TEXT, vigencia_fim TEXT,
        aprovado_por TEXT, aprovado_em TEXT,
        limite_envios INTEGER, alerta_pct_limite INTEGER,
        envios_realizados INTEGER DEFAULT 0,
        versao_atual INTEGER DEFAULT 1, atualizado_em TEXT
    );
    CREATE TABLE IF NOT EXISTS campanha_versao (
        campanha_id TEXT, versao INTEGER, snapshot_json TEXT,
        alterado_por TEXT, alterado_em TEXT, motivo TEXT
    );
    CREATE TABLE IF NOT EXISTS campanha_historico_estado (
        hist_id TEXT, campanha_id TEXT, estado_anterior TEXT,
        estado_novo TEXT, motivo TEXT, alterado_por TEXT, alterado_em TEXT
    );
    CREATE TABLE IF NOT EXISTS campanha_jornada (
        campanha_id TEXT, jornada_id TEXT, ordem INTEGER, ativo INTEGER DEFAULT 1
    );

    -- Peças
    CREATE TABLE IF NOT EXISTS peca (
        peca_id TEXT PRIMARY KEY, peca_codigo TEXT, nome TEXT,
        descricao TEXT, canal TEXT, tags TEXT, conteudo_json TEXT,
        html_renderizado TEXT, assunto TEXT, template_meta_id TEXT,
        variaveis_usadas TEXT, status_aprovacao TEXT DEFAULT 'rascunho',
        aprovado_por TEXT, aprovado_em TEXT, motivo_reprovacao TEXT,
        criado_por TEXT, criado_em TEXT, owner TEXT,
        area_responsavel TEXT, versao_atual INTEGER DEFAULT 1, atualizado_em TEXT
    );
    CREATE TABLE IF NOT EXISTS peca_versao (
        peca_id TEXT, versao INTEGER, conteudo_json TEXT,
        html_renderizado TEXT, alterado_por TEXT, alterado_em TEXT, motivo TEXT
    );
    CREATE TABLE IF NOT EXISTS peca_aprovacao (
        aprovacao_id TEXT, peca_id TEXT, versao INTEGER, etapa TEXT,
        perfil_aprovador TEXT, status TEXT, aprovado_por TEXT,
        aprovado_em TEXT, comentario TEXT
    );
    CREATE TABLE IF NOT EXISTS whatsapp_templates (
        template_id TEXT, template_meta_id TEXT, nome TEXT,
        categoria TEXT, corpo TEXT, variaveis_posicionais TEXT,
        status_meta TEXT, submetido_em TEXT, aprovado_em TEXT
    );
    CREATE TABLE IF NOT EXISTS asset (
        asset_id TEXT, nome TEXT, tipo TEXT, caminho_volume TEXT,
        tags TEXT, tamanho_kb INTEGER, criado_por TEXT, criado_em TEXT
    );

    -- Jornadas
    CREATE TABLE IF NOT EXISTS jornada (
        jornada_id TEXT PRIMARY KEY, jornada_codigo TEXT, campanha_id TEXT,
        nome TEXT, descricao TEXT, grafo_json TEXT, seg_entrada_id TEXT,
        resumo TEXT, objetivo_negocio TEXT, observacoes TEXT,
        status TEXT DEFAULT 'rascunho', ao_sair_segmento TEXT,
        ao_pausar_campanha TEXT, cap_estourado TEXT,
        aprovado_por TEXT, aprovado_em TEXT, criado_por TEXT,
        criado_em TEXT, owner TEXT, versao_atual INTEGER DEFAULT 1,
        atualizado_em TEXT
    );
    CREATE TABLE IF NOT EXISTS jornada_estado_cliente (
        estado_id TEXT, jornada_id TEXT, campanha_id TEXT, cpf_cnpj TEXT,
        no_atual TEXT, status TEXT, proxima_acao_em TEXT, entrou_em TEXT,
        ultimo_processamento TEXT, historico_nos TEXT, contexto_json TEXT
    );
    CREATE TABLE IF NOT EXISTS jornada_participacao (
        cpf_cnpj TEXT, jornada_id TEXT, campanha_id TEXT,
        entrou_em TEXT, saiu_em TEXT, status_final TEXT, vezes_participou INTEGER
    );
    CREATE TABLE IF NOT EXISTS jornada_log (
        log_id TEXT, jornada_id TEXT, cpf_cnpj TEXT, no_id TEXT,
        no_tipo TEXT, acao TEXT, resultado TEXT, executado_em TEXT
    );
    CREATE TABLE IF NOT EXISTS config_jornada_politica (
        politica_id TEXT, escopo TEXT, ao_sair_segmento TEXT,
        ao_pausar_campanha TEXT, cap_estourado TEXT, reentrada TEXT,
        reentrada_dias INTEGER, ao_editar_ativa TEXT, permite_loop INTEGER,
        loop_max_iteracoes_teto INTEGER, loop_max_dias_teto INTEGER,
        ativo INTEGER DEFAULT 1, atualizado_por TEXT, atualizado_em TEXT
    );

    -- Canais
    CREATE TABLE IF NOT EXISTS catalogo_canais (
        canal_id TEXT, nome_exibicao TEXT, icone TEXT,
        suporta_html INTEGER, suporta_imagem INTEGER, suporta_botoes INTEGER,
        suporta_video INTEGER, max_caracteres INTEGER, formato_editor TEXT,
        campos_obrigatorios TEXT, provider_class TEXT,
        rate_limit_por_segundo INTEGER, rate_limit_por_dia INTEGER,
        ativo INTEGER DEFAULT 1, atualizado_em TEXT
    );

    -- Waterfall/Capping
    CREATE TABLE IF NOT EXISTS campanha_prioridade (
        campanha_id TEXT, prioridade INTEGER, dias_espera_cascata INTEGER,
        atualizado_por TEXT, atualizado_em TEXT
    );
    CREATE TABLE IF NOT EXISTS regras_capping (
        regra_id TEXT, canal TEXT, max_mensagens INTEGER, periodo TEXT,
        intervalo_minimo_horas INTEGER, escopo TEXT,
        prioritaria_ignora_cap INTEGER DEFAULT 0, ativo INTEGER DEFAULT 1,
        atualizado_por TEXT, atualizado_em TEXT
    );
    CREATE TABLE IF NOT EXISTS config_conversao (
        config_id TEXT, escopo TEXT, evento_conversao TEXT,
        janela_dias INTEGER, ativo INTEGER DEFAULT 1,
        atualizado_por TEXT, atualizado_em TEXT
    );
    CREATE TABLE IF NOT EXISTS supressao_log (
        supressao_id TEXT, cpf_cnpj TEXT, campanha_id TEXT, canal TEXT,
        motivo TEXT, detalhe TEXT, data_execucao TEXT
    );

    -- Disparo
    CREATE TABLE IF NOT EXISTS fila_disparo (
        fila_id TEXT, cpf_cnpj TEXT, campanha_id TEXT, jornada_id TEXT,
        no_id TEXT, peca_id TEXT, canal TEXT, destinatario TEXT,
        agendado_para TEXT, prioridade INTEGER, status TEXT DEFAULT 'pendente',
        tentativas INTEGER DEFAULT 0, criado_em TEXT, atualizado_em TEXT
    );
    CREATE TABLE IF NOT EXISTS disparo_tentativa (
        tentativa_id TEXT, fila_id TEXT, cpf_cnpj TEXT, numero_tentativa INTEGER,
        resultado TEXT, erro_detalhe TEXT, provider_response TEXT, executado_em TEXT
    );
    CREATE TABLE IF NOT EXISTS disparo_avulso (
        disparo_id TEXT, disparo_codigo TEXT, nome TEXT, descricao TEXT,
        seg_id TEXT, peca_id TEXT, canal TEXT, campanha_id TEXT,
        tipo_envio TEXT, agendado_para TEXT, status TEXT,
        aprovado_por TEXT, aprovado_em TEXT,
        qtd_publico INTEGER, qtd_elegivel INTEGER, qtd_enviado INTEGER,
        criado_por TEXT, criado_em TEXT
    );
    CREATE TABLE IF NOT EXISTS config_janela_envio (
        config_id TEXT, canal TEXT, hora_inicio INTEGER, hora_fim INTEGER,
        dias_semana TEXT, timezone TEXT, ativo INTEGER DEFAULT 1,
        atualizado_por TEXT, atualizado_em TEXT
    );
    CREATE TABLE IF NOT EXISTS config_retry (
        config_id TEXT, canal TEXT, max_tentativas INTEGER,
        backoff_minutos TEXT, ativo INTEGER DEFAULT 1,
        atualizado_por TEXT, atualizado_em TEXT
    );

    -- Tracking
    CREATE TABLE IF NOT EXISTS tracking_disparo (
        envio_id TEXT PRIMARY KEY, cpf_cnpj TEXT, campanha_id TEXT,
        jornada_id TEXT, peca_id TEXT, canal TEXT,
        enviado_em TEXT, entregue_em TEXT, visualizado_em TEXT,
        aberto_em TEXT, clicou_em TEXT, converteu_em TEXT,
        status_atual TEXT, erro_detalhe TEXT,
        provider_message_id TEXT, atualizado_em TEXT
    );

    -- Otimização
    CREATE TABLE IF NOT EXISTS config_otimizacao (
        config_id TEXT, escopo TEXT, metrica_alvo TEXT, metrica_custom_json TEXT,
        janela_avaliacao_horas INTEGER, trafego_minimo_pct REAL,
        min_amostras_por_variante INTEGER, frequencia_recalculo TEXT,
        otimizacao_ativa INTEGER, ativo INTEGER DEFAULT 1,
        atualizado_por TEXT, atualizado_em TEXT
    );
    CREATE TABLE IF NOT EXISTS otimizacao_variante (
        variante_id TEXT, jornada_id TEXT, no_id TEXT, peca_id TEXT,
        rotulo TEXT, peso_atual REAL, ativo INTEGER DEFAULT 1, criado_em TEXT
    );
    CREATE TABLE IF NOT EXISTS otimizacao_resultado (
        variante_id TEXT, janela TEXT, envios INTEGER, aberturas INTEGER,
        cliques INTEGER, conversoes INTEGER, taxa_metrica_alvo REAL, atualizado_em TEXT
    );
    CREATE TABLE IF NOT EXISTS otimizacao_historico (
        hist_id TEXT, variante_id TEXT, jornada_id TEXT,
        peso_anterior REAL, peso_novo REAL, motivo TEXT, recalculado_em TEXT
    );

    -- Operação
    CREATE TABLE IF NOT EXISTS saude_operacional (
        metrica_id TEXT, escopo TEXT, valor REAL, status TEXT,
        detalhe TEXT, ultima_verificacao TEXT
    );
    CREATE TABLE IF NOT EXISTS notificacao (
        notif_id TEXT, destinatario TEXT, tipo TEXT, entidade_tipo TEXT,
        entidade_id TEXT, titulo TEXT, mensagem TEXT, severidade TEXT,
        lida INTEGER DEFAULT 0, criado_em TEXT
    );

    -- Eventos (barramento S0)
    CREATE TABLE IF NOT EXISTS disparo_eventos (
        evento_id TEXT, tipo_evento TEXT, entidade_tipo TEXT, entidade_id TEXT,
        payload_json TEXT, emitido_por TEXT, emitido_em TEXT, processado INTEGER DEFAULT 0
    );
    """)


def _seed_governanca(c):
    """Perfis RBAC + consentimento."""
    c.executemany(
        "INSERT INTO usuarios_perfil VALUES (?, ?, ?, ?)",
        [
            (USER_ADMIN, "admin", "engagement", 1),
            (USER_ANALISTA, "analista", "engagement", 1),
            ("sem_perfil@bradesco.com.br", "analista", "segmenthub", 1),  # não tem S3
        ]
    )
    # Consentimento: 3 clientes, 1 opt-out
    c.executemany(
        "INSERT INTO consentimento VALUES (?, ?, ?, datetime('now'))",
        [
            ("11111111111", "email", "opt_in"),
            ("11111111111", "whatsapp", "opt_in"),
            ("22222222222", "email", "opt_in"),
            ("22222222222", "whatsapp", "opt_out"),  # WPP bloqueado
            ("33333333333", "email", "opt_in"),
            ("33333333333", "whatsapp", "opt_in"),
            ("44444444444", "email", "opt_out"),  # Email bloqueado
            ("44444444444", "whatsapp", "opt_in"),
        ]
    )


def _seed_contratos_s1(c):
    """Dados do S1 que o S3 consome (seg_resultado_corrente, seg_definicao, seg_destino)."""
    c.executemany(
        "INSERT INTO seg_definicao VALUES (?, ?, ?, ?)",
        [
            (SEG_ID_1, "Alta Renda Premium", "ativa", 1),
            (SEG_ID_2, "Jovens Digitais", "ativa", 1),
        ]
    )
    c.executemany(
        "INSERT INTO seg_destino VALUES (?, ?)",
        [
            (SEG_ID_1, "engagement"),
            (SEG_ID_2, "engagement"),
        ]
    )
    # Resultado corrente: 4 clientes no seg1, 3 no seg2
    c.executemany(
        "INSERT INTO seg_resultado_corrente VALUES (?, ?, ?, datetime('now'))",
        [
            (SEG_ID_1, "11111111111", "exec_001"),
            (SEG_ID_1, "22222222222", "exec_001"),
            (SEG_ID_1, "33333333333", "exec_001"),
            (SEG_ID_1, "44444444444", "exec_001"),
            (SEG_ID_2, "11111111111", "exec_002"),
            (SEG_ID_2, "33333333333", "exec_002"),
            (SEG_ID_2, "55555555555", "exec_002"),
        ]
    )


def _seed_campanhas(c):
    """2 campanhas em estados diferentes."""
    c.execute(
        "INSERT INTO campanha VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'),?,?,?,?,?,?,?,?,?,datetime('now'))",
        (CAMPANHA_1, "CAM-CROSSSELL-PREMIUM-A1B2", "Cross-sell Premium",
         "Oferta de cartão platinum", "aumentar cross-sell",
         json.dumps(["cross-sell", "premium"]), "Resumo da campanha 1",
         "Aumentar penetração platinum", None,
         USER_ADMIN, "CRM", "crm@bradesco.com.br", USER_ADMIN,
         "ativa", "2026-08-01T00:00:00", "2026-12-31T23:59:59",
         USER_ADMIN, "2026-08-05T10:00:00",
         50000, 80, 1250, 2)
    )
    c.execute(
        "INSERT INTO campanha VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'),?,?,?,?,?,?,?,?,?,datetime('now'))",
        (CAMPANHA_2, "CAM-ENGAJAMENTO-JOVENS-C3D4", "Engajamento Jovens",
         "Ativação de conta digital", "engajamento digital",
         json.dumps(["engajamento", "jovens"]), None, None, None,
         USER_ANALISTA, "Digital", None, USER_ANALISTA,
         "rascunho", None, None, None, None,
         None, None, 0, 1)
    )
    # Versões
    c.execute(
        "INSERT INTO campanha_versao VALUES (?, ?, ?, ?, datetime('now'), ?)",
        (CAMPANHA_1, 1, json.dumps({"nome": "Cross-sell Premium v1"}), USER_ADMIN, "Criação")
    )
    c.execute(
        "INSERT INTO campanha_versao VALUES (?, ?, ?, ?, datetime('now'), ?)",
        (CAMPANHA_1, 2, json.dumps({"nome": "Cross-sell Premium", "objetivo": "aumentar cross-sell"}),
         USER_ADMIN, "Ajuste objetivo")
    )
    # Histórico de estados
    c.executemany(
        "INSERT INTO campanha_historico_estado VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
        [
            ("hist_001", CAMPANHA_1, "rascunho", "em_aprovacao", None, USER_ANALISTA),
            ("hist_002", CAMPANHA_1, "em_aprovacao", "aprovada", "Aprovada", USER_ADMIN),
            ("hist_003", CAMPANHA_1, "aprovada", "ativa", "Ativada", USER_ADMIN),
        ]
    )
    # Vínculo campanha -> jornada
    c.executemany(
        "INSERT INTO campanha_jornada VALUES (?, ?, ?, ?)",
        [
            (CAMPANHA_1, JORNADA_1, 1, 1),
            (CAMPANHA_1, JORNADA_2, 2, 1),
        ]
    )
    # Prioridade waterfall
    c.execute(
        "INSERT INTO campanha_prioridade VALUES (?, ?, ?, ?, datetime('now'))",
        (CAMPANHA_1, 1, 7, USER_ADMIN)
    )


def _seed_pecas(c):
    """2 peças: 1 email aprovada, 1 whatsapp em aprovação."""
    grafo_email = json.dumps({
        "type": "email",
        "subject": "Conheça o Platinum",
        "blocks": [{"type": "text", "content": "Olá {{nome}}, conheça o novo cartão."}]
    })
    c.execute(
        "INSERT INTO peca VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'),?,?,?,datetime('now'))",
        (PECA_EMAIL_1, "PEC-EMAIL-PLATINUM-E1F2", "Email Platinum Oferta",
         "Email de oferta do cartão platinum", "email",
         json.dumps(["oferta", "platinum"]), grafo_email,
         "<html><body>Olá {{nome}}</body></html>",
         "Conheça o Platinum - Exclusivo para você", None,
         json.dumps(["nome", "limite_aprovado"]),
         "aprovada", USER_ADMIN, "2026-08-03T14:00:00", None,
         USER_ANALISTA, USER_ANALISTA, "CRM", 1)
    )
    grafo_wpp = json.dumps({
        "type": "whatsapp",
        "template": "conta_digital_ativacao",
        "params": ["nome", "codigo"]
    })
    c.execute(
        "INSERT INTO peca VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'),?,?,?,datetime('now'))",
        (PECA_WPP_1, "PEC-WPP-ATIVACAO-G3H4", "WhatsApp Ativação",
         "Template de ativação de conta", "whatsapp",
         json.dumps(["ativacao"]), grafo_wpp, None, None,
         "tmpl_ativacao_001", json.dumps(["nome", "codigo"]),
         "em_aprovacao", None, None, None,
         USER_ANALISTA, USER_ANALISTA, "Digital", 1)
    )
    # Aprovação da peça email
    c.execute(
        "INSERT INTO peca_aprovacao VALUES (?,?,?,?,?,?,?,datetime('now'),?)",
        ("apr_001", PECA_EMAIL_1, 1, "conteudo", "admin", "aprovado", USER_ADMIN, "OK")
    )
    # Template WhatsApp
    c.execute(
        "INSERT INTO whatsapp_templates VALUES (?,?,?,?,?,?,?,datetime('now'),NULL)",
        ("tmpl_001", "tmpl_ativacao_001", "conta_digital_ativacao",
         "UTILITY", "Olá {{1}}, ative sua conta com o código {{2}}",
         json.dumps(["nome", "codigo"]), "submetido")
    )


def _seed_jornadas(c):
    """2 jornadas vinculadas à campanha 1."""
    grafo_1 = json.dumps({
        "nodes": [
            {"id": "n1", "type": "entrada", "data": {"seg_id": SEG_ID_1}},
            {"id": "n2", "type": "enviar_peca", "data": {"peca_id": PECA_EMAIL_1}},
            {"id": "n3", "type": "esperar", "data": {"dias": 3}},
            {"id": "n4", "type": "condicao", "data": {"campo": "abriu_email", "op": "=", "valor": True}},
            {"id": "n5", "type": "saida", "data": {}},
        ],
        "edges": [
            {"source": "n1", "target": "n2"},
            {"source": "n2", "target": "n3"},
            {"source": "n3", "target": "n4"},
            {"source": "n4", "target": "n5"},
        ]
    })
    c.execute(
        "INSERT INTO jornada VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'),?,?,datetime('now'))",
        (JORNADA_1, "JOR-CROSSSELL-001-01", CAMPANHA_1,
         "Jornada Email Platinum", "Régua de email para oferta platinum",
         grafo_1, SEG_ID_1, None, None, None,
         "ativa", "continua", "termina_quem_entrou", "adia",
         USER_ADMIN, "2026-08-05T10:00:00", USER_ANALISTA,
         USER_ANALISTA, 1)
    )
    grafo_2 = json.dumps({
        "nodes": [
            {"id": "n1", "type": "entrada", "data": {"seg_id": SEG_ID_1}},
            {"id": "n2", "type": "ab_split", "data": {"variantes": ["A", "B"]}},
            {"id": "n3", "type": "enviar_peca", "data": {"peca_id": PECA_EMAIL_1}},
            {"id": "n4", "type": "saida", "data": {}},
        ],
        "edges": [
            {"source": "n1", "target": "n2"},
            {"source": "n2", "target": "n3"},
            {"source": "n3", "target": "n4"},
        ]
    })
    c.execute(
        "INSERT INTO jornada VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'),?,?,datetime('now'))",
        (JORNADA_2, "JOR-CROSSSELL-001-02", CAMPANHA_1,
         "Jornada A/B Platinum", "Teste A/B de assunto",
         grafo_2, SEG_ID_1, None, None, None,
         "ativa", None, None, None,
         USER_ADMIN, "2026-08-05T10:00:00", USER_ANALISTA,
         USER_ANALISTA, 1)
    )
    # Estado de clientes na jornada 1
    c.executemany(
        "INSERT INTO jornada_estado_cliente VALUES (?,?,?,?,?,?,?,datetime('now'),datetime('now'),?,NULL)",
        [
            ("est_001", JORNADA_1, CAMPANHA_1, "11111111111", "n3", "ativo", "2026-08-22T10:00:00", json.dumps(["n1", "n2", "n3"])),
            ("est_002", JORNADA_1, CAMPANHA_1, "22222222222", "n2", "ativo", "2026-08-19T15:00:00", json.dumps(["n1", "n2"])),
            ("est_003", JORNADA_1, CAMPANHA_1, "33333333333", "n5", "concluido", None, json.dumps(["n1", "n2", "n3", "n4", "n5"])),
        ]
    )
    # Política global
    c.execute(
        "INSERT INTO config_jornada_politica VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))",
        ("pol_global", "global", "continua", "termina_quem_entrou", "adia",
         "apos_dias", 30, "versao_congelada", 1, 5, 30, 1, USER_ADMIN)
    )


def _seed_canais(c):
    """2 canais: email + whatsapp."""
    c.executemany(
        "INSERT INTO catalogo_canais VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))",
        [
            ("email", "E-mail", "mail", 1, 1, 0, 0, None, "rico_html",
             json.dumps(["assunto", "conteudo"]), "EmailProvider", 50, 100000, 1),
            ("whatsapp", "WhatsApp", "chat", 0, 1, 1, 0, 1024, "mensagem_simples",
             json.dumps(["template_meta_id"]), "WhatsAppProvider", 30, 50000, 1),
        ]
    )


def _seed_waterfall_capping(c):
    """Capping + conversão config."""
    c.executemany(
        "INSERT INTO regras_capping VALUES (?,?,?,?,?,?,?,?,?,datetime('now'))",
        [
            ("cap_01", "email", 3, "semana", 24, "global", 0, 1, USER_ADMIN),
            ("cap_02", "whatsapp", 2, "semana", 48, "global", 0, 1, USER_ADMIN),
        ]
    )
    c.execute(
        "INSERT INTO config_conversao VALUES (?,?,?,?,?,?,datetime('now'))",
        ("conv_01", "global", "clicou", 7, 1, USER_ADMIN)
    )


def _seed_fila_tracking(c):
    """Fila com envios pendentes + tracking com funil."""
    # Fila
    c.executemany(
        "INSERT INTO fila_disparo VALUES (?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'),datetime('now'))",
        [
            ("fila_001", "11111111111", CAMPANHA_1, JORNADA_1, "n2", PECA_EMAIL_1,
             "email", "cliente1@gmail.com", "2026-08-19T10:00:00", 1, "pendente", 0),
            ("fila_002", "22222222222", CAMPANHA_1, JORNADA_1, "n2", PECA_EMAIL_1,
             "email", "cliente2@gmail.com", "2026-08-19T10:00:00", 1, "enviado", 1),
            ("fila_003", "33333333333", CAMPANHA_1, JORNADA_1, "n2", PECA_EMAIL_1,
             "email", "cliente3@gmail.com", "2026-08-19T10:00:00", 1, "enviado", 1),
        ]
    )
    # Tracking (funil realístico)
    c.executemany(
        "INSERT INTO tracking_disparo VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))",
        [
            ("env_001", "22222222222", CAMPANHA_1, JORNADA_1, PECA_EMAIL_1, "email",
             "2026-08-18T10:00:00", "2026-08-18T10:01:00", None,
             "2026-08-18T14:30:00", "2026-08-18T14:31:00", None,
             "clicou", None, "msg_prov_001"),
            ("env_002", "33333333333", CAMPANHA_1, JORNADA_1, PECA_EMAIL_1, "email",
             "2026-08-18T10:00:00", "2026-08-18T10:01:00", None,
             "2026-08-18T16:00:00", None, None,
             "aberto", None, "msg_prov_002"),
            ("env_003", "44444444444", CAMPANHA_1, JORNADA_1, PECA_EMAIL_1, "email",
             "2026-08-18T10:00:00", None, None, None, None, None,
             "enviado", "bounce: mailbox full", "msg_prov_003"),
        ]
    )


def _seed_otimizacao(c):
    """Config MAB + 2 variantes com resultados."""
    c.execute(
        "INSERT INTO config_otimizacao VALUES (?,?,?,?,?,?,?,?,?,?,?,datetime('now'))",
        ("mab_01", "global", "clique", None, 24, 0.1, 50, "diario", 1, 1, USER_ADMIN)
    )
    c.executemany(
        "INSERT INTO otimizacao_variante VALUES (?,?,?,?,?,?,?,datetime('now'))",
        [
            ("var_A", JORNADA_2, "n2", PECA_EMAIL_1, "Assunto A", 0.6, 1),
            ("var_B", JORNADA_2, "n2", PECA_EMAIL_1, "Assunto B", 0.4, 1),
        ]
    )
    c.executemany(
        "INSERT INTO otimizacao_resultado VALUES (?,datetime('now'),?,?,?,?,?,datetime('now'))",
        [
            ("var_A", 500, 180, 45, 12, 0.09),
            ("var_B", 500, 150, 30, 8, 0.06),
        ]
    )


def _seed_operacao(c):
    """Saúde operacional + alertas."""
    c.executemany(
        "INSERT INTO saude_operacional VALUES (?,?,?,?,?,datetime('now'))",
        [
            ("saude_01", "fila_email", 0.98, "verde", "Fila email saudável"),
            ("saude_02", "fila_whatsapp", 0.85, "amarelo", "Rate limit próximo"),
        ]
    )
    c.execute(
        "INSERT INTO notificacao VALUES (?,?,?,?,?,?,?,?,?,datetime('now'))",
        ("notif_001", USER_ADMIN, "alerta_saude", "canal", "whatsapp",
         "\u26a0\ufe0f Rate limit WhatsApp", "85% do rate limit diário utilizado",
         "alerta", 0)
    )


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else str(DB_PATH)
    seed_database(path)
    print(f"Seed concluído: {path}")
