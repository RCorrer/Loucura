# Databricks notebook source
# S1-JOB-04: seg_overlap (sobreposições) - 100% PySpark

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, when, lit, current_timestamp
spark = SparkSession.builder.getOrCreate()

# 1. Carrega resultado corrente dos segmentos ativos
df_result = spark.sql("""
    SELECT seg_id, cpf_cnpj
    FROM plataforma.segmentacao.seg_resultado_corrente
    WHERE seg_id IN (SELECT seg_id FROM plataforma.segmentacao.seg_definicao WHERE status = 'ativa')
""")

# 2. Auto-join para pares
df_pairs = df_result.alias("a") \
    .join(df_result.alias("b"), col("a.cpf_cnpj") == col("b.cpf_cnpj")) \
    .filter(col("a.seg_id") < col("b.seg_id")) \
    .groupBy(col("a.seg_id").alias("seg_id_a"), col("b.seg_id").alias("seg_id_b")) \
    .agg(count("*").alias("clientes_em_comum"))

# 3. Calcula totais por segmento
df_totals = df_result.groupBy("seg_id").agg(count("*").alias("total"))

# 4. Calcula percentuais
df_overlap = df_pairs \
    .join(df_totals.alias("ta"), col("seg_id_a") == col("ta.seg_id")) \
    .join(df_totals.alias("tb"), col("seg_id_b") == col("tb.seg_id")) \
    .withColumn("pct_sobre_a", (col("clientes_em_comum") / col("ta.total") * 100)) \
    .withColumn("pct_sobre_b", (col("clientes_em_comum") / col("tb.total") * 100)) \
    .withColumn("calculado_em", current_timestamp()) \
    .select("seg_id_a", "seg_id_b", "clientes_em_comum", "pct_sobre_a", "pct_sobre_b", "calculado_em")

# 5. Upsert em seg_overlap
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

# 6. Alerta de alta sobreposição (>80%)
spark.sql("""
    INSERT INTO plataforma.segmentacao.seg_notificacao
    (notif_id, destinatario, tipo, seg_id, titulo, mensagem)
    SELECT
        concat('notif_', uuid()),
        d.owner,
        'alerta',
        o.seg_id_a,
        concat('⚠️ Alta sobreposição: ', o.seg_id_a, ' x ', o.seg_id_b),
        concat('Sobreposição de ', round(greatest(o.pct_sobre_a, o.pct_sobre_b), 2), '% entre ', o.seg_id_a, ' e ', o.seg_id_b)
    FROM plataforma.segmentacao.seg_overlap o
    JOIN plataforma.segmentacao.seg_definicao d ON o.seg_id_a = d.seg_id
    WHERE (o.pct_sobre_a > 80 OR o.pct_sobre_b > 80)
      AND d.owner IS NOT NULL
      AND NOT EXISTS (
          SELECT 1 FROM plataforma.segmentacao.seg_notificacao n
          WHERE n.seg_id = o.seg_id_a AND n.tipo = 'alerta' AND n.criado_em > current_timestamp() - INTERVAL 1 DAY
      )
""")

print("✅ Overlap calculado")