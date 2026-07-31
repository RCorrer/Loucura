# Databricks notebook source
# S1-JOB-01: seg_exec (execução/recálculo) com PySpark
# 
# ATENÇÃO: Ajuste o caminho do projeto se necessário.
# O script tenta detectar automaticamente o caminho baseado no local do notebook.
# Se falhar, defina manualmente a variável PROJECT_PATH abaixo.
# 
# Caminho esperado: /Workspace/Users/rafael_correr@hotmail.com/campaign_databricks_app/databricks/jobs/seg_exec

# COMMAND ----------

# MAGIC %md
# MAGIC ### Parâmetros do Job
# MAGIC - `seg_id`: ID da segmentação a ser executada
# MAGIC - `origem_execucao`: `agendada` | `aprovacao` | `manual`

# COMMAND ----------

# Recebe parâmetros do Workflow
dbutils.widgets.text("seg_id", "", "ID da Segmentação")
dbutils.widgets.text("origem_execucao", "agendada", "Origem da Execução")

seg_id = dbutils.widgets.get("seg_id")
origem_execucao = dbutils.widgets.get("origem_execucao")

print(f"Executando segmentação: {seg_id} | Origem: {origem_execucao}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Setup do ambiente (auto-detecção de caminho)

# COMMAND ----------

import sys
import os
import json
import uuid
from datetime import datetime

# Tenta detectar o caminho do projeto automaticamente
notebook_path = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
project_path = os.path.dirname(os.path.dirname(os.path.dirname(notebook_path)))

# Fallback: se a detecção falhar, defina manualmente
if not os.path.exists(os.path.join(project_path, "src")):
    # ⚠️ ATENÇÃO: Ajuste este caminho para o seu workspace
    project_path = "/Workspace/Users/rafael_correr@hotmail.com/campaign_databricks_app"
    print(f"⚠️ Usando caminho manual: {project_path}")

if project_path not in sys.path:
    sys.path.insert(0, project_path)

print(f"📁 Caminho do projeto: {project_path}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Imports e funções auxiliares

# COMMAND ----------

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit, current_timestamp, when
from pyspark.sql.types import StructType, StructField, StringType

from src.db.databricks_client import get_client
from src.core.query_engine import QueryEngine
from src.core.validator import RegraValidator
from src.models.regras import RegrasJson

spark = SparkSession.builder.getOrCreate()
client = get_client()

# COMMAND ----------

def gerar_exec_id(seg_id: str) -> str:
    now = datetime.now().strftime("%Y%m%d_%H%M")
    suffix = uuid.uuid4().hex[:4]
    return f"exec_{seg_id}_{now}_{suffix}"

# COMMAND ----------

# MAGIC %md
# MAGIC ### Função principal (com PySpark)

# COMMAND ----------

def main(seg_id: str, origem: str):
    exec_id = gerar_exec_id(seg_id)
    print(f"🚀 Iniciando execução: {exec_id}")

    # 1. Carrega definição da segmentação
    sql_def = """
        SELECT seg_id, regras_json, versao_atual, owner, status
        FROM plataforma.segmentacao.seg_definicao
        WHERE seg_id = ? AND status IN ('ativa', 'aprovada')
    """
    result = client.execute_query(sql_def, (seg_id,))
    if not result:
        print(f"❌ Segmentação {seg_id} não encontrada ou não está ativa/aprovada")
        sql_erro = """
            INSERT INTO plataforma.segmentacao.seg_execucao
            (exec_id, seg_id, origem_execucao, status, qtd_clientes)
            VALUES (?, ?, ?, 'erro', 0)
        """
        client.execute_insert(sql_erro, (exec_id, seg_id, origem))
        return

    row = result[0]
    regras_json = json.loads(row["regras_json"])
    versao = row["versao_atual"]
    owner = row.get("owner")

    # 2. Valida regras
    try:
        regras = RegrasJson(**regras_json)
        validator = RegraValidator()
        erros = validator.validar_regras(regras)
        if erros:
            raise ValueError(f"Erro de metadado: {erros}")
    except Exception as e:
        print(f"❌ Erro de metadado: {e}")
        # Registra erro e notifica
        sql_erro = """
            INSERT INTO plataforma.segmentacao.seg_execucao
            (exec_id, seg_id, origem_execucao, status, qtd_clientes)
            VALUES (?, ?, ?, 'erro_metadado', 0)
        """
        client.execute_insert(sql_erro, (exec_id, seg_id, origem))
        # Atualiza saúde e notifica
        if owner:
            notif_id = f"notif_{uuid.uuid4().hex[:8]}"
            sql_notif = """
                INSERT INTO plataforma.segmentacao.seg_notificacao
                (notif_id, destinatario, tipo, seg_id, titulo, mensagem)
                VALUES (?, ?, 'alerta', ?, ?, ?)
            """
            client.execute_insert(sql_notif, (notif_id, owner, seg_id, f"Erro em {seg_id}", str(e)))
        return

    # 3. Gera SQL via QueryEngine
    query_engine = QueryEngine()
    sql_consulta, params = query_engine.generate_query(regras)

    # 4. Executa a consulta via Spark (usando o SQL gerado)
    sql_select = f"""
        SELECT cpf_cnpj
        FROM ({sql_consulta}) AS subquery
    """
    # Executa via cliente SQL (que já trata placeholders)
    cpfs_result = client.execute_query(sql_select, tuple(params))
    cpf_list = [row["cpf_cnpj"] for row in cpfs_result]
    qtd_clientes = len(cpf_list)

    if not cpf_list:
        print("⚠️ Nenhum cliente encontrado. Limpando resultado corrente.")
        sql_delete = "DELETE FROM plataforma.segmentacao.seg_resultado_corrente WHERE seg_id = ?"
        client.execute_insert(sql_delete, (seg_id,))
    else:
        # Usa PySpark para fazer o MERGE de forma eficiente
        df = spark.createDataFrame(
            [(seg_id, cpf, exec_id) for cpf in cpf_list],
            schema=StructType([
                StructField("seg_id", StringType()),
                StructField("cpf_cnpj", StringType()),
                StructField("exec_id", StringType())
            ])
        )

        df.createOrReplaceTempView("novos_clientes")

        # MERGE via Spark SQL (atualiza ou insere)
        merge_sql = f"""
            MERGE INTO plataforma.segmentacao.seg_resultado_corrente AS target
            USING novos_clientes AS source
            ON target.seg_id = source.seg_id AND target.cpf_cnpj = source.cpf_cnpj
            WHEN MATCHED THEN
                UPDATE SET exec_id = source.exec_id, entrou_em = current_timestamp()
            WHEN NOT MATCHED THEN
                INSERT (seg_id, cpf_cnpj, exec_id, entrou_em)
                VALUES (source.seg_id, source.cpf_cnpj, source.exec_id, current_timestamp())
        """
        spark.sql(merge_sql)

        # Remove clientes que saíram do segmento (WHEN NOT MATCHED BY SOURCE)
        delete_sql = f"""
            DELETE FROM plataforma.segmentacao.seg_resultado_corrente
            WHERE seg_id = '{seg_id}'
              AND cpf_cnpj NOT IN (SELECT cpf_cnpj FROM novos_clientes)
        """
        spark.sql(delete_sql)

        # Append em seg_resultado_historico (snapshot)
        df_hist = df.withColumn("versao_usada", lit(versao)) \
                   .withColumn("snapshot_em", current_timestamp()) \
                   .select("exec_id", "seg_id", "versao_usada", "cpf_cnpj", "snapshot_em")
        df_hist.write.mode("append").saveAsTable("plataforma.segmentacao.seg_resultado_historico")

    # 5. Registra execução como sucesso
    sql_exec = """
        INSERT INTO plataforma.segmentacao.seg_execucao
        (exec_id, seg_id, versao_usada, origem_execucao, qtd_clientes, status, executado_em)
        VALUES (?, ?, ?, ?, ?, 'sucesso', current_timestamp())
    """
    client.execute_insert(sql_exec, (exec_id, seg_id, versao, origem, qtd_clientes))

    # 6. Emite evento
    sql_evento = """
        INSERT INTO plataforma.eventos.seg_eventos
        (evento_id, seg_id, exec_id, tipo_evento, destino, payload_json, criado_em)
        VALUES (?, ?, ?, 'executada', ?, ?, current_timestamp())
    """
    evento_id = f"evt_{uuid.uuid4().hex[:8]}"
    payload = json.dumps({"qtd_clientes": qtd_clientes, "origem": origem})
    client.execute_insert(sql_evento, (evento_id, seg_id, exec_id, origem, payload))

    print(f"✅ Execução concluída: {exec_id} | Qtd: {qtd_clientes}")

# COMMAND ----------

if __name__ == "__main__" and seg_id:
    main(seg_id, origem_execucao)
else:
    print("⚠️ Nenhum seg_id fornecido. O job não será executado.")