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

SEG_ID = dbutils.widgets.get("seg_id")
ORIGEM = dbutils.widgets.get("origem_execucao")

assert SEG_ID, "Parâmetro seg_id é obrigatório"
print(f"▶ Executando segmentação: {SEG_ID} | Origem: {ORIGEM}")

# Schemas
CATALOG = "plataforma"
SCHEMA_SEG = "segmentacao"
SCHEMA_META = "metadata"

# COMMAND ----------

# ============================================================
# STEP 1: Carregar definição da segmentação
# ============================================================

df_definicao = spark.sql(f"""
  SELECT seg_id, nome, regras_json, versao_atual, status, publico_base_id,
         vigencia_inicio, vigencia_fim, agendamento_cron
  FROM {CATALOG}.{SCHEMA_SEG}.seg_definicao
  WHERE seg_id = '{SEG_ID}'
    AND habilitado = true
""")

if df_definicao.count() == 0:
    dbutils.notebook.exit(json.dumps({
        "status": "erro",
        "mensagem": f"Segmentação {SEG_ID} não encontrada ou desabilitada"
    }))

seg = df_definicao.collect()[0]
print(f"✓ Segmentação carregada: {seg['nome']} (v{seg['versao_atual']})")
print(f"  Status: {seg['status']}")

# Validação de status
if seg["status"] not in ("ativa", "aprovada"):
    dbutils.notebook.exit(json.dumps({
        "status": "ignorado",
        "mensagem": f"Status '{seg['status']}' não permite execução"
    }))

# Validação de vigência
agora = datetime.now(timezone.utc)
if seg["vigencia_fim"] and seg["vigencia_fim"] < agora:
    dbutils.notebook.exit(json.dumps({
        "status": "expirado",
        "mensagem": f"Vigência encerrada em {seg['vigencia_fim']}"
    }))

regras = json.loads(seg["regras_json"]) if isinstance(seg["regras_json"], str) else seg["regras_json"]
print(f"✓ Regras carregadas (público base: {regras.get('publico_base')})")

# COMMAND ----------

# DBTITLE 1,Step 2: Montar query SQL a partir das regras
# ============================================================
# STEP 2: Montar e executar query SQL a partir das regras
# ============================================================

def build_condition(node: dict, catalogo_df) -> str:
    """
    Converte um nó de regra (RegraNo) em SQL WHERE condition.
    Recursivo: suporta grupos aninhados.
    """
    if "rules" not in node:
        return "1=1"

    conditions = []
    for rule in node["rules"]:
        if "rules" in rule:
            # Grupo aninhado
            sub = build_condition(rule, catalogo_df)
            conditions.append(f"({sub})")
        else:
            # Folha: {campo_id, op, value}
            campo_id = rule["campo_id"]
            op = rule["op"]
            value = rule.get("value")

            # Resolve campo físico via catálogo
            campo_info = catalogo_df.filter(
                F.col("caracteristica_id") == campo_id
            ).first()

            if not campo_info:
                raise ValueError(f"Campo {campo_id} não encontrado no catálogo")

            col_fisico = f"{campo_info['tabela_fisica']}.{campo_info['campo_fisico']}"

            # Helper: formata valor para SQL com escape de aspas
            def sql_val(v):
                if isinstance(v, bool):
                    return str(v).lower()  # True → true (Spark syntax)
                if isinstance(v, str):
                    escaped = v.replace("'", "''")
                    return f"'{escaped}'"
                return str(v)

            # Monta condição SQL
            if op == "is_null":
                conditions.append(f"{col_fisico} IS NULL")
            elif op == "is_not_null":
                conditions.append(f"{col_fisico} IS NOT NULL")
            elif op == "in":
                vals = ", ".join([sql_val(v) for v in value])
                conditions.append(f"{col_fisico} IN ({vals})")
            elif op == "not_in":
                vals = ", ".join([sql_val(v) for v in value])
                conditions.append(f"{col_fisico} NOT IN ({vals})")
            elif op == "between":
                conditions.append(f"{col_fisico} BETWEEN {sql_val(value[0])} AND {sql_val(value[1])}")
            elif op == "contains":
                escaped = str(value).replace("'", "''")
                conditions.append(f"{col_fisico} LIKE '%{escaped}%'")
            elif op == "starts_with":
                escaped = str(value).replace("'", "''")
                conditions.append(f"{col_fisico} LIKE '{escaped}%'")
            else:
                # Operadores simples: =, !=, >, <, >=, <=
                conditions.append(f"{col_fisico} {op} {sql_val(value)}")

    operator = f" {node.get('operator', 'AND')} "
    return operator.join(conditions)


