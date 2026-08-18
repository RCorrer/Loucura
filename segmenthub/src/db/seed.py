"""Seed script for the local SQLite fake database.

Creates all tables and populates them with consistent fictional data
so the full SegmentHub flow works locally without Databricks.

Tables created:
- catalogo_caracteristicas (metadata)
- catalogo_publicos (metadata)
- campos_em_uso (metadata)
- customer_features_wide (caracteristicas)
- pf_geral (publico base)
- pj_geral (publico base)
- seg_definicao (segmentacao)
- seg_saude (segmentacao)
- seg_comentario (segmentacao)
- seg_notificacao (segmentacao)
- seg_execucao (segmentacao)
- seg_job_log (segmentacao)
"""

import json
import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def seed_database(db_path: str = None):
    """Create and seed the local SQLite database."""
    if db_path is None:
        db_path = str(Path(__file__).parent / "local.db")

    logger.info(f"Criando banco local em: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    _create_tables(conn)
    _seed_catalogo_caracteristicas(conn)
    _seed_catalogo_publicos(conn)
    _seed_publico_pf_geral(conn)
    _seed_publico_pj_geral(conn)
    _seed_customer_features_wide(conn)
    _seed_campos_em_uso(conn)
    _seed_seg_definicao(conn)
    _seed_seg_saude(conn)
    _seed_seg_comentario(conn)
    _seed_seg_notificacao(conn)
    _seed_seg_execucao(conn)
    _seed_seg_job_log(conn)

    conn.commit()
    conn.close()
    logger.info("\u2705 Seed conclu\u00eddo com sucesso!")


def _create_tables(conn: sqlite3.Connection):
    """Create all tables mimicking the Unity Catalog schema."""
    conn.executescript("""
        -- ============================================================
        -- METADATA
        -- ============================================================
        CREATE TABLE IF NOT EXISTS catalogo_caracteristicas (
            caracteristica_id TEXT PRIMARY KEY,
            campo_label TEXT NOT NULL,
            tema TEXT NOT NULL,
            tema_ordem INTEGER DEFAULT 0,
            tipo_dado TEXT NOT NULL,
            operadores TEXT,  -- JSON array
            valores_dominio TEXT,  -- JSON array
            descricao TEXT,
            tabela_fisica TEXT,
            campo_fisico TEXT,
            sensibilidade TEXT DEFAULT 'baixa',
            ativo INTEGER DEFAULT 1,
            usavel_em_visao360 INTEGER DEFAULT 0,
            usavel_em_peca INTEGER DEFAULT 0,
            bloco_visao360 TEXT
        );

        CREATE TABLE IF NOT EXISTS catalogo_publicos (
            publico_id TEXT PRIMARY KEY,
            nome TEXT NOT NULL,
            descricao TEXT,
            ativo INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS campos_em_uso (
            campo_id TEXT PRIMARY KEY,
            qtd_segmentacoes_ativas INTEGER DEFAULT 0,
            segmentacoes TEXT  -- JSON array
        );

        -- ============================================================
        -- PUBLICO (bases de p\u00fablico)
        -- ============================================================
        CREATE TABLE IF NOT EXISTS pf_geral (
            cpf_cnpj TEXT PRIMARY KEY
        );

        CREATE TABLE IF NOT EXISTS pj_geral (
            cpf_cnpj TEXT PRIMARY KEY
        );

        -- ============================================================
        -- CARACTERISTICAS
        -- ============================================================
        CREATE TABLE IF NOT EXISTS customer_features_wide (
            cpf_cnpj TEXT PRIMARY KEY,
            idade INTEGER,
            renda_mensal REAL,
            segmento_comportamental TEXT,
            canal_preferido TEXT,
            qtd_produtos_contratados INTEGER,
            tempo_relacionamento_meses INTEGER,
            score_credito INTEGER,
            uf TEXT,
            ticket_medio REAL,
            frequencia_transacoes INTEGER,
            saldo_medio REAL,
            flag_digital INTEGER DEFAULT 0,
            profissao TEXT,
            estado_civil TEXT
        );

        -- ============================================================
        -- SEGMENTACAO
        -- ============================================================
        CREATE TABLE IF NOT EXISTS seg_definicao (
            seg_id TEXT PRIMARY KEY,
            seg_codigo TEXT,
            seg_slug TEXT,
            nome TEXT NOT NULL,
            descricao TEXT,
            objetivo TEXT,
            seg_tags TEXT,  -- JSON array
            resumo TEXT,
            objetivo_negocio TEXT,
            publico_alvo_descricao TEXT,
            observacoes TEXT,
            documentacao_md TEXT,
            owner TEXT,
            area_responsavel TEXT,
            email_contato TEXT,
            criado_por TEXT,
            criado_em TEXT,
            seg_origem_id TEXT,
            tipo_origem TEXT,
            tipo TEXT DEFAULT 'direta',
            publico_base_id TEXT,
            regras_json TEXT,  -- JSON
            status TEXT DEFAULT 'rascunho',
            vigencia_inicio TEXT,
            vigencia_fim TEXT,
            agendamento_cron TEXT,
            recorrencia TEXT,
            aprovado_por TEXT,
            aprovado_em TEXT,
            checklist_validacao_json TEXT,
            versao_atual INTEGER DEFAULT 1,
            atualizado_em TEXT,
            habilitado INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS seg_saude (
            seg_id TEXT PRIMARY KEY,
            health_status TEXT,
            ultima_verificacao TEXT,
            variacao_publico_pct REAL,
            taxa_sucesso_exec REAL,
            tempo_medio_exec_seg REAL,
            alertas_json TEXT,
            publico_atual INTEGER
        );

        CREATE TABLE IF NOT EXISTS seg_comentario (
            comentario_id TEXT PRIMARY KEY,
            seg_id TEXT,
            versao_referencia INTEGER,
            tipo TEXT DEFAULT 'geral',
            autor TEXT,
            texto TEXT,
            respondendo_a TEXT,
            mencoes TEXT,  -- JSON array
            resolvido INTEGER DEFAULT 0,
            criado_em TEXT,
            editado_em TEXT
        );

        CREATE TABLE IF NOT EXISTS seg_notificacao (
            notif_id TEXT PRIMARY KEY,
            destinatario TEXT,
            tipo TEXT,
            seg_id TEXT,
            titulo TEXT,
            mensagem TEXT,
            lida INTEGER DEFAULT 0,
            criado_em TEXT
        );

        CREATE TABLE IF NOT EXISTS seg_execucao (
            exec_id TEXT PRIMARY KEY,
            seg_id TEXT,
            status TEXT,
            inicio TEXT,
            fim TEXT,
            publico_gerado INTEGER,
            erro TEXT,
            versao INTEGER
        );

        CREATE TABLE IF NOT EXISTS seg_job_log (
            log_id TEXT PRIMARY KEY,
            seg_id TEXT,
            acao TEXT,
            job_id TEXT,
            run_id TEXT,
            status TEXT,
            detalhes TEXT,
            criado_em TEXT
        );
    """)


# ============================================================
# SEED DATA
# ============================================================

# CPFs fict\u00edcios (formato simplificado para dev)
_CPFS_PF = [
    "11111111111", "22222222222", "33333333333", "44444444444",
    "55555555555", "66666666666", "77777777777", "88888888888",
    "99999999999", "10101010101", "12121212121", "13131313131",
    "14141414141", "15151515151", "16161616161", "17171717171",
    "18181818181", "19191919191", "20202020202", "21212121212",
]

_CPFS_PJ = [
    "11111111000100", "22222222000100", "33333333000100",
    "44444444000100", "55555555000100",
]


def _seed_catalogo_caracteristicas(conn: sqlite3.Connection):
    """Seed feature catalog — must match columns in customer_features_wide."""
    campos = [
        ("idade", "Idade", "Demogr\u00e1fico", 1, "numerico", '["=", "!=", ">", "<", ">=", "<=", "between"]', None, "Idade do cliente em anos", "customer_features_wide", "idade", "baixa"),
        ("renda_mensal", "Renda Mensal", "Financeiro", 2, "numerico", '["=", "!=", ">", "<", ">=", "<=", "between"]', None, "Renda mensal declarada (R$)", "customer_features_wide", "renda_mensal", "alta"),
        ("segmento_comportamental", "Segmento Comportamental", "Comportamento", 3, "categorico", '["=", "!=", "in", "not_in"]', '["digital", "tradicional", "premium", "basico"]', "Segmento comportamental do cliente", "customer_features_wide", "segmento_comportamental", "baixa"),
        ("canal_preferido", "Canal Preferido", "Comportamento", 3, "categorico", '["=", "!=", "in", "not_in"]', '["app", "agencia", "internet_banking", "telefone", "whatsapp"]', "Canal de prefer\u00eancia para contato", "customer_features_wide", "canal_preferido", "baixa"),
        ("qtd_produtos_contratados", "Qtd Produtos Contratados", "Relacionamento", 4, "numerico", '["=", "!=", ">", "<", ">=", "<=", "between"]', None, "Total de produtos ativos", "customer_features_wide", "qtd_produtos_contratados", "baixa"),
        ("tempo_relacionamento_meses", "Tempo de Relacionamento", "Relacionamento", 4, "numerico", '["=", "!=", ">", "<", ">=", "<=", "between"]', None, "Tempo como cliente (meses)", "customer_features_wide", "tempo_relacionamento_meses", "baixa"),
        ("score_credito", "Score de Cr\u00e9dito", "Financeiro", 2, "numerico", '["=", "!=", ">", "<", ">=", "<=", "between"]', None, "Score de cr\u00e9dito (0-1000)", "customer_features_wide", "score_credito", "alta"),
        ("uf", "UF", "Demogr\u00e1fico", 1, "categorico", '["=", "!=", "in", "not_in"]', '["SP", "RJ", "MG", "RS", "PR", "BA", "SC", "GO", "PE", "CE"]', "Estado de resid\u00eancia", "customer_features_wide", "uf", "media"),
        ("ticket_medio", "Ticket M\u00e9dio", "Financeiro", 2, "numerico", '["=", "!=", ">", "<", ">=", "<=", "between"]', None, "Ticket m\u00e9dio de transa\u00e7\u00f5es (R$)", "customer_features_wide", "ticket_medio", "media"),
        ("frequencia_transacoes", "Frequ\u00eancia de Transa\u00e7\u00f5es", "Comportamento", 3, "numerico", '["=", "!=", ">", "<", ">=", "<=", "between"]', None, "Transa\u00e7\u00f5es/m\u00eas", "customer_features_wide", "frequencia_transacoes", "baixa"),
        ("saldo_medio", "Saldo M\u00e9dio", "Financeiro", 2, "numerico", '["=", "!=", ">", "<", ">=", "<=", "between"]', None, "Saldo m\u00e9dio em conta (R$)", "customer_features_wide", "saldo_medio", "alta"),
        ("flag_digital", "Cliente Digital", "Comportamento", 3, "booleano", '["="]', '["true", "false"]', "Se usa predominantemente canais digitais", "customer_features_wide", "flag_digital", "baixa"),
        ("profissao", "Profiss\u00e3o", "Demogr\u00e1fico", 1, "categorico", '["=", "!=", "in", "not_in"]', '["engenheiro", "medico", "advogado", "professor", "analista", "empresario", "autonomo", "aposentado"]', "Profiss\u00e3o declarada", "customer_features_wide", "profissao", "media"),
        ("estado_civil", "Estado Civil", "Demogr\u00e1fico", 1, "categorico", '["=", "!=", "in", "not_in"]', '["solteiro", "casado", "divorciado", "viuvo"]', "Estado civil", "customer_features_wide", "estado_civil", "media"),
    ]

    conn.executemany(
        """INSERT OR REPLACE INTO catalogo_caracteristicas
           (caracteristica_id, campo_label, tema, tema_ordem, tipo_dado, operadores, valores_dominio, descricao, tabela_fisica, campo_fisico, sensibilidade, ativo)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
        campos
    )


def _seed_catalogo_publicos(conn: sqlite3.Connection):
    """Seed public bases — names must match table names in the publico schema."""
    publicos = [
        ("pf_geral", "PF Geral", "Base geral de pessoas f\u00edsicas"),
        ("pj_geral", "PJ Geral", "Base geral de pessoas jur\u00eddicas"),
    ]
    conn.executemany(
        "INSERT OR REPLACE INTO catalogo_publicos (publico_id, nome, descricao, ativo) VALUES (?, ?, ?, 1)",
        publicos
    )


def _seed_publico_pf_geral(conn: sqlite3.Connection):
    """Seed PF (pessoa f\u00edsica) public base."""
    conn.executemany(
        "INSERT OR REPLACE INTO pf_geral (cpf_cnpj) VALUES (?)",
        [(cpf,) for cpf in _CPFS_PF]
    )


def _seed_publico_pj_geral(conn: sqlite3.Connection):
    """Seed PJ (pessoa jur\u00eddica) public base."""
    conn.executemany(
        "INSERT OR REPLACE INTO pj_geral (cpf_cnpj) VALUES (?)",
        [(cnpj,) for cnpj in _CPFS_PJ]
    )


def _seed_customer_features_wide(conn: sqlite3.Connection):
    """Seed feature table — columns must match catalogo_caracteristicas IDs."""
    import random
    random.seed(42)  # Reproducible

    segmentos = ["digital", "tradicional", "premium", "basico"]
    canais = ["app", "agencia", "internet_banking", "telefone", "whatsapp"]
    ufs = ["SP", "RJ", "MG", "RS", "PR", "BA", "SC", "GO", "PE", "CE"]
    profissoes = ["engenheiro", "medico", "advogado", "professor", "analista", "empresario", "autonomo", "aposentado"]
    estados_civis = ["solteiro", "casado", "divorciado", "viuvo"]

    # PF customers
    for cpf in _CPFS_PF:
        idade = random.randint(18, 75)
        renda = round(random.uniform(1500, 50000), 2)
        segmento = random.choice(segmentos)
        canal = random.choice(canais)
        produtos = random.randint(1, 8)
        tempo = random.randint(3, 240)
        score = random.randint(200, 950)
        uf = random.choice(ufs)
        ticket = round(random.uniform(50, 5000), 2)
        freq = random.randint(2, 80)
        saldo = round(random.uniform(500, 200000), 2)
        digital = 1 if segmento == "digital" or canal == "app" else 0
        profissao = random.choice(profissoes)
        estado_civil = random.choice(estados_civis)

        conn.execute(
            """INSERT OR REPLACE INTO customer_features_wide
               (cpf_cnpj, idade, renda_mensal, segmento_comportamental, canal_preferido,
                qtd_produtos_contratados, tempo_relacionamento_meses, score_credito,
                uf, ticket_medio, frequencia_transacoes, saldo_medio, flag_digital,
                profissao, estado_civil)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (cpf, idade, renda, segmento, canal, produtos, tempo, score,
             uf, ticket, freq, saldo, digital, profissao, estado_civil)
        )

    # PJ customers (simplified features)
    for cnpj in _CPFS_PJ:
        conn.execute(
            """INSERT OR REPLACE INTO customer_features_wide
               (cpf_cnpj, idade, renda_mensal, segmento_comportamental, canal_preferido,
                qtd_produtos_contratados, tempo_relacionamento_meses, score_credito,
                uf, ticket_medio, frequencia_transacoes, saldo_medio, flag_digital,
                profissao, estado_civil)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (cnpj, None, round(random.uniform(10000, 500000), 2), "premium", "internet_banking",
             random.randint(3, 15), random.randint(12, 120), random.randint(500, 950),
             random.choice(ufs), round(random.uniform(500, 50000), 2), random.randint(10, 200),
             round(random.uniform(10000, 1000000), 2), 1, "empresario", None)
        )


def _seed_campos_em_uso(conn: sqlite3.Connection):
    """Seed fields-in-use view data."""
    campos = [
        ("idade", 3, json.dumps(["seg_001", "seg_002", "seg_003"])),
        ("renda_mensal", 2, json.dumps(["seg_001", "seg_003"])),
        ("segmento_comportamental", 2, json.dumps(["seg_002", "seg_003"])),
        ("uf", 1, json.dumps(["seg_002"])),
        ("score_credito", 1, json.dumps(["seg_003"])),
    ]
    conn.executemany(
        "INSERT OR REPLACE INTO campos_em_uso (campo_id, qtd_segmentacoes_ativas, segmentacoes) VALUES (?, ?, ?)",
        campos
    )


def _seed_seg_definicao(conn: sqlite3.Connection):
    """Seed sample segmentations."""
    segmentacoes = [
        {
            "seg_id": "seg_001",
            "seg_codigo": "ALTA-RENDA-SP",
            "seg_slug": "alta-renda-sp",
            "nome": "Alta Renda S\u00e3o Paulo",
            "descricao": "Clientes de alta renda em SP para oferta premium",
            "objetivo": "aquisicao",
            "seg_tags": json.dumps(["alta-renda", "premium", "sp"]),
            "resumo": "Segmento de clientes PF com renda > R$15k em SP",
            "objetivo_negocio": "Aumentar penetra\u00e7\u00e3o de produtos premium",
            "publico_alvo_descricao": "Clientes PF de alta renda no estado de SP",
            "owner": "maria.silva@bradesco.com.br",
            "area_responsavel": "Varejo Premium",
            "email_contato": "maria.silva@bradesco.com.br",
            "criado_por": "maria.silva@bradesco.com.br",
            "publico_base_id": "pf_geral",
            "regras_json": json.dumps({
                "publico_base": "pf_geral",
                "inclusao": {
                    "operator": "AND",
                    "rules": [
                        {"campo_id": "renda_mensal", "op": ">", "value": 15000},
                        {"campo_id": "uf", "op": "=", "value": "SP"}
                    ]
                },
                "exclusao": None
            }),
            "tipo": "direta",
            "status": "ativa",
            "versao_atual": 2,
            "criado_em": "2024-11-15 10:00:00",
            "atualizado_em": "2024-12-01 14:30:00",
            "habilitado": 1,
            "agendamento_cron": "0 8 * * 1",
            "recorrencia": "semanal",
        },
        {
            "seg_id": "seg_002",
            "seg_codigo": "DIGITAL-JOVEM",
            "seg_slug": "digital-jovem",
            "nome": "Jovens Digitais",
            "descricao": "Clientes jovens com perfil digital first",
            "objetivo": "engajamento",
            "seg_tags": json.dumps(["digital", "jovem", "app"]),
            "resumo": "Segmento de clientes < 30 anos e comportamento digital",
            "objetivo_negocio": "Aumentar engajamento no app",
            "publico_alvo_descricao": "Clientes PF jovens com perfil digital",
            "owner": "joao.santos@bradesco.com.br",
            "area_responsavel": "Digital",
            "email_contato": "joao.santos@bradesco.com.br",
            "criado_por": "joao.santos@bradesco.com.br",
            "publico_base_id": "pf_geral",
            "regras_json": json.dumps({
                "publico_base": "pf_geral",
                "inclusao": {
                    "operator": "AND",
                    "rules": [
                        {"campo_id": "idade", "op": "<", "value": 30},
                        {"campo_id": "segmento_comportamental", "op": "=", "value": "digital"}
                    ]
                },
                "exclusao": None
            }),
            "tipo": "direta",
            "status": "ativa",
            "versao_atual": 1,
            "criado_em": "2024-12-01 09:00:00",
            "atualizado_em": "2024-12-10 11:00:00",
            "habilitado": 1,
            "agendamento_cron": "0 6 * * *",
            "recorrencia": "diaria",
        },
        {
            "seg_id": "seg_003",
            "seg_codigo": "RISCO-CREDITO",
            "seg_slug": "risco-credito",
            "nome": "Monitoramento Risco Cr\u00e9dito",
            "descricao": "Clientes com score baixo e alta renda para a\u00e7\u00e3o preventiva",
            "objetivo": "retencao",
            "seg_tags": json.dumps(["risco", "credito", "preventivo"]),
            "resumo": "Score < 400 e renda > R$5k",
            "objetivo_negocio": "Redu\u00e7\u00e3o de inadimpl\u00eancia",
            "publico_alvo_descricao": "Clientes com risco elevado mas potencial de reten\u00e7\u00e3o",
            "owner": "ana.costa@bradesco.com.br",
            "area_responsavel": "Gest\u00e3o de Riscos",
            "email_contato": "ana.costa@bradesco.com.br",
            "criado_por": "ana.costa@bradesco.com.br",
            "publico_base_id": "pf_geral",
            "regras_json": json.dumps({
                "publico_base": "pf_geral",
                "inclusao": {
                    "operator": "AND",
                    "rules": [
                        {"campo_id": "score_credito", "op": "<", "value": 400},
                        {"campo_id": "renda_mensal", "op": ">=", "value": 5000}
                    ]
                },
                "exclusao": {
                    "operator": "AND",
                    "rules": [
                        {"campo_id": "idade", "op": "<", "value": 18}
                    ]
                }
            }),
            "tipo": "direta",
            "status": "rascunho",
            "versao_atual": 1,
            "criado_em": "2025-01-05 15:00:00",
            "atualizado_em": "2025-01-05 15:00:00",
            "habilitado": 1,
            "agendamento_cron": None,
            "recorrencia": None,
        },
    ]

    for seg in segmentacoes:
        conn.execute(
            """INSERT OR REPLACE INTO seg_definicao
               (seg_id, seg_codigo, seg_slug, nome, descricao, objetivo, seg_tags,
                resumo, objetivo_negocio, publico_alvo_descricao, owner,
                area_responsavel, email_contato, criado_por, publico_base_id,
                regras_json, tipo, status, versao_atual, criado_em, atualizado_em,
                habilitado, agendamento_cron, recorrencia)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (seg["seg_id"], seg["seg_codigo"], seg["seg_slug"], seg["nome"],
             seg["descricao"], seg["objetivo"], seg["seg_tags"], seg["resumo"],
             seg["objetivo_negocio"], seg["publico_alvo_descricao"], seg["owner"],
             seg["area_responsavel"], seg["email_contato"], seg["criado_por"],
             seg["publico_base_id"], seg["regras_json"], seg["tipo"], seg["status"],
             seg["versao_atual"], seg["criado_em"], seg["atualizado_em"],
             seg["habilitado"], seg["agendamento_cron"], seg["recorrencia"])
        )


def _seed_seg_saude(conn: sqlite3.Connection):
    """Seed health data — references seg_definicao.seg_id."""
    saudes = [
        ("seg_001", "verde", "2025-01-10 08:15:00", 2.3, 98.5, 12.4, json.dumps([]), 4500),
        ("seg_002", "amarelo", "2025-01-10 06:30:00", -8.1, 95.0, 8.7, json.dumps([{"tipo": "variacao", "msg": "Varia\u00e7\u00e3o > 5%"}]), 1200),
        ("seg_003", "vermelho", "2025-01-09 15:00:00", 0.0, 0.0, 0.0, json.dumps([{"tipo": "sem_execucao", "msg": "Nunca executada"}]), 0),
    ]
    conn.executemany(
        """INSERT OR REPLACE INTO seg_saude
           (seg_id, health_status, ultima_verificacao, variacao_publico_pct,
            taxa_sucesso_exec, tempo_medio_exec_seg, alertas_json, publico_atual)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        saudes
    )


def _seed_seg_comentario(conn: sqlite3.Connection):
    """Seed sample comments."""
    comentarios = [
        ("com_aaa111", "seg_001", 1, "geral", "maria.silva@bradesco.com.br",
         "Segmenta\u00e7\u00e3o criada para campanha Q1 2025", None, json.dumps([]), 0,
         "2024-11-15 10:05:00", None),
        ("com_bbb222", "seg_001", 2, "aprovacao", "joao.santos@bradesco.com.br",
         "Aprovado. Regras validadas com a \u00e1rea de neg\u00f3cio.", None, json.dumps(["maria.silva@bradesco.com.br"]), 1,
         "2024-12-01 14:35:00", None),
        ("com_ccc333", "seg_002", 1, "geral", "joao.santos@bradesco.com.br",
         "Verificar se o crit\u00e9rio de idade est\u00e1 ok com compliance", None, json.dumps([]), 0,
         "2024-12-01 09:10:00", None),
    ]
    conn.executemany(
        """INSERT OR REPLACE INTO seg_comentario
           (comentario_id, seg_id, versao_referencia, tipo, autor, texto,
            respondendo_a, mencoes, resolvido, criado_em, editado_em)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        comentarios
    )


def _seed_seg_notificacao(conn: sqlite3.Connection):
    """Seed sample notifications."""
    notificacoes = [
        ("notif_001", "maria.silva@bradesco.com.br", "aprovacao", "seg_001",
         "Segmenta\u00e7\u00e3o aprovada", "Sua segmenta\u00e7\u00e3o 'Alta Renda SP' foi aprovada.",
         1, "2024-12-01 14:35:00"),
        ("notif_002", "joao.santos@bradesco.com.br", "saude", "seg_002",
         "Alerta de sa\u00fade", "A segmenta\u00e7\u00e3o 'Jovens Digitais' teve varia\u00e7\u00e3o > 5%.",
         0, "2025-01-10 06:35:00"),
    ]
    conn.executemany(
        """INSERT OR REPLACE INTO seg_notificacao
           (notif_id, destinatario, tipo, seg_id, titulo, mensagem, lida, criado_em)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        notificacoes
    )


def _seed_seg_execucao(conn: sqlite3.Connection):
    """Seed execution history."""
    execucoes = [
        ("exec_001", "seg_001", "sucesso", "2025-01-06 08:00:00", "2025-01-06 08:12:24", 4500, None, 2),
        ("exec_002", "seg_001", "sucesso", "2024-12-30 08:00:00", "2024-12-30 08:11:50", 4398, None, 2),
        ("exec_003", "seg_002", "sucesso", "2025-01-10 06:00:00", "2025-01-10 06:08:42", 1200, None, 1),
        ("exec_004", "seg_002", "erro", "2025-01-09 06:00:00", "2025-01-09 06:02:10", 0, "Timeout no warehouse", 1),
    ]
    conn.executemany(
        """INSERT OR REPLACE INTO seg_execucao
           (exec_id, seg_id, status, inicio, fim, publico_gerado, erro, versao)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        execucoes
    )


def _seed_seg_job_log(conn: sqlite3.Connection):
    """Seed job audit log."""
    logs = [
        ("log_001", "seg_001", "criar", "job_12345", None, "sucesso", "Job criado com cron 0 8 * * 1", "2024-12-01 14:40:00"),
        ("log_002", "seg_002", "criar", "job_12346", None, "sucesso", "Job criado com cron 0 6 * * *", "2024-12-10 11:05:00"),
        ("log_003", "seg_001", "executar", "job_12345", "run_99001", "sucesso", "Execu\u00e7\u00e3o manual", "2025-01-06 08:00:00"),
    ]
    conn.executemany(
        """INSERT OR REPLACE INTO seg_job_log
           (log_id, seg_id, acao, job_id, run_id, status, detalhes, criado_em)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        logs
    )


# ============================================================
# CLI: run directly to (re)create the database
# ============================================================
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    target = sys.argv[1] if len(sys.argv) > 1 else None
    seed_database(target)
    print(f"\n\u2705 Banco criado em: {target or Path(__file__).parent / 'local.db'}")
