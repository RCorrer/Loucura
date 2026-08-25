# Databricks notebook source
"""
===============================================================================
S1-JOB: seg_exec — Execução de Segmentação Individual
===============================================================================

Notebook parametrizado que executa UMA segmentação.
Cada segmentação ativa possui seu próprio Databricks Job apontando para
este notebook com o parâmetro `seg_id`.

Parâmetros (via dbutils.widgets):
  - seg_id: ID da segmentação a executar
  - origem_execucao: 'agendada' | 'manual' | 'reativacao'

Fluxo:
  1. Carrega definição da segmentação (regras_json, versao_atual)
  2. Valida pré-condições (status ativa, regras válidas)
  3. Gera e executa a query SQL a partir das regras
  4. Persiste resultado em seg_resultado_corrente e seg_resultado_historico
  5. Atualiza métricas de saúde individual (seg_saude)
  6. Registra execução em seg_execucao

Tabelas envolvidas:
  - plataforma.segmentacao.seg_definicao (leitura)
  - plataforma.segmentacao.seg_execucao (escrita)
  - plataforma.segmentacao.seg_resultado_corrente (escrita — MERGE)
  - plataforma.segmentacao.seg_resultado_historico (escrita — INSERT)
  - plataforma.segmentacao.seg_saude (escrita — MERGE)

Autor: SegmentHub Platform
Versão: 2.0 (arquitetura job-per-segment)
===============================================================================
"""

# COMMAND ----------

# DBTITLE 1,Setup: Parâmetros e imports
# ============================================================
# SETUP: Parâmetros e imports
# ============================================================

import json
import time
from datetime import datetime, timezone
from pyspark.sql import functions as F

# Parâmetros do Job
dbutils.widgets.text("seg_id", "", "ID da Segmentação")
dbutils.widgets.text("origem_execucao", "agendada", "Origem (agendada/manual/reativacao)")
dbutils.widgets.text("exec_id", "", "ID da Execução (propagado pelo service, vazio se agendada)")

SEG_ID = dbutils.widgets.get("seg_id")
ORIGEM = dbutils.widgets.get("origem_execucao")

# RF-01/RF-02: Se exec_id foi propagado pelo service, reutiliza (UPDATE no final).
# Se vazio (execução agendada), gera novo exec_id (INSERT no final).
EXEC_ID_PARAM = dbutils.widgets.get("exec_id").strip() or None
IS_PREREGISTERED = EXEC_ID_PARAM is not None

assert SEG_ID, "Parâmetro seg_id é obrigatório"
print(f"▶ Executando segmentação: {SEG_ID} | Origem: {ORIGEM}")
if IS_PREREGISTERED:
    print(f"  exec_id propagado: {EXEC_ID_PARAM} (será UPDATE no final)")
else:
    print(f"  exec_id será gerado pelo job (INSERT no final)")

# Schemas
CATALOG = "plataforma"
SCHEMA_SEG = "segmentacao"
SCHEMA_META = "metadata"


def _marcar_exec_erro(motivo: str):
    """Atualiza registro pré-registrado para 'erro' em caso de saída prematura.
    Só atua se IS_PREREGISTERED (execução manual com exec_id do service).
    Para execuções agendadas (sem pré-registro), não há registro a atualizar."""
    if not IS_PREREGISTERED:
        return
    try:
        spark.sql(
            f"""UPDATE {CATALOG}.{SCHEMA_SEG}.seg_execucao
            SET status = 'erro', qtd_clientes = 0
            WHERE exec_id = :exec_id AND status = 'em_execucao'""",
            args={"exec_id": EXEC_ID_PARAM}
        )
        print(f"⚠️ Execução {EXEC_ID_PARAM} marcada como 'erro': {motivo}")
    except Exception as e:
        print(f"❌ Falha ao marcar execução como erro: {e}")

# COMMAND ----------

