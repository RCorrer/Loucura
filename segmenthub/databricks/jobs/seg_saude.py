# Databricks notebook source
# S1-JOB-03: seg_saude (health checks) - 100% PySpark

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, when, max, min, avg, lit, current_timestamp
spark = SparkSession.builder.getOrCreate()

# 1. Para cada segmento ativo/pausado/aprovado, calcula métricas
df_exec = spark.sql("""
    SELECT seg_id, status, qtd_clientes, executado_em
    FROM plataforma.segmentacao.seg_execucao
    WHERE seg_id IN (SELECT seg_id FROM plataforma.segmentacao.seg_definicao WHERE status IN ('ativa','pausada','aprovada'))
    ORDER BY executado_em DESC
""")

# Agrupa por seg_id
df_metrics = df_exec.groupBy("seg_id").agg(
    count("*").alias("total_exec"),
    count(when(col("status") == "sucesso", 1)).alias("sucessos"),
    count(when(col("status").isin(["erro", "erro_metadado"]), 1)).alias("falhas"),
    max("qtd_clientes").alias("max_publico"),
    min("qtd_clientes").alias("min_publico"),
    avg("qtd_clientes").alias("media_publico"),
    max("executado_em").alias("ultima_exec")
)

# Para cada segmento, determina status de saúde (verde/amarelo/vermelho)
df_saude = df_metrics.select(
    col("seg_id"),
    when(col("falhas") >= 2, lit("vermelho"))
    .when((col("falhas") == 1) | (col("max_publico") == 0), lit("amarelo"))
    .otherwise(lit("verde")).alias("health_status"),
    lit(current_timestamp()).alias("ultima_verificacao"),
    col("max_publico").alias("publico_atual"),
    # alertas_json (simplificado)
    when(col("falhas") >= 2, lit('{"tipo":"falha_recente"}'))
    .otherwise(lit(None)).alias("alertas_json")
)

# Upsert em seg_saude usando MERGE
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

# Gera notificações para segmentos vermelhos
spark.sql("""
    INSERT INTO plataforma.segmentacao.seg_notificacao
    (notif_id, destinatario, tipo, seg_id, titulo, mensagem)
    SELECT
        concat('notif_', uuid()),
        d.owner,
        'alerta',
        s.seg_id,
        concat('🔴 Saúde crítica: ', s.seg_id),
        concat('Segmentação ', s.seg_id, ' em estado vermelho. Verifique os alertas.')
    FROM plataforma.segmentacao.seg_saude s
    JOIN plataforma.segmentacao.seg_definicao d ON s.seg_id = d.seg_id
    WHERE s.health_status = 'vermelho'
      AND d.owner IS NOT NULL
      AND NOT EXISTS (
          SELECT 1 FROM plataforma.segmentacao.seg_notificacao n
          WHERE n.seg_id = s.seg_id AND n.tipo = 'alerta' AND n.criado_em > current_timestamp() - INTERVAL 1 HOUR
      )
""")

print("✅ Saúde atualizada")