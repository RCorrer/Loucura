"""Configurações centrais do EngagementHub (S3)."""

import os

# Unity Catalog
CATALOG = os.getenv("UC_CATALOG", "plataforma")
SCHEMA_ENG = "engagement"
SCHEMA_SEG = "segmentacao"  # consumo S1
SCHEMA_META = "metadata"     # consumo S1 (variáveis)
SCHEMA_GOV = "governanca"    # consentimento + RBAC
SCHEMA_CORE = "core_cliente"  # golden_record
SCHEMA_EVENTOS = "eventos"   # barramento

# Tabelas externas consumidas
TABLE_SEG_RESULTADO = f"{CATALOG}.{SCHEMA_SEG}.seg_resultado_corrente"
TABLE_SEG_DEFINICAO = f"{CATALOG}.{SCHEMA_SEG}.seg_definicao"
TABLE_SEG_DESTINO = f"{CATALOG}.{SCHEMA_SEG}.seg_destino"
TABLE_CONSENTIMENTO = f"{CATALOG}.{SCHEMA_GOV}.consentimento"
TABLE_FEATURES_WIDE = f"{CATALOG}.caracteristicas.customer_features_wide"
TABLE_GOLDEN_RECORD = f"{CATALOG}.{SCHEMA_CORE}.golden_record"
TABLE_RETORNO_ATEND = f"{CATALOG}.{SCHEMA_EVENTOS}.retorno_atendimento"

# Tabelas internas principais
TABLE_CAMPANHA = f"{CATALOG}.{SCHEMA_ENG}.campanha"
TABLE_JORNADA = f"{CATALOG}.{SCHEMA_ENG}.jornada"
TABLE_PECA = f"{CATALOG}.{SCHEMA_ENG}.peca"
TABLE_FILA = f"{CATALOG}.{SCHEMA_ENG}.fila_disparo"
TABLE_TRACKING = f"{CATALOG}.{SCHEMA_ENG}.tracking_disparo"
TABLE_SUPRESSAO = f"{CATALOG}.{SCHEMA_ENG}.supressao_log"
TABLE_CAPPING = f"{CATALOG}.{SCHEMA_ENG}.regras_capping"
TABLE_PRIORIDADE = f"{CATALOG}.{SCHEMA_ENG}.campanha_prioridade"
TABLE_CANAIS = f"{CATALOG}.{SCHEMA_ENG}.catalogo_canais"
TABLE_ESTADO_CLIENTE = f"{CATALOG}.{SCHEMA_ENG}.jornada_estado_cliente"
TABLE_SAUDE_OP = f"{CATALOG}.{SCHEMA_ENG}.saude_operacional"
TABLE_NOTIFICACAO = f"{CATALOG}.{SCHEMA_ENG}.notificacao"
TABLE_CAMPANHA_JORNADA = f"{CATALOG}.{SCHEMA_ENG}.campanha_jornada"
TABLE_JORNADA_PARTICIPACAO = f"{CATALOG}.{SCHEMA_ENG}.jornada_participacao"
TABLE_CONFIG_JANELA = f"{CATALOG}.{SCHEMA_ENG}.config_janela_envio"
TABLE_EXECUCAO_ORQUESTRADOR = f"{CATALOG}.{SCHEMA_ENG}.execucao_orquestrador"
TABLE_JORNADA_LOG = f"{CATALOG}.{SCHEMA_ENG}.jornada_log"
TABLE_POLITICA_JORNADA = f"{CATALOG}.{SCHEMA_ENG}.config_jornada_politica"
TABLE_DISPARO_TENTATIVA = f"{CATALOG}.{SCHEMA_ENG}.disparo_tentativa"
TABLE_CONFIG_RETRY = f"{CATALOG}.{SCHEMA_ENG}.config_retry"
TABLE_DISPARO_EVENTOS = f"{CATALOG}.{SCHEMA_ENG}.disparo_eventos"

# App
APP_NAME = "EngagementHub"
APP_VERSION = "0.1.0"
