# Databricks notebook source
# S1-JOB-03: seg_saude (health checks) - 100% PySpark

# COMMAND ----------

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, when, max, min, avg, lit, current_timestamp, expr, coalesce, greatest
from delta.tables import DeltaTable

spark = SparkSession.builder.getOrCreate()

# ============================================================
# 1. Carrega segmentos ativos/pausados/aprovados
# ============================================================
df_segmentos = spark.table("plataforma.segmentacao.seg_definicao") \
    .filter(col("status").isin(["ativa", "pausada", "aprovada"])) \
    .select("seg_id", "owner")

# ============================================================
# 2. Carrega execuções para esses segmentos
# ============================================================
df_exec = spark.table("plataforma.segmentacao.seg_execucao") \
    .filter(col("seg_id").isin([row.seg_id for row in df_segmentos.select("seg_id").collect()])) \
    .select("seg_id", "status", "qtd_clientes", "executado_em")

# ============================================================
# 3. Calcula métricas por segmento (agg)
# ============================================================
df_metrics = df_exec.groupBy("seg_id").agg(
    count("*").alias("total_exec"),
    count(when(col("status") == "sucesso", 1)).alias("sucessos"),
    count(when(col("status").isin(["erro", "erro_metadado"]), 1)).alias("falhas"),
    max("qtd_clientes").alias("max_publico"),
    min("qtd_clientes").alias("min_publico"),
    avg("qtd_clientes").alias("media_publico"),
    max("executado_em").alias("ultima_exec")
)

# ============================================================
# 4. Determina status de saúde (regras)
# ============================================================
df_saude = df_metrics.select(
    col("seg_id"),
    # Regra: 2+ falhas → vermelho; 1 falha ou público zero → amarelo; senão verde
    when(col("falhas") >= 2, lit("vermelho"))
    .when((col("falhas") == 1) | (col("max_publico") == 0), lit("amarelo"))
    .otherwise(lit("verde")).alias("health_status"),
    lit(current_timestamp()).alias("ultima_verificacao"),
    col("max_publico").alias("publico_atual"),
    # Alerta JSON (simplificado)
    when(col("falhas") >= 2, lit('{"tipo":"falha_recente"}'))
    .when(col("max_publico") == 0, lit('{"tipo":"publico_zerado"}'))
    .otherwise(lit(None)).alias("alertas_json")
)

# ============================================================
# 5. Upsert em seg_saude via DeltaTable.merge
# ============================================================
delta_saude = DeltaTable.forName(spark, "plataforma.segmentacao.seg_saude")

# Cria DataFrame com os dados a serem inseridos/atualizados
df_upsert = df_saude.select(
    "seg_id",
    "health_status",
    "ultima_verificacao",
    "publico_atual",
    "alertas_json"
)

delta_saude.alias("target") \
    .merge(
        df_upsert.alias("source"),
        "target.seg_id = source.seg_id"
    ) \
    .whenMatchedUpdate(set={
        "health_status": col("source.health_status"),
        "ultima_verificacao": col("source.ultima_verificacao"),
        "publico_atual": col("source.publico_atual"),
        "alertas_json": col("source.alertas_json")
    }) \
    .whenNotMatchedInsert(values={
        "seg_id": col("source.seg_id"),
        "health_status": col("source.health_status"),
        "ultima_verificacao": col("source.ultima_verificacao"),
        "publico_atual": col("source.publico_atual"),
        "alertas_json": col("source.alertas_json")
    }) \
    .execute()

# ============================================================
# 6. Notificações para segmentos vermelhos (apenas se não enviada nas últimas 24h)
# ============================================================
# 6a. Busca notificações existentes nas últimas 24h
df_notif_existente = spark.table("plataforma.segmentacao.seg_notificacao") \
    .filter(col("tipo") == "alerta") \
    .filter(col("criado_em") > expr("current_timestamp() - interval 1 day")) \
    .select("seg_id")

# 6b. Junta com segmentos vermelhos que ainda não foram notificados
df_vermelho = df_saude \
    .filter(col("health_status") == "vermelho") \
    .join(df_segmentos.select("seg_id", "owner"), on="seg_id", how="inner") \
    .filter(col("owner").isNotNull()) \
    .join(
        df_notif_existente.select("seg_id").distinct(),
        on="seg_id",
        how="left_anti"
    )

# 6c. Gera notificações
if df_vermelho.count() > 0:
    # Prepara dados para notificação
    df_notif = df_vermelho.select(
        col("seg_id"),
        col("owner").alias("destinatario"),
        lit("alerta").alias("tipo"),
        col("seg_id").alias("seg_id_notif"),  # nome diferente para evitar conflito
        expr("concat('🔴 Saúde crítica: ', seg_id)").alias("titulo"),
        expr("concat('Segmentação ', seg_id, ' em estado vermelho. Verifique os alertas.')").alias("mensagem")
    ).select(
        expr("concat('notif_', uuid())").alias("notif_id"),
        "destinatario",
        "tipo",
        "seg_id_notif",
        "titulo",
        "mensagem"
    )
    
    # Insere notificações
    df_notif.write.mode("append").saveAsTable("plataforma.segmentacao.seg_notificacao")
    print(f"🔔 {df_vermelho.count()} notificações enviadas para segmentos vermelhos")
else:
    print("ℹ️ Nenhuma notificação necessária (sem segmentos vermelhos ou já notificados)")

# ============================================================
# 7. Finaliza
# ============================================================
print("✅ Saúde atualizada")