# DBTITLE 1,Step 1: Carregar definição da segmentação
# ============================================================
# STEP 1: Carregar definição da segmentação
# ============================================================

df_definicao = spark.sql(
    f"""SELECT seg_id, nome, regras_json, versao_atual, status, publico_base_id,
           vigencia_inicio, vigencia_fim, agendamento_cron
    FROM {CATALOG}.{SCHEMA_SEG}.seg_definicao
    WHERE seg_id = :seg_id
      AND habilitado = true""",
    args={"seg_id": SEG_ID}
)

if df_definicao.count() == 0:
    _marcar_exec_erro(f"Segmentação {SEG_ID} não encontrada ou desabilitada")
    dbutils.notebook.exit(json.dumps({
        "status": "erro",
        "mensagem": f"Segmentação {SEG_ID} não encontrada ou desabilitada"
    }))

seg = df_definicao.collect()[0]
print(f"✓ Segmentação carregada: {seg['nome']} (v{seg['versao_atual']})")
print(f"  Status: {seg['status']}")

# Validação de status
if seg["status"] not in ("ativa", "aprovada"):
    _marcar_exec_erro(f"Status '{seg['status']}' não permite execução")
    dbutils.notebook.exit(json.dumps({
        "status": "erro",
        "mensagem": f"Status '{seg['status']}' não permite execução"
    }))

# Validação de vigência (usa naive datetime para compatibilidade com Spark timestamps)
agora = datetime.utcnow()
if seg["vigencia_fim"] and seg["vigencia_fim"] < agora:
    _marcar_exec_erro(f"Vigência encerrada em {seg['vigencia_fim']}")
    dbutils.notebook.exit(json.dumps({
        "status": "erro",
        "mensagem": f"Vigência encerrada em {seg['vigencia_fim']}"
    }))

regras = json.loads(seg["regras_json"]) if isinstance(seg["regras_json"], str) else seg["regras_json"]
print(f"✓ Regras carregadas (público base: {regras.get('publico_base')})")

# COMMAND ----------

# DBTITLE 1,Step 2: Montar query SQL a partir das regras
# ============================================================
# STEP 2: Montar e executar query SQL a partir das regras
# ============================================================
# RF-05: Queries parametrizadas (Spark 3.4+).
# - Nomes de tabela/coluna (do catálogo confiável) → identifiers (f-string)
# - VALORES das regras (input do usuário) → named params (:p0, :p1...)
# ============================================================

# Whitelist de operadores válidos (defesa contra regras corrompidas)
OPS_VALIDOS = {"=", "!=", ">", "<", ">=", "<=", "in", "not_in",
               "between", "contains", "starts_with", "ends_with",
               "not_contains", "not_starts_with", "not_ends_with",
               "is_null", "is_not_null"}

# Materializa catálogo como dict para lookup O(1) (evita N filter().first())
catalogo_df = spark.table(f"{CATALOG}.{SCHEMA_META}.catalogo_caracteristicas").filter("ativo = true")
_catalogo_rows = catalogo_df.collect()
catalogo_dict = {row["caracteristica_id"]: row.asDict() for row in _catalogo_rows}

# Contador global de parâmetros (para nomes únicos entre inclusão + exclusão)
_param_counter = [0]

def _next_param() -> str:
    """Gera nome de parâmetro único sequencial: p0, p1, p2..."""
    name = f"p{_param_counter[0]}"
    _param_counter[0] += 1
    return name


