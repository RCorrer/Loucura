# Databricks notebook source
# S1-JOB-02: seg_guardiao (vigência) - com histórico correto

# COMMAND ----------

from pyspark.sql import SparkSession
spark = SparkSession.builder.getOrCreate()

# 1. Identifica quais segmentações serão ativadas (aprovadas com vigência iniciada)
df_ativar = spark.sql("""
    SELECT seg_id
    FROM plataforma.segmentacao.seg_definicao
    WHERE status = 'aprovada'
      AND vigencia_inicio <= current_timestamp()
      AND habilitado = true
""")

# 2. Identifica quais serão encerradas (ativas com vigência expirada)
df_encerrar = spark.sql("""
    SELECT seg_id
    FROM plataforma.segmentacao.seg_definicao
    WHERE status = 'ativa'
      AND vigencia_fim <= current_timestamp()
      AND habilitado = true
""")

# 3. Executa os UPDATES
if df_ativar.count() > 0:
    # Atualiza status para 'ativa'
    segs_ativar = [row.seg_id for row in df_ativar.collect()]
    spark.sql(f"""
        UPDATE plataforma.segmentacao.seg_definicao
        SET status = 'ativa', atualizado_em = current_timestamp()
        WHERE seg_id IN ({','.join(["'"+s+"'" for s in segs_ativar])})
    """)
    # Registra histórico APENAS para as que foram ativadas
    for seg_id in segs_ativar:
        spark.sql(f"""
            INSERT INTO plataforma.segmentacao.seg_historico_estado
            (hist_id, seg_id, estado_anterior, estado_novo, motivo, alterado_por)
            VALUES (
                concat('hist_', uuid()),
                '{seg_id}',
                'aprovada',
                'ativa',
                'guardiao_vigencia',
                'system'
            )
        """)
    print(f"✅ Ativadas: {len(segs_ativar)} segmentações")

if df_encerrar.count() > 0:
    segs_encerrar = [row.seg_id for row in df_encerrar.collect()]
    spark.sql(f"""
        UPDATE plataforma.segmentacao.seg_definicao
        SET status = 'encerrada', atualizado_em = current_timestamp()
        WHERE seg_id IN ({','.join(["'"+s+"'" for s in segs_encerrar])})
    """)
    for seg_id in segs_encerrar:
        spark.sql(f"""
            INSERT INTO plataforma.segmentacao.seg_historico_estado
            (hist_id, seg_id, estado_anterior, estado_novo, motivo, alterado_por)
            VALUES (
                concat('hist_', uuid()),
                '{seg_id}',
                'ativa',
                'encerrada',
                'guardiao_vigencia',
                'system'
            )
        """)
    print(f"⛔ Encerradas: {len(segs_encerrar)} segmentações")

if df_ativar.count() == 0 and df_encerrar.count() == 0:
    print("ℹ️ Nenhuma segmentação com vigência a ser alterada.")

print("✅ Guardião concluído")