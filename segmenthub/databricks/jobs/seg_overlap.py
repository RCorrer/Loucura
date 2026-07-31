# Databricks notebook source
# S1-JOB-04: seg_overlap (sobreposições) - com deduplicação de notificações

# COMMAND ----------

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, when, lit, current_timestamp, expr, greatest
from delta.tables import DeltaTable

spark = SparkSession.builder.getOrCreate()

# ============================================================
# 1. Carrega segmentos ativos
# ============================================================
df_segmentos = spark.table("plataforma.segmentacao.seg_definicao") \
    .filter(col("status") == "ativa") \
    .select("seg_id", "owner")

# Lista de IDs ativos (para uso em joins)
ids_ativos = [row.seg_id for row in df_segmentos.select("seg_id").collect()]

if len(ids_ativos) < 2:
    print("⚠️ Menos de 2 segmentos ativos. Nada a calcular.")
    dbutils.notebook.exit("Sem segmentos ativos suficientes")

# ============================================================
# 2. Carrega resultado corrente para os segmentos ativos
# ============================================================
df_result = spark.table("plataforma.segmentacao.seg_resultado_corrente") \
    .filter(col("seg_id").isin(ids_ativos)) \
    .select("seg_id", "cpf_cnpj")

# ============================================================
# 3. Calcula sobreposições (auto-join)
# ============================================================
df_pairs = df_result.alias("a") \
    .join(df_result.alias("b"), col("a.cpf_cnpj") == col("b.cpf_cnpj")) \
    .filter(col("a.seg_id") < col("b.seg_id")) \
    .groupBy(col("a.seg_id").alias("seg_id_a"), col("b.seg_id").alias("seg_id_b")) \
    .agg(count("*").alias("clientes_em_comum"))

# ============================================================
# 4. Calcula totais por segmento
# ============================================================
df_totals = df_result.groupBy("seg_id").agg(count("*").alias("total"))

# ============================================================
# 5. Calcula percentuais
# ============================================================
df_overlap = df_pairs \
    .join(df_totals.alias("ta"), col("seg_id_a") == col("ta.seg_id")) \
    .join(df_totals.alias("tb"), col("seg_id_b") == col("tb.seg_id")) \
    .withColumn("pct_sobre_a", (col("clientes_em_comum") / col("ta.total")) * 100) \
    .withColumn("pct_sobre_b", (col("clientes_em_comum") / col("tb.total")) * 100) \
    .withColumn("calculado_em", current_timestamp()) \
    .select("seg_id_a", "seg_id_b", "clientes_em_comum", "pct_sobre_a", "pct_sobre_b", "calculado_em")

# ============================================================
# 6. Upsert em seg_overlap via DeltaTable.merge
# ============================================================
delta_overlap = DeltaTable.forName(spark, "plataforma.segmentacao.seg_overlap")

delta_overlap.alias("target") \
    .merge(
        df_overlap.alias("source"),
        "target.seg_id_a = source.seg_id_a AND target.seg_id_b = source.seg_id_b"
    ) \
    .whenMatchedUpdate(set={
        "clientes_em_comum": col("source.clientes_em_comum"),
        "pct_sobre_a": col("source.pct_sobre_a"),
        "pct_sobre_b": col("source.pct_sobre_b"),
        "calculado_em": col("source.calculado_em")
    }) \
    .whenNotMatchedInsert(values={
        "seg_id_a": col("source.seg_id_a"),
        "seg_id_b": col("source.seg_id_b"),
        "clientes_em_comum": col("source.clientes_em_comum"),
        "pct_sobre_a": col("source.pct_sobre_a"),
        "pct_sobre_b": col("source.pct_sobre_b"),
        "calculado_em": col("source.calculado_em")
    }) \
    .execute()

print(f"✅ Overlap calculado para {df_overlap.count()} pares")

# ============================================================
# 7. Identifica overlaps com alta sobreposição (> 80%)
# ============================================================
df_alto_overlap = df_overlap \
    .filter((col("pct_sobre_a") > 80) | (col("pct_sobre_b") > 80)) \
    .select(
        col("seg_id_a"),
        col("seg_id_b"),
        greatest(col("pct_sobre_a"), col("pct_sobre_b")).alias("max_pct")
    )

if df_alto_overlap.count() == 0:
    print("ℹ️ Nenhuma sobreposição acima de 80%")
else:
    # ============================================================
    # 8. DEDUPLICAÇÃO: busca notificações existentes nas últimas 24h
    # ============================================================
    df_existing_alerts = spark.table("plataforma.segmentacao.seg_notificacao") \
        .filter(col("tipo") == "alerta") \
        .filter(col("titulo").like("%sobreposição%")) \
        .filter(col("criado_em") > (current_timestamp() - expr("INTERVAL 1 DAY"))) \
        .select(col("seg_id").alias("alerted_seg_id")) \
        .distinct()

    # ============================================================
    # 9. Prepara notificações (apenas para segmentos que NÃO foram alertados recentemente)
    # ============================================================
    # Junta com owners (apenas seg_id_a recebe a notificação, pois é o owner do primeiro segmento)
    df_notif_base = df_alto_overlap \
        .join(df_segmentos.alias("d"), col("seg_id_a") == col("d.seg_id")) \
        .filter(col("d.owner").isNotNull()) \
        .select(
            col("seg_id_a").alias("seg_id"),
            col("d.owner").alias("destinatario"),
            col("seg_id_b"),
            col("max_pct")
        ) \
        .join(
            df_existing_alerts,
            col("seg_id") == col("alerted_seg_id"),
            how="left_anti"
        )

    # ============================================================
    # 10. Insere notificações (se houver novas)
    # ============================================================
    if df_notif_base.count() > 0:
        df_notif = df_notif_base.select(
            expr("concat('notif_', uuid())").alias("notif_id"),
            col("destinatario"),
            lit("alerta").alias("tipo"),
            col("seg_id"),
            expr("concat('⚠️ Alta sobreposição: ', seg_id, ' x ', seg_id_b)").alias("titulo"),
            expr("concat('Sobreposição de ', round(max_pct, 2), '% entre ', seg_id, ' e ', seg_id_b)").alias("mensagem")
        ).withColumn("criado_em", current_timestamp())

        # Insere via append na tabela de notificações
        df_notif.write.mode("append").saveAsTable("plataforma.segmentacao.seg_notificacao")
        print(f"🔔 {df_notif.count()} notificações de overlap enviadas")
    else:
        print("ℹ️ Nenhuma notificação nova necessária (já alertado nas últimas 24h)")

print("✅ Overlap calculado")