def build_condition(node: dict) -> tuple:
    """
    Converte nó de regra em (sql_where_string, params_dict).
    Valores são parametrizados com :pN; identifiers (tabela.coluna) ficam inline.
    Recursivo: suporta grupos aninhados.
    """
    if not node.get("rules"):
        return "1=1", {}

    conditions = []
    params = {}

    for rule in node["rules"]:
        if "rules" in rule:
            # Grupo aninhado
            sub_sql, sub_params = build_condition(rule)
            conditions.append(f"({sub_sql})")
            params.update(sub_params)
        else:
            # Folha: {campo_id, op, value}
            campo_id = rule["campo_id"]
            op = rule["op"]
            value = rule.get("value")

            # Valida operador contra whitelist
            if op not in OPS_VALIDOS:
                raise ValueError(f"Operador inválido '{op}' para campo {campo_id}")

            # Resolve campo físico via dict (O(1))
            campo_info = catalogo_dict.get(campo_id)
            if not campo_info:
                raise ValueError(f"Campo {campo_id} não encontrado no catálogo")

            col_fisico = f"{campo_info['tabela_fisica']}.{campo_info['campo_fisico']}"

            # Monta condição SQL com parâmetros nomeados
            if op == "is_null":
                conditions.append(f"{col_fisico} IS NULL")
            elif op == "is_not_null":
                conditions.append(f"{col_fisico} IS NOT NULL")
            elif op == "in":
                pnames = []
                for v in value:
                    pn = _next_param()
                    params[pn] = v
                    pnames.append(f":{pn}")
                conditions.append(f"{col_fisico} IN ({', '.join(pnames)})")
            elif op == "not_in":
                pnames = []
                for v in value:
                    pn = _next_param()
                    params[pn] = v
                    pnames.append(f":{pn}")
                conditions.append(f"{col_fisico} NOT IN ({', '.join(pnames)})")
            elif op == "between":
                p_lo, p_hi = _next_param(), _next_param()
                params[p_lo] = value[0]
                params[p_hi] = value[1]
                conditions.append(f"{col_fisico} BETWEEN :{p_lo} AND :{p_hi}")
            elif op == "contains":
                pn = _next_param()
                params[pn] = f"%{value}%"
                conditions.append(f"{col_fisico} LIKE :{pn}")
            elif op == "not_contains":
                pn = _next_param()
                params[pn] = f"%{value}%"
                conditions.append(f"{col_fisico} NOT LIKE :{pn}")
            elif op == "starts_with":
                pn = _next_param()
                params[pn] = f"{value}%"
                conditions.append(f"{col_fisico} LIKE :{pn}")
            elif op == "not_starts_with":
                pn = _next_param()
                params[pn] = f"{value}%"
                conditions.append(f"{col_fisico} NOT LIKE :{pn}")
            elif op == "ends_with":
                pn = _next_param()
                params[pn] = f"%{value}"
                conditions.append(f"{col_fisico} LIKE :{pn}")
            elif op == "not_ends_with":
                pn = _next_param()
                params[pn] = f"%{value}"
                conditions.append(f"{col_fisico} NOT LIKE :{pn}")
            else:
                # Operadores simples: =, !=, >, <, >=, <=
                pn = _next_param()
                params[pn] = value
                conditions.append(f"{col_fisico} {op} :{pn}")

    operator = f" {node.get('operator', 'AND')} "
    return operator.join(conditions), params


# Identifica tabelas envolvidas nas regras (para JOINs) — usa dict O(1)
def extrair_tabelas(node: dict) -> set:
    tabelas = set()
    for rule in node.get("rules", []):
        if "rules" in rule:
            tabelas.update(extrair_tabelas(rule))
        else:
            campo_info = catalogo_dict.get(rule["campo_id"])
            if campo_info:
                tabelas.add((campo_info["tabela_fisica"], campo_info["join_key"]))
    return tabelas


# Resolve público base
publico_base = regras["publico_base"]
df_publicos = spark.table(f"{CATALOG}.{SCHEMA_META}.catalogo_publicos")
publico_info = df_publicos.filter(F.col("publico_id") == publico_base).first()

if not publico_info:
    _marcar_exec_erro(f"Público base '{publico_base}' não encontrado")
    dbutils.notebook.exit(json.dumps({
        "status": "erro", "mensagem": f"Público base '{publico_base}' não encontrado"
    }))

