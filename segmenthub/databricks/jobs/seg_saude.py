# Databricks notebook source
# S1-JOB-03: seg_saude - 100% PySpark DataFrames

from pyspark.sql import SparkSession, functions as F
from pyspark.sql.window import Window
import uuid, json
spark = SparkSession.builder.getOrCreate()

# 1. Lista segmentos ativos/pausados/aprovados
df_segmentos = spark.table("plataforma.segmentacao.seg_definicao") \
    .filter(F.col("status").isin(["ativa", "pausada", "aprovada"])) \
    .select("seg_id", "owner")

# 2. Para cada segmento, obter execuções recentes
df_exec = spark.table("plataforma.segmentacao.seg_execucao") \
    .filter(F.col("seg_id").isin([row.seg_id for row in df_segmentos.select("seg_id").collect()])) \
    .withColumn("rank", F.row_number().over(Window.partitionBy("seg_id").orderBy(F.desc("executado_em")))) \
    .filter(F.col("rank") <= 3) \
    .select("seg_id", "status", "qtd_clientes", "executado_em")

# 3. Agrega métricas
df_metrics = df_exec.groupBy("seg_id").agg(
    F.count("*").alias("total_exec"),
    F.sum(F.when(F.col("status") == "sucesso", 1).otherwise(0)).alias("sucessos"),
    F.sum(F.when(F.col("status").isin(["erro", "erro_metadado"]), 1).otherwise(0)).alias("falhas"),
    F.max("qtd_clientes").alias("max_publico"),
    F.min("qtd_clientes").alias("min_publico"),
    F.avg("qtd_clientes").alias("media_publico"),
    F.max("executado_em").alias("ultima_exec")
)

# 4. Calcula status de saúde
df_saude = df_metrics.select(
    F.col("seg_id"),
    F.when(F.col("falhas") >= 2, F.lit("vermelho"))
     .when((F.col("falhas") == 1) | (F.col("max_publico") == 0), F.lit("amarelo"))
     .otherwise(F.lit("verde")).alias("health_status"),
    F.current_timestamp().alias("ultima_verificacao"),
    F.col("max_publico").alias("publico_atual"),
    F.when(F.col("falhas") >= 2, F.lit(json.dumps({"tipo":"falha_recente"}))).otherwise(F.lit(None)).alias("alertas_json")
)

# 5. Upsert em seg_saude (usando DeltaTable)
from delta.tables import DeltaTable
deltaTable = DeltaTable.forName(spark, "plataforma.segmentacao.seg_saude")
# É necessário fazer merge manual: criar tabela temporária e usar merge
df_saude.createOrReplaceTempView("saude_temp")
spark.sql("""
    MERGE INTO plataforma.segmentacao.seg_saude AS target
    USING saude_temp AS source
    ON target.seg_id = source.seg_id
    WHEN MATCHED THEN
        UPDATE SET
            health_status = source.health_status,
            ultima_verificacao = source.ultima_verificacao,
            publico_atual = source.publico_atual,
            alertas_json = source.alertas_json
    WHEN NOT MATCHED THEN
        INSERT (seg_id, health_status, ultima_verificacao, publico_atual, alertas_json)
        VALUES (source.seg_id, source.health_status, source.ultima_verificacao,
                source.publico_atual, source.alertas_json)
""")

# 6. Notificações para vermelhos (usando DataFrame)
df_vermelhos = spark.table("plataforma.segmentacao.seg_saude") \
    .filter(F.col("health_status") == "vermelho") \
    .select("seg_id") \
    .join(spark.table("plataforma.segmentacao.seg_definicao").select("seg_id", "owner"), "seg_id") \
    .filter(F.col("owner").isNotNull())

if df_vermelhos.count() > 0:
    df_notif = df_vermelhos.select(
        F.concat(F.lit("notif_"), F.expr("uuid()")).alias("notif_id"),
        F.col("owner").alias("destinatario"),
        F.lit("alerta").alias("tipo"),
        F.col("seg_id"),
        F.concat(F.lit("🔴 Saúde crítica: "), F.col("seg_id")).alias("titulo"),
        F.concat(F.lit("Segmentação "), F.col("seg_id"), F.lit(" em estado vermelho. Verifique os alertas.")).alias("mensagem")
    )
    df_notif.write.mode("append").saveAsTable("plataforma.segmentacao.seg_notificacao")

print("✅ Saúde atualizada")