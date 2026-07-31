# Databricks notebook source
# S1-JOB-04: seg_overlap (sobreposições) - 100% PySpark

# COMMAND ----------

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, when, lit, current_timestamp, expr, greatest
from delta.tables import DeltaTable

spark = SparkSession.builder.getOrCreate()

# ============================================================
# 1. Carrega resultado corrente dos segmentos ativos
# ============================================================
# Busca apenas segmentos com status 'ativa'
df_segmentos_ativos = spark.table("plataforma.segmentacao.seg_definicao") \
    .filter(col("status") == "ativa") \
    .select("seg_id", "owner")

# Lista de seg_ids ativos
ids_ativos = [row.seg_id for row in df_segmentos_ativos.select("seg_id").collect()]

if len(ids_ativos) < 2:
    print(f"ℹ️ Apenas {len(ids_ativos)} segmento(s) ativo(s). São necessários pelo menos 2 para calcular sobreposições.")
    dbutils.notebook.exit("Sobreposição não calculada (menos de 2 segmentos ativos)")

# ============================================================
# 2. Carrega resultado corrente (cpf_cnpj) para os segmentos ativos
# ============================================================
df_result = spark.table("plataforma.segmentacao.seg_resultado_corrente") \
    .filter(col("seg_id").isin(ids_ativos)) \
    .select("seg_id", "cpf_cnpj")

# ============================================================
# 3. Calcula sobreposição por pares (self-join com condição seg_id_a < seg_id_b)
# ============================================================
# Auto-join para encontrar interseções
df_pairs = df_result.alias("a") \
    .join(df_result.alias("b"), col("a.cpf_cnpj") == col("b.cpf_cnpj")) \
    .filter(col("a.seg_id") < col("b.seg_id")) \
    .groupBy(col("a.seg_id").alias("seg_id_a"), col("b.seg_id").alias("seg_id_b")) \
    .agg(count("*").alias("clientes_em_comum"))

# ============================================================
# 4. Calcula total de clientes por segmento
# ============================================================
df_totals = df_result.groupBy("seg_id") \
    .agg(count("*").alias("total"))

# ============================================================
# 5. Junta para calcular percentuais (pct_sobre_a e pct_sobre_b)
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

# Cria DataFrame com os dados a serem upsertados
df_upsert = df_overlap.select(
    "seg_id_a",
    "seg_id_b",
    "clientes_em_comum",
    "pct_sobre_a",
    "pct_sobre_b",
    "calculado_em"
)

delta_overlap.alias("target") \
    .merge(
        df_upsert.alias("source"),
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

# ============================================================
# 7. Alerta de alta sobreposição (>80%)
# ============================================================
# Identifica pares com alta sobreposição
df_alto_overlap = df_overlap \
    .filter((col("pct_sobre_a") > 80) | (col("pct_sobre_b") > 80)) \
    .select(
        col("seg_id_a"),
        col("seg_id_b"),
        greatest(col("pct_sobre_a"), col("pct_sobre_b")).alias("max_pct")
    )

if df_alto_overlap.count() > 0:
    # Busca owners dos segmentos envolvidos
    df_owners = df_segmentos_ativos.select("seg_id", "owner").filter(col("owner").isNotNull())
    
    # Para cada par com alta sobreposição, cria notificação para o owner de seg_id_a (pode ser ajustado)
    # Vamos criar notificações para ambos os owners? Para simplificar, apenas para o owner de seg_id_a
    df_notif_pairs = df_alto_overlap \
        .join(df_owners.alias("oa"), col("seg_id_a") == col("oa.seg_id")) \
        .select(
            col("oa.owner").alias("destinatario"),
            lit("alerta").alias("tipo"),
            col("seg_id_a").alias("seg_id_notif"),
            expr("concat('⚠️ Alta sobreposição: ', seg_id_a, ' x ', seg_id_b)").alias("titulo"),
            expr("concat('Sobreposição de ', round(max_pct, 2), '% entre ', seg_id_a, ' e ', seg_id_b)").alias("mensagem")
        ) \
        .select(
            expr("concat('notif_', uuid())").alias("notif_id"),
            "destinatario",
            "tipo",
            "seg_id_notif",
            "titulo",
            "mensagem"
        )
    
    # Insere notificações
    df_notif_pairs.write.mode("append").saveAsTable("plataforma.segmentacao.seg_notificacao")
    print(f"🔔 {df_notif_pairs.count()} notificações de alta sobreposição enviadas")
else:
    print("ℹ️ Nenhuma sobreposição alta (>80%) encontrada.")

# ============================================================
# 8. Finaliza
# ============================================================
print(f"✅ Overlap calculado para {df_overlap.count()} pares de segmentos")