tabela_base = publico_info["tabela_fisica"]
join_key_base = publico_info["join_key"]

print(f"✓ Público base: {publico_info['nome']} → {tabela_base} (key: {join_key_base})")

# Monta WHERE parametrizado (inclusão)
inclusao_where, inclusao_params = build_condition(regras["inclusao"])

# Monta WHERE parametrizado (exclusão, se existir)
exclusao_where, exclusao_params = None, {}
if regras.get("exclusao"):
    exclusao_where, exclusao_params = build_condition(regras["exclusao"])

# Combina todos os params
query_params = {**inclusao_params, **exclusao_params}

# Resolve JOINs necessários
tabelas_inclusao = extrair_tabelas(regras["inclusao"])
tabelas_exclusao = extrair_tabelas(regras.get("exclusao", {})) if regras.get("exclusao") else set()
tabelas_todas = tabelas_inclusao | tabelas_exclusao

# Monta JOINs (identifiers confiáveis do catálogo)
joins_sql = ""
for tabela, join_key in tabelas_todas:
    if tabela != tabela_base:
        joins_sql += f"\n  LEFT JOIN {tabela} ON {tabela}.{join_key} = {tabela_base}.{join_key_base}"

# Query final — alias cpf_cnpj alinhado com DDL seg_resultado_corrente
query_sql = f"""
SELECT DISTINCT {tabela_base}.{join_key_base} AS cpf_cnpj
FROM {tabela_base}{joins_sql}
WHERE ({inclusao_where})
"""

if exclusao_where:
    query_sql += f"  AND NOT ({exclusao_where})\n"

print(f"\n📋 Query gerada:\n{query_sql}")
print(f"🔒 Parâmetros ({len(query_params)}): {list(query_params.keys())}")

# COMMAND ----------

# DBTITLE 1,Step 3: Executar query e medir resultado
# ============================================================
# STEP 3: Executar query e medir resultado
# ============================================================

try:
    t0 = time.time()
    df_resultado = spark.sql(query_sql, args=query_params)
    qtd_clientes = df_resultado.count()
    tempo_exec = round(time.time() - t0, 2)
    print(f"\n✓ Resultado: {qtd_clientes:,} clientes em {tempo_exec}s")
except Exception as e:
    _marcar_exec_erro(f"Erro na execução da query: {e}")
    dbutils.notebook.exit(json.dumps({
        "status": "erro",
        "mensagem": f"Erro na execução SQL: {str(e)[:500]}"
    }))

# COMMAND ----------

# DBTITLE 1,Step 4: Persistir resultado
# ============================================================
# STEP 4: Persistir resultado
# ============================================================

try:
    # RF-01: Reutiliza exec_id do service (se propagado) ou gera novo (execução agendada)
    exec_id = EXEC_ID_PARAM or f"exec_{SEG_ID}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
exec_timestamp = datetime.utcnow()

# 4a. MERGE em seg_resultado_corrente (snapshot atual)
df_resultado.createOrReplaceTempView("resultado_novo")

spark.sql(
    f"""MERGE INTO {CATALOG}.{SCHEMA_SEG}.seg_resultado_corrente AS target
    USING (
      SELECT :seg_id AS seg_id, cpf_cnpj
      FROM resultado_novo
    ) AS source
    ON target.seg_id = source.seg_id AND target.cpf_cnpj = source.cpf_cnpj
    WHEN NOT MATCHED THEN INSERT (seg_id, cpf_cnpj, exec_id, entrou_em)
      VALUES (source.seg_id, source.cpf_cnpj, :exec_id, current_timestamp())
    WHEN NOT MATCHED BY SOURCE AND target.seg_id = :seg_id THEN DELETE""",
    args={"seg_id": SEG_ID, "exec_id": exec_id}
)

print(f"✓ seg_resultado_corrente atualizado (MERGE)")

