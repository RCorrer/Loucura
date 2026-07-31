# Databricks notebook source
# S1-JOB-04: seg_overlap - 100% PySpark DataFrames

from pyspark.sql import SparkSession, functions as F
from delta.tables import DeltaTable
import uuid
spark = SparkSession.builder.getOrCreate()

# 1. Carrega resultado corrente dos segmentos ativos
df_seg_ativos = spark.table("plataforma.segmentacao.seg_definicao") \
    .filter(F.col("status") == "ativa") \
    .select("seg_id")

if df_seg_ativos.count() < 2:
    print("Menos de 2 segmentos ativos. Nada a calcular.")
    dbutils.notebook.exit("Sem segmentos suficientes")

df_result = spark.table("plataforma.segmentacao.seg_resultado_corrente") \
    .filter(F.col("seg_id").isin([row.seg_id for row in df_seg_ativos.collect()]))

# 2. Auto-join para pares (a e b)
df_pairs = df_result.alias("a") \
    .join(df_result.alias("b"), F.col("a.cpf_cnpj") == F.col("b.cpf_cnpj")) \
    .filter(F.col("a.seg_id") < F.col("b.seg_id")) \
    .groupBy(F.col("a.seg_id").alias("seg_id_a"), F.col("b.seg_id").alias("seg_id_b")) \
    .agg(F.count("*").alias("clientes_em_comum"))

# 3. Totais por segmento
df_totals = df_result.groupBy("seg_id").agg(F.count("*").alias("total"))

# 4. Percentuais
df_overlap = df_pairs \
    .join(df_totals.alias("ta"), F.col("seg_id_a") == F.col("ta.seg_id")) \
    .join(df_totals.alias("tb"), F.col("seg_id_b") == F.col("tb.seg_id")) \
    .withColumn("pct_sobre_a", F.col("clientes_em_comum") / F.col("ta.total") * 100) \
    .withColumn("pct_sobre_b", F.col("clientes_em_comum") / F.col("tb.total") * 100) \
    .withColumn("calculado_em", F.current_timestamp()) \
    .select("seg_id_a", "seg_id_b", "clientes_em_comum", "pct_sobre_a", "pct_sobre_b", "calculado_em")

# 5. Upsert em seg_overlap (via MERGE)
df_overlap.createOrReplaceTempView("overlap_temp")
spark.sql("""
    MERGE INTO plataforma.segmentacao.seg_overlap AS target
    USING overlap_temp AS source
    ON target.seg_id_a = source.seg_id_a AND target.seg_id_b = source.seg_id_b
    WHEN MATCHED THEN
        UPDATE SET
            clientes_em_comum = source.clientes_em_comum,
            pct_sobre_a = source.pct_sobre_a,
            pct_sobre_b = source.pct_sobre_b,
            calculado_em = source.calculado_em
    WHEN NOT MATCHED THEN
        INSERT (seg_id_a, seg_id_b, clientes_em_comum, pct_sobre_a, pct_sobre_b, calculado_em)
        VALUES (source.seg_id_a, source.seg_id_b, source.clientes_em_comum,
                source.pct_sobre_a, source.pct_sobre_b, source.calculado_em)
""")

# 6. Alertas de alta sobreposição (>80%)
df_alerta = spark.table("plataforma.segmentacao.seg_overlap") \
    .filter((F.col("pct_sobre_a") > 80) | (F.col("pct_sobre_b") > 80)) \
    .select("seg_id_a", "seg_id_b", F.greatest("pct_sobre_a", "pct_sobre_b").alias("max_pct"))

if df_alerta.count() > 0:
    # Buscar owners
    df_owners = spark.table("plataforma.segmentacao.seg_definicao") \
        .filter(F.col("seg_id").isin([row.seg_id_a for row in df_alerta.collect()]) |
                F.col("seg_id").isin([row.seg_id_b for row in df_alerta.collect()])) \
        .select("seg_id", "owner") \
        .filter(F.col("owner").isNotNull())

    # Juntar para gerar notificações (para cada par, notificar ambos os owners)
    df_notif = df_alerta \
        .join(df_owners.alias("oa"), F.col("seg_id_a") == F.col("oa.seg_id")) \
        .select(
            F.concat(F.lit("notif_"), F.expr("uuid()")).alias("notif_id"),
            F.col("oa.owner").alias("destinatario"),
            F.lit("alerta").alias("tipo"),
            F.col("seg_id_a").alias("seg_id"),
            F.concat(F.lit("⚠️ Alta sobreposição: "), F.col("seg_id_a"), F.lit(" x "), F.col("seg_id_b")).alias("titulo"),
            F.concat(F.lit("Sobreposição de "), F.round(F.col("max_pct"), 2), F.lit("% entre "), F.col("seg_id_a"), F.lit(" e "), F.col("seg_id_b")).alias("mensagem")
        )
    df_notif.write.mode("append").saveAsTable("plataforma.segmentacao.seg_notificacao")

print("✅ Overlap calculado")