# Carrega catálogo de características
catalogo_df = spark.table(f"{CATALOG}.{SCHEMA_META}.catalogo_caracteristicas").filter("ativo = true")

# Identifica tabelas envolvidas nas regras (para JOINs)
def extrair_tabelas(node: dict) -> set:
    tabelas = set()
    for rule in node.get("rules", []):
        if "rules" in rule:
            tabelas.update(extrair_tabelas(rule))
        else:
            campo_info = catalogo_df.filter(
                F.col("caracteristica_id") == rule["campo_id"]
            ).first()
            if campo_info:
                tabelas.add((campo_info["tabela_fisica"], campo_info["join_key"]))
    return tabelas


# Resolve público base
publico_base = regras["publico_base"]
df_publicos = spark.table(f"{CATALOG}.{SCHEMA_META}.catalogo_publicos")
publico_info = df_publicos.filter(F.col("publico_id") == publico_base).first()

if not publico_info:
    raise ValueError(f"Público base '{publico_base}' não encontrado")

tabela_base = publico_info["tabela_fisica"]
join_key_base = publico_info["join_key"]

print(f"✓ Público base: {publico_info['nome']} → {tabela_base} (key: {join_key_base})")

# Monta WHERE (inclusão)
inclusao_where = build_condition(regras["inclusao"], catalogo_df)

# Monta WHERE (exclusão, se existir)
exclusao_where = None
if regras.get("exclusao"):
    exclusao_where = build_condition(regras["exclusao"], catalogo_df)

# Resolve JOINs necessários
tabelas_inclusao = extrair_tabelas(regras["inclusao"])
tabelas_exclusao = extrair_tabelas(regras.get("exclusao", {})) if regras.get("exclusao") else set()
tabelas_todas = tabelas_inclusao | tabelas_exclusao

# Monta JOINs
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

# COMMAND ----------

# ============================================================
# STEP 3: Executar query e medir resultado
# ============================================================

t0 = time.time()
df_resultado = spark.sql(query_sql)
qtd_clientes = df_resultado.count()
tempo_exec = round(time.time() - t0, 2)

print(f"\n✓ Resultado: {qtd_clientes:,} clientes em {tempo_exec}s")

# COMMAND ----------

# ============================================================
# STEP 4: Persistir resultado
# ============================================================

exec_id = f"exec_{SEG_ID}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
exec_timestamp = datetime.now(timezone.utc)

# 4a. MERGE em seg_resultado_corrente (snapshot atual)
df_resultado.createOrReplaceTempView("resultado_novo")

spark.sql(f"""
  MERGE INTO {CATALOG}.{SCHEMA_SEG}.seg_resultado_corrente AS target
  USING (
    SELECT '{SEG_ID}' AS seg_id, cpf_cnpj
    FROM resultado_novo
  ) AS source
  ON target.seg_id = source.seg_id AND target.cpf_cnpj = source.cpf_cnpj
  WHEN NOT MATCHED THEN INSERT (seg_id, cpf_cnpj, exec_id, entrou_em)
    VALUES (source.seg_id, source.cpf_cnpj, '{exec_id}', current_timestamp())
  WHEN NOT MATCHED BY SOURCE AND target.seg_id = '{SEG_ID}' THEN DELETE
""")

print(f"✓ seg_resultado_corrente atualizado (MERGE)")

# 4b. INSERT em seg_resultado_historico (auditoria)
# DDL order: exec_id, seg_id, versao_usada, cpf_cnpj, snapshot_em
spark.sql(f"""
  INSERT INTO {CATALOG}.{SCHEMA_SEG}.seg_resultado_historico
  (exec_id, seg_id, versao_usada, cpf_cnpj, snapshot_em)
  SELECT '{exec_id}',
         '{SEG_ID}',
         {seg['versao_atual']},
         cpf_cnpj,
         current_timestamp()
  FROM resultado_novo
""")

print(f"✓ seg_resultado_historico inserido ({qtd_clientes} registros)")

