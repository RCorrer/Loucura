# Databricks notebook source
# S1-JOB-04: seg_overlap (sobreposições) com PySpark
# Usa JOIN e agregação em Spark para eficiência

# ATENÇÃO: Ajuste o caminho do projeto se necessário.
# Caminho esperado: /Workspace/Users/rafael_correr@hotmail.com/campaign_databricks_app/databricks/jobs/seg_overlap

# COMMAND ----------

# MAGIC %md
# MAGIC ### Job de Sobreposição
# MAGIC Calcula interseção entre segmentos ativos.

# COMMAND ----------

import sys
import os
import uuid
from datetime import datetime

# Detecção automática de caminho
try:
    notebook_path = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
    project_path = os.path.dirname(os.path.dirname(os.path.dirname(notebook_path)))
    if not os.path.exists(os.path.join(project_path, "src")):
        project_path = "/Workspace/Users/rafael_correr@hotmail.com/campaign_databricks_app"
    if project_path not in sys.path:
        sys.path.insert(0, project_path)
    print(f"📁 Caminho do projeto: {project_path}")
except:
    project_path = "/Workspace/Users/rafael_correr@hotmail.com/campaign_databricks_app"
    if project_path not in sys.path:
        sys.path.insert(0, project_path)
    print(f"⚠️ Usando caminho manual: {project_path}")

# COMMAND ----------

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, when, lit, current_timestamp
from src.db.databricks_client import get_client

spark = SparkSession.builder.getOrCreate()
client = get_client()

# COMMAND ----------

# MAGIC %md
# MAGIC ### Calcular overlap via Spark

# COMMAND ----------

def main():
    print("🚀 Calculando overlaps...")

    # Carrega resultado corrente dos segmentos ativos
    df_result = spark.sql("""
        SELECT seg_id, cpf_cnpj
        FROM plataforma.segmentacao.seg_resultado_corrente
        WHERE seg_id IN (SELECT seg_id FROM plataforma.segmentacao.seg_definicao WHERE status = 'ativa')
    """)

    # Auto-join para calcular interseções
    df_pairs = df_result.alias("a") \
        .join(df_result.alias("b"), col("a.cpf_cnpj") == col("b.cpf_cnpj")) \
        .filter(col("a.seg_id") < col("b.seg_id")) \
        .groupBy(col("a.seg_id").alias("seg_id_a"), col("b.seg_id").alias("seg_id_b")) \
        .agg(count("*").alias("clientes_em_comum"))

    if df_pairs.count() == 0:
        print("⚠️ Nenhum par de segmentos ativos com interseção.")
        return

    # Calcula totais por segmento
    df_totals = df_result.groupBy("seg_id").agg(count("*").alias("total"))

    # Calcula percentuais
    df_overlap = df_pairs \
        .join(df_totals.alias("ta"), col("seg_id_a") == col("ta.seg_id")) \
        .join(df_totals.alias("tb"), col("seg_id_b") == col("tb.seg_id")) \
        .withColumn("pct_sobre_a", col("clientes_em_comum") / col("ta.total") * 100) \
        .withColumn("pct_sobre_b", col("clientes_em_comum") / col("tb.total") * 100) \
        .withColumn("calculado_em", current_timestamp()) \
        .select("seg_id_a", "seg_id_b", "clientes_em_comum", "pct_sobre_a", "pct_sobre_b", "calculado_em")

    # Upsert em seg_overlap (MERGE via Spark SQL)
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

    print("✅ Overlaps calculados e armazenados.")

    # Alerta de sobreposição > 80% (via cliente SQL)
    alertas = spark.sql("""
        SELECT seg_id_a, seg_id_b, pct_sobre_a, pct_sobre_b
        FROM plataforma.segmentacao.seg_overlap
        WHERE pct_sobre_a > 80 OR pct_sobre_b > 80
    """)
    if alertas.count() > 0:
        for row in alertas.collect():
            seg_a = row["seg_id_a"]
            seg_b = row["seg_id_b"]
            pct_a = row["pct_sobre_a"]
            pct_b = row["pct_sobre_b"]
            # Busca owners
            sql_owners = "SELECT owner FROM plataforma.segmentacao.seg_definicao WHERE seg_id IN (?, ?)"
            owners = client.execute_query(sql_owners, (seg_a, seg_b))
            for owner_row in owners:
                owner = owner_row.get("owner")
                if owner:
                    notif_id = f"notif_{uuid.uuid4().hex[:8]}"
                    sql_notif = """
                        INSERT INTO plataforma.segmentacao.seg_notificacao
                        (notif_id, destinatario, tipo, seg_id, titulo, mensagem)
                        VALUES (?, ?, 'alerta', ?, ?, ?)
                    """
                    titulo = f"⚠️ Alta sobreposição: {seg_a} x {seg_b}"
                    msg = f"Sobreposição de {round(max(pct_a, pct_b), 2)}% entre {seg_a} e {seg_b}."
                    client.execute_insert(sql_notif, (notif_id, owner, seg_a, titulo, msg))
                    print(f"📢 Alerta de overlap enviado para {owner}")

    print("✅ Job de overlap concluído.")

# COMMAND ----------

if __name__ == "__main__":
    main()