# 4b. INSERT em seg_resultado_historico (auditoria)
spark.sql(
    f"""INSERT INTO {CATALOG}.{SCHEMA_SEG}.seg_resultado_historico
    (exec_id, seg_id, versao_usada, cpf_cnpj, snapshot_em)
    SELECT :exec_id, :seg_id, :versao, cpf_cnpj, current_timestamp()
    FROM resultado_novo""",
    args={"exec_id": exec_id, "seg_id": SEG_ID, "versao": seg["versao_atual"]}
)

    print(f"✓ seg_resultado_historico inserido ({qtd_clientes} registros)")
except Exception as e:
    _marcar_exec_erro(f"Erro ao persistir resultado: {e}")
    dbutils.notebook.exit(json.dumps({
        "status": "erro",
        "mensagem": f"Erro ao persistir: {str(e)[:500]}"
    }))

# COMMAND ----------

# DBTITLE 1,Step 5: Registrar execução em seg_execucao
# ============================================================
# STEP 5: Registrar execução em seg_execucao
# ============================================================
# RF-01/RF-02: Se exec_id veio do service (IS_PREREGISTERED), o registro
# já existe com status 'em_execucao' → UPDATE para 'sucesso'.
# Se exec_id foi gerado aqui (agendada) → INSERT novo registro.
# ============================================================

# Obtem job_id e run_id do contexto Databricks
try:
    context = json.loads(dbutils.notebook.entry_point.getDbutils().notebook().getContext().toJson())
    job_id = context.get("tags", {}).get("jobId", "")
    run_id = context.get("tags", {}).get("multitaskParentRunId", "") or context.get("tags", {}).get("runId", "")
    job_run_url = f"/jobs/{job_id}/runs/{run_id}" if job_id else ""
except Exception:
    job_id, run_id, job_run_url = "", "", ""

# Params comuns para UPDATE e INSERT
_exec_params = {
    "exec_id": exec_id,
    "seg_id": SEG_ID,
    "versao": seg["versao_atual"],
    "origem": ORIGEM,
    "qtd": qtd_clientes,
    "p_job_id": job_id or None,
    "p_run_id": run_id or None,
    "p_job_run_url": job_run_url or None,
}

if IS_PREREGISTERED:
    # UPDATE: registro já existe (criado pelo service antes do disparo)
    spark.sql(
        f"""UPDATE {CATALOG}.{SCHEMA_SEG}.seg_execucao
        SET status = 'sucesso',
            versao_usada = :versao,
            executado_em = current_timestamp(),
            qtd_clientes = :qtd,
            job_id = :p_job_id,
            run_id = :p_run_id,
            job_run_url = :p_job_run_url
        WHERE exec_id = :exec_id""",
        args=_exec_params
    )
    print(f"✓ Execução atualizada (UPDATE): {exec_id}")
else:
    # INSERT: execução agendada (sem registro prévio)
    spark.sql(
        f"""INSERT INTO {CATALOG}.{SCHEMA_SEG}.seg_execucao
        (exec_id, seg_id, versao_usada, origem_execucao, executado_em,
         qtd_clientes, status, job_id, run_id, job_run_url)
        VALUES (:exec_id, :seg_id, :versao, :origem, current_timestamp(),
                :qtd, 'sucesso', :p_job_id, :p_run_id, :p_job_run_url)""",
        args=_exec_params
    )
    print(f"✓ Execução registrada (INSERT): {exec_id}")

# COMMAND ----------

# DBTITLE 1,Step 6: Atualizar saúde individual (seg_saude)
# ============================================================
# STEP 6: Atualizar saúde individual (seg_saude)
# ============================================================

# Busca execução anterior para calcular variação
df_exec_anterior = spark.sql(
    f"""SELECT qtd_clientes
    FROM {CATALOG}.{SCHEMA_SEG}.seg_execucao
    WHERE seg_id = :seg_id AND status = 'sucesso' AND exec_id != :exec_id
    ORDER BY executado_em DESC LIMIT 1""",
    args={"seg_id": SEG_ID, "exec_id": exec_id}
)

