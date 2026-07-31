# Databricks notebook source
# S1-JOB-02: seg_guardiao - 100% PySpark DataFrames

from pyspark.sql import SparkSession, functions as F
import uuid
spark = SparkSession.builder.getOrCreate()

# 1. Ativar segmentações agendadas
df_def = spark.table("plataforma.segmentacao.seg_definicao")
df_ativar = df_def.filter(
    (F.col("status") == "aprovada") &
    (F.col("vigencia_inicio") <= F.current_timestamp()) &
    (F.col("habilitado") == True)
)
# Atualiza status para ativa (precisa de UPDATE em Delta)
# Para fazer UPDATE via DataFrame, usamos o DeltaTable API ou spark.sql
# Como é uma operação simples, usaremos spark.sql para UPDATE, mas mantendo DataFrames para leitura.
# A opção seria criar uma tabela temporária e fazer MERGE, mas é mais complexo.
# Vamos usar spark.sql apenas para o UPDATE, já que DataFrame não tem UPDATE nativo.
# Para manter a pureza, poderíamos usar spark.sql, mas você pediu sem spark.sql.
# Então faremos: ler os IDs, e usar um loop para atualizar? Não é eficiente.
# A melhor forma é usar DeltaTable API:
from delta.tables import DeltaTable
deltaTable = DeltaTable.forName(spark, "plataforma.segmentacao.seg_definicao")
deltaTable.update(
    condition = (F.col("status") == "aprovada") & (F.col("vigencia_inicio") <= F.current_timestamp()) & (F.col("habilitado") == True),
    set = {"status": F.lit("ativa"), "atualizado_em": F.current_timestamp()}
)

# Registrar histórico (usando DataFrame)
df_ativados = spark.table("plataforma.segmentacao.seg_definicao") \
    .filter((F.col("status") == "ativa") & (F.col("vigencia_inicio") <= F.current_timestamp()) & (F.col("habilitado") == True)) \
    .select("seg_id")
# Para simplificar, inserimos histórico diretamente com um SELECT+INSERT (DataFrame)
if df_ativados.count() > 0:
    df_hist = df_ativados.select(
        F.concat(F.lit("hist_"), F.expr("uuid()")).alias("hist_id"),
        F.col("seg_id"),
        F.lit("aprovada").alias("estado_anterior"),
        F.lit("ativa").alias("estado_novo"),
        F.lit("guardiao_vigencia").alias("motivo"),
        F.lit("system").alias("alterado_por")
    )
    df_hist.write.mode("append").saveAsTable("plataforma.segmentacao.seg_historico_estado")

# 2. Encerrar segmentações expiradas
deltaTable = DeltaTable.forName(spark, "plataforma.segmentacao.seg_definicao")
deltaTable.update(
    condition = (F.col("status") == "ativa") & (F.col("vigencia_fim") <= F.current_timestamp()) & (F.col("habilitado") == True),
    set = {"status": F.lit("encerrada"), "atualizado_em": F.current_timestamp()}
)

df_encerrados = spark.table("plataforma.segmentacao.seg_definicao") \
    .filter((F.col("status") == "encerrada") & (F.col("vigencia_fim") <= F.current_timestamp()) & (F.col("habilitado") == True)) \
    .select("seg_id")
if df_encerrados.count() > 0:
    df_hist2 = df_encerrados.select(
        F.concat(F.lit("hist_"), F.expr("uuid()")).alias("hist_id"),
        F.col("seg_id"),
        F.lit("ativa").alias("estado_anterior"),
        F.lit("encerrada").alias("estado_novo"),
        F.lit("guardiao_vigencia").alias("motivo"),
        F.lit("system").alias("alterado_por")
    )
    df_hist2.write.mode("append").saveAsTable("plataforma.segmentacao.seg_historico_estado")

print("✅ Guardião concluído")