# Databricks notebook source
# S1-JOB-03: seg_saude (health checks) com PySpark
# Usa Spark para agregar métricas de execuções

# ATENÇÃO: Ajuste o caminho do projeto se necessário.
# Caminho esperado: /Workspace/Users/rafael_correr@hotmail.com/campaign_databricks_app/databricks/jobs/seg_saude

# COMMAND ----------

# MAGIC %md
# MAGIC ### Job de Saúde
# MAGIC Calcula métricas de saúde para cada segmentação ativa/pausada/agendada.
# MAGIC - Status: verde/amarelo/vermelho
# MAGIC - Variação de público
# MAGIC - Falhas recentes

# COMMAND ----------

import sys
import os
import json
import uuid
from datetime import datetime, timedelta

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
from pyspark.sql.functions import col, count, when, max, min, avg, lit, current_timestamp
from pyspark.sql.types import *
from src.db.databricks_client import get_client

spark = SparkSession.builder.getOrCreate()
client = get_client()

# COMMAND ----------

# MAGIC %md
# MAGIC ### Agregar métricas via Spark

# COMMAND ----------

# Lê dados de execuções via Spark
df_exec = spark.sql("""
    SELECT seg_id, status, qtd_clientes, executado_em
    FROM plataforma.segmentacao.seg_execucao
    WHERE seg_id IN (SELECT seg_id FROM plataforma.segmentacao.seg_definicao WHERE status IN ('ativa','pausada','aprovada','em_aprovacao'))
""")

# Agrupa por seg_id e calcula métricas
df_metrics = df_exec.groupBy("seg_id").agg(
    count("*").alias("total_execucoes"),
    count(when(col("status") == "sucesso", 1)).alias("sucessos"),
    count(when(col("status").isin(["erro", "erro_metadado"]), 1)).alias("falhas"),
    max("qtd_clientes").alias("max_publico"),
    min("qtd_clientes").alias("min_publico"),
    avg("qtd_clientes").alias("media_publico")
)

# COMMAND ----------

# MAGIC %md
# MAGIC ### Função para calcular saúde

# COMMAND ----------

def calcular_saude(seg_id: str, df_metrics, client):
    # Busca a linha do segmento
    row = df_metrics.filter(col("seg_id") == seg_id).collect()
    if not row:
        return {"health_status": "sem_dados", "publico_atual": None, "alertas": None}
    
    row = row[0]
    total_exec = row["total_execucoes"] or 0
    falhas = row["falhas"] or 0
    publico_atual = row["max_publico"] or 0
    
    status = "verde"
    alertas = []
    
    # Critérios
    if total_exec > 0:
        taxa_falha = falhas / total_exec
        if taxa_falha > 0.5:
            status = "vermelho"
            alertas.append({"tipo": "alta_taxa_falha", "taxa": round(taxa_falha*100, 2)})
        elif taxa_falha > 0.2:
            status = "amarelo"
            alertas.append({"tipo": "taxa_falha_media", "taxa": round(taxa_falha*100, 2)})
    
    if publico_atual == 0:
        if status != "vermelho":
            status = "amarelo"
        alertas.append({"tipo": "publico_zerado"})
    
    return {
        "health_status": status,
        "publico_atual": publico_atual,
        "alertas": alertas if alertas else None,
        "ultima_verificacao": datetime.now()
    }

# COMMAND ----------

# MAGIC %md
# MAGIC ### Executa e atualiza seg_saude

# COMMAND ----------

def main():
    # Lista todas as segmentações ativas/pausadas/agendadas
    sql_lista = """
        SELECT seg_id, owner
        FROM plataforma.segmentacao.seg_definicao
        WHERE status IN ('ativa', 'pausada', 'aprovada', 'em_aprovacao')
    """
    segmentos = client.execute_query(sql_lista)

    for row in segmentos:
        seg_id = row["seg_id"]
        owner = row.get("owner")
        dados = calcular_saude(seg_id, df_metrics, client)

        # Upsert em seg_saude (usando cliente SQL, mas poderia ser Spark também)
        sql_upsert = """
            MERGE INTO plataforma.segmentacao.seg_saude AS target
            USING (SELECT ? AS seg_id) AS source
            ON target.seg_id = source.seg_id
            WHEN MATCHED THEN
                UPDATE SET
                    health_status = ?,
                    ultima_verificacao = current_timestamp(),
                    publico_atual = ?,
                    alertas_json = ?
            WHEN NOT MATCHED THEN
                INSERT (seg_id, health_status, ultima_verificacao, publico_atual, alertas_json)
                VALUES (?, ?, current_timestamp(), ?, ?)
        """
        alertas_json = json.dumps(dados["alertas"]) if dados["alertas"] else None
        client.execute_insert(sql_upsert, (
            seg_id,
            dados["health_status"],
            dados["publico_atual"],
            alertas_json,
            seg_id,
            dados["health_status"],
            dados["publico_atual"],
            alertas_json
        ))

        # Se vermelho, notifica owner
        if dados["health_status"] == "vermelho" and owner:
            notif_id = f"notif_{uuid.uuid4().hex[:8]}"
            sql_notif = """
                INSERT INTO plataforma.segmentacao.seg_notificacao
                (notif_id, destinatario, tipo, seg_id, titulo, mensagem)
                VALUES (?, ?, 'alerta', ?, ?, ?)
            """
            titulo = f"🔴 Saúde crítica: {seg_id}"
            msg = f"Segmentação {seg_id} em estado vermelho. Alertas: {json.dumps(dados['alertas'])}"
            client.execute_insert(sql_notif, (notif_id, owner, seg_id, titulo, msg))
            print(f"🔴 Notificação enviada para {owner} sobre {seg_id}")

    print("✅ Saúde atualizada.")

# COMMAND ----------

if __name__ == "__main__":
    main()