# COMMAND ----------

# ============================================================
# STEP 5: Registrar execução em seg_execucao
# ============================================================

# Obtem job_id e run_id do contexto Databricks
try:
    context = json.loads(dbutils.notebook.entry_point.getDbutils().notebook().getContext().toJson())
    job_id = context.get("tags", {}).get("jobId", "")
    run_id = context.get("tags", {}).get("multitaskParentRunId", "") or context.get("tags", {}).get("runId", "")
    job_run_url = f"/jobs/{job_id}/runs/{run_id}" if job_id else ""
except Exception:
    job_id, run_id, job_run_url = "", "", ""

spark.sql(f"""
  INSERT INTO {CATALOG}.{SCHEMA_SEG}.seg_execucao
  VALUES (
    '{exec_id}',
    '{SEG_ID}',
    {seg['versao_atual']},
    '{ORIGEM}',
    current_timestamp(),
    {qtd_clientes},
    'sucesso',
    '{job_id}',
    '{run_id}',
    '{job_run_url}'
  )
""")

print(f"✓ Execução registrada: {exec_id}")

# COMMAND ----------

# ============================================================
# STEP 6: Atualizar saúde individual (seg_saude)
# ============================================================

# Busca execução anterior para calcular variação
df_exec_anterior = spark.sql(f"""
  SELECT qtd_clientes
  FROM {CATALOG}.{SCHEMA_SEG}.seg_execucao
  WHERE seg_id = '{SEG_ID}'
    AND status = 'sucesso'
    AND exec_id != '{exec_id}'
  ORDER BY executado_em DESC
  LIMIT 1
""")

publico_anterior = None
if df_exec_anterior.count() > 0:
    publico_anterior = df_exec_anterior.collect()[0]["qtd_clientes"]

variacao_pct = 0.0
if publico_anterior and publico_anterior > 0:
    variacao_pct = round(((qtd_clientes - publico_anterior) / publico_anterior) * 100, 2)

# Taxa de sucesso (últimas 10 execuções)
df_taxa = spark.sql(f"""
  SELECT
    COUNT(CASE WHEN status = 'sucesso' THEN 1 END) * 100.0 / COUNT(*) AS taxa
  FROM (
    SELECT status FROM {CATALOG}.{SCHEMA_SEG}.seg_execucao
    WHERE seg_id = '{SEG_ID}'
    ORDER BY executado_em DESC
    LIMIT 10
  )
""")
taxa_sucesso = round(df_taxa.collect()[0]["taxa"], 1) if df_taxa.count() > 0 else 100.0

# Tempo médio (últimas 10)
df_tempo = spark.sql(f"""
  SELECT AVG(tempo_exec_seg) AS media
  FROM (
    SELECT TIMESTAMPDIFF(SECOND, executado_em, current_timestamp()) AS tempo_exec_seg
    FROM {CATALOG}.{SCHEMA_SEG}.seg_execucao
    WHERE seg_id = '{SEG_ID}' AND status = 'sucesso'
    ORDER BY executado_em DESC
    LIMIT 10
  )
""")
tempo_medio = tempo_exec  # usa tempo atual como aproximação

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

# MERGE em seg_saude
spark.sql(f"""
  MERGE INTO {CATALOG}.{SCHEMA_SEG}.seg_saude AS target
  USING (SELECT '{SEG_ID}' AS seg_id) AS source
  ON target.seg_id = source.seg_id
  WHEN MATCHED THEN UPDATE SET
    health_status = '{health_status}',
    ultima_verificacao = current_timestamp(),
    variacao_publico_pct = {variacao_pct},
    taxa_sucesso_exec = {taxa_sucesso},
    tempo_medio_exec_seg = CAST({tempo_exec} AS INT),
    alertas_json = '{json.dumps(alertas)}',
    publico_atual = {qtd_clientes}
  WHEN NOT MATCHED THEN INSERT
    (seg_id, health_status, ultima_verificacao, variacao_publico_pct,
     taxa_sucesso_exec, tempo_medio_exec_seg, alertas_json, publico_atual)
  VALUES
    ('{SEG_ID}', '{health_status}', current_timestamp(), {variacao_pct},
     {taxa_sucesso}, CAST({tempo_exec} AS INT), '{json.dumps(alertas)}', {qtd_clientes})
""")

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