publico_anterior = None
if df_exec_anterior.count() > 0:
    publico_anterior = df_exec_anterior.collect()[0]["qtd_clientes"]

variacao_pct = 0.0
if publico_anterior and publico_anterior > 0:
    variacao_pct = round(((qtd_clientes - publico_anterior) / publico_anterior) * 100, 2)

# Taxa de sucesso (últimas 10 execuções)
df_taxa = spark.sql(
    f"""SELECT
      COUNT(CASE WHEN status = 'sucesso' THEN 1 END) * 100.0 / COUNT(*) AS taxa
    FROM (
      SELECT status FROM {CATALOG}.{SCHEMA_SEG}.seg_execucao
      WHERE seg_id = :seg_id
      ORDER BY executado_em DESC LIMIT 10
    )""",
    args={"seg_id": SEG_ID}
)
taxa_sucesso = round(df_taxa.collect()[0]["taxa"], 1) if df_taxa.count() > 0 else 100.0

# Tempo da execução atual (já medido no Step 3)
tempo_medio = tempo_exec

# Determina health status
alertas = []
if abs(variacao_pct) > 30:
    alertas.append(f"Variação de público: {variacao_pct:+.1f}%")
if taxa_sucesso < 80:
    alertas.append(f"Taxa de sucesso baixa: {taxa_sucesso}%")
if tempo_exec > 300:  # > 5min
    alertas.append(f"Execução lenta: {tempo_exec}s")

if taxa_sucesso < 70 or abs(variacao_pct) > 50:
    health_status = "vermelho"
elif alertas:
    health_status = "amarelo"
else:
    health_status = "verde"

# MERGE em seg_saude (parametrizado)
_saude_params = {
    "seg_id": SEG_ID,
    "health": health_status,
    "variacao": variacao_pct,
    "taxa": taxa_sucesso,
    "tempo": int(tempo_exec),
    "alertas": json.dumps(alertas),
    "publico": qtd_clientes,
}

spark.sql(
    f"""MERGE INTO {CATALOG}.{SCHEMA_SEG}.seg_saude AS target
    USING (SELECT :seg_id AS seg_id) AS source
    ON target.seg_id = source.seg_id
    WHEN MATCHED THEN UPDATE SET
      health_status = :health,
      ultima_verificacao = current_timestamp(),
      variacao_publico_pct = :variacao,
      taxa_sucesso_exec = :taxa,
      tempo_medio_exec_seg = :tempo,
      alertas_json = :alertas,
      publico_atual = :publico
    WHEN NOT MATCHED THEN INSERT
      (seg_id, health_status, ultima_verificacao, variacao_publico_pct,
       taxa_sucesso_exec, tempo_medio_exec_seg, alertas_json, publico_atual)
    VALUES
      (:seg_id, :health, current_timestamp(), :variacao,
       :taxa, :tempo, :alertas, :publico)""",
    args=_saude_params
)

print(f"✓ Saúde atualizada: {health_status.upper()} (variação: {variacao_pct:+.1f}%)")

# COMMAND ----------

# ============================================================
# FIM: Retorno de sucesso
# ============================================================

result = {
    "status": "sucesso",
    "seg_id": SEG_ID,
    "exec_id": exec_id,
    "qtd_clientes": qtd_clientes,
    "tempo_exec_seg": tempo_exec,
    "health_status": health_status,
    "versao": seg["versao_atual"],
}

print(f"\n{'='*60}")
print(f"✅ EXECUÇÃO CONCLUÍDA")
print(f"   Segmentação: {seg['nome']}")
print(f"   Clientes:    {qtd_clientes:,}")
print(f"   Tempo:       {tempo_exec}s")
print(f"   Saúde:       {health_status.upper()}")
print(f"{'='*60}")

dbutils.notebook.exit(json.dumps(result))
