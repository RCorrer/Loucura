# Databricks notebook source
# S1-JOB-02: seg_guardiao (vigência) - PySpark puro (sem spark.sql)

# COMMAND ----------

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit, current_timestamp, when, expr, to_timestamp
from delta.tables import DeltaTable

spark = SparkSession.builder.getOrCreate()

# ============================================================
# 1. Lê tabela de definição
# ============================================================
df_def = spark.table("plataforma.segmentacao.seg_definicao") \
    .filter(col("habilitado") == True) \
    .select("seg_id", "status", "vigencia_inicio", "vigencia_fim")

# ============================================================
# 2. Identifica segmentações a ativar (aprovadas com vigência iniciada)
# ============================================================
df_ativar = df_def \
    .filter(col("status") == "aprovada") \
    .filter(col("vigencia_inicio") <= current_timestamp()) \
    .select("seg_id")

# ============================================================
# 3. Identifica segmentações a encerrar (ativas com vigência expirada)
# ============================================================
df_encerrar = df_def \
    .filter(col("status") == "ativa") \
    .filter(col("vigencia_fim") <= current_timestamp()) \
    .select("seg_id")

# ============================================================
# 4. Coleta IDs (para usar no merge e histórico)
# ============================================================
ids_ativar = [row.seg_id for row in df_ativar.collect()]
ids_encerrar = [row.seg_id for row in df_encerrar.collect()]

# ============================================================
# 5. Aplica atualizações via DeltaTable.merge (sem SQL)
# ============================================================
delta_table = DeltaTable.forName(spark, "plataforma.segmentacao.seg_definicao")

# 5a. Ativar
if ids_ativar:
    # Cria DataFrame com os IDs e o novo status
    df_update_ativar = spark.createDataFrame([(seg_id, "ativa") for seg_id in ids_ativar], ["seg_id", "novo_status"])
    delta_table.alias("target") \
        .merge(
            df_update_ativar.alias("source"),
            "target.seg_id = source.seg_id"
        ) \
        .whenMatchedUpdate(set={
            "status": col("source.novo_status"),
            "atualizado_em": current_timestamp()
        }) \
        .execute()
    print(f"✅ Ativadas: {len(ids_ativar)}")

# 5b. Encerrar
if ids_encerrar:
    df_update_encerrar = spark.createDataFrame([(seg_id, "encerrada") for seg_id in ids_encerrar], ["seg_id", "novo_status"])
    delta_table.alias("target") \
        .merge(
            df_update_encerrar.alias("source"),
            "target.seg_id = source.seg_id"
        ) \
        .whenMatchedUpdate(set={
            "status": col("source.novo_status"),
            "atualizado_em": current_timestamp()
        }) \
        .execute()
    print(f"⛔ Encerradas: {len(ids_encerrar)}")

# ============================================================
# 6. Insere histórico APENAS para os segmentos que mudaram
# ============================================================
if ids_ativar or ids_encerrar:
    # Prepara dados para histórico
    hist_rows = []
    if ids_ativar:
        for seg_id in ids_ativar:
            hist_rows.append((seg_id, "aprovada", "ativa", "guardiao_vigencia", "system"))
    if ids_encerrar:
        for seg_id in ids_encerrar:
            hist_rows.append((seg_id, "ativa", "encerrada", "guardiao_vigencia", "system"))
    
    if hist_rows:
        # Cria DataFrame com o histórico
        df_hist = spark.createDataFrame(
            hist_rows,
            ["seg_id", "estado_anterior", "estado_novo", "motivo", "alterado_por"]
        ).withColumn("hist_id", expr("concat('hist_', uuid()")) \
         .withColumn("alterado_em", current_timestamp()) \
         .select("hist_id", "seg_id", "estado_anterior", "estado_novo", "motivo", "alterado_por", "alterado_em")
        
        # Insere via append na tabela de histórico
        df_hist.write.mode("append").saveAsTable("plataforma.segmentacao.seg_historico_estado")
        print(f"✅ Histórico registrado para {len(hist_rows)} segmentações")

# ============================================================
# 7. Finaliza
# ============================================================
if not ids_ativar and not ids_encerrar:
    print("ℹ️ Nenhuma segmentação com vigência a ser alterada.")

print("✅ Guardião concluído")