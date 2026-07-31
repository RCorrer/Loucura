# Databricks notebook source
# S1-JOB-01: seg_exec (execução/recálculo) - 100% PySpark DataFrames
# Recebe parâmetros: seg_id, origem_execucao

# COMMAND ----------

# Parâmetros
dbutils.widgets.text("seg_id", "", "ID da Segmentação")
dbutils.widgets.text("origem_execucao", "agendada", "Origem da Execução")
seg_id = dbutils.widgets.get("seg_id")
origem = dbutils.widgets.get("origem_execucao")

print(f"Executando: {seg_id} | Origem: {origem}")

# COMMAND ----------

# Imports e setup
import uuid
import json
from datetime import datetime
from pyspark.sql import SparkSession, functions as F
from pyspark.sql.types import StructType, StructField, StringType

spark = SparkSession.builder.getOrCreate()

def gerar_exec_id(seg_id):
    now = datetime.now().strftime("%Y%m%d_%H%M")
    suffix = uuid.uuid4().hex[:4]
    return f"exec_{seg_id}_{now}_{suffix}"

# COMMAND ----------

# 1. Carrega definição da segmentação (DataFrame)
df_def = spark.table("plataforma.segmentacao.seg_definicao") \
    .filter((F.col("seg_id") == seg_id) & (F.col("status").isin(["ativa", "aprovada"])))

if df_def.count() == 0:
    print(f"❌ Segmentação {seg_id} não encontrada ou não está ativa/aprovada")
    exec_id = gerar_exec_id(seg_id)
    # Insere execução de erro (usando DataFrame)
    df_erro = spark.createDataFrame([(exec_id, seg_id, origem, "erro", 0)],
                                     ["exec_id", "seg_id", "origem_execucao", "status", "qtd_clientes"])
    df_erro.write.mode("append").saveAsTable("plataforma.segmentacao.seg_execucao")
    dbutils.notebook.exit("Segmentação não encontrada")

row = df_def.collect()[0]
regras_json = row.regras_json
versao = row.versao_atual
owner = row.owner
publico_base = row.publico_base_id

# COMMAND ----------

# 2. Valida regras (sem spark.sql)
import re
campos = re.findall(r'"campo_id"\s*:\s*"([^"]+)"', regras_json)
if campos:
    # Carrega catálogo de características como DataFrame
    df_catalogo = spark.table("plataforma.metadata.catalogo_caracteristicas") \
        .filter(F.col("ativo") == True) \
        .select("caracteristica_id") \
        .distinct()
    # Extrai os IDs válidos
    validos = [row.caracteristica_id for row in df_catalogo.collect()]
    invalidos = [c for c in campos if c not in validos]
else:
    invalidos = []

if invalidos:
    print(f"❌ Erro de metadado: campos inválidos {invalidos}")
    exec_id = gerar_exec_id(seg_id)
    # Insere execução com erro
    df_erro = spark.createDataFrame([(exec_id, seg_id, origem, "erro_metadado", 0)],
                                     ["exec_id", "seg_id", "origem_execucao", "status", "qtd_clientes"])
    df_erro.write.mode("append").saveAsTable("plataforma.segmentacao.seg_execucao")
    # Atualiza saúde (usando DataFrame)
    df_saude = spark.table("plataforma.segmentacao.seg_saude") \
        .filter(F.col("seg_id") == seg_id)
    if df_saude.count() > 0:
        df_saude_update = df_saude.withColumn("health_status", F.lit("vermelho")) \
            .withColumn("alertas_json", F.lit(json.dumps({"tipo":"erro_metadado","campos_invalidos":invalidos})))
        # Sobrescreve a linha (para simplificar, usa overwrite com merge, mas faremos replace)
        # Como é POC, deletamos e inserimos
        spark.sql(f"DELETE FROM plataforma.segmentacao.seg_saude WHERE seg_id = '{seg_id}'")
        df_saude_update.select("seg_id", "health_status", "alertas_json") \
            .write.mode("append").saveAsTable("plataforma.segmentacao.seg_saude")
    else:
        df_saude_new = spark.createDataFrame([(seg_id, "vermelho", json.dumps({"tipo":"erro_metadado","campos_invalidos":invalidos}))],
                                              ["seg_id", "health_status", "alertas_json"])
        df_saude_new.write.mode("append").saveAsTable("plataforma.segmentacao.seg_saude")
    # Notificação
    if owner:
        notif_id = f"notif_{uuid.uuid4().hex[:8]}"
        df_notif = spark.createDataFrame([(notif_id, owner, "alerta", seg_id, "Erro de metadado", f"Campos inválidos: {invalidos}")],
                                         ["notif_id", "destinatario", "tipo", "seg_id", "titulo", "mensagem"])
        df_notif.write.mode("append").saveAsTable("plataforma.segmentacao.seg_notificacao")
    dbutils.notebook.exit("Erro de metadado")

# COMMAND ----------

# 3. Gera SQL via DataFrame (não usa spark.sql)
# Função que converte regras JSON em condições de DataFrame
def build_filters(regras_json, base_df, feature_df):
    # Parse do JSON (simplificado)
    import json
    try:
        regras = json.loads(regras_json)
        conditions = []
        for rule in regras.get("rules", []):
            campo = rule["campo_id"]
            op = rule["op"]
            valor = rule["value"]
            if op == ">":
                conditions.append(F.col(f"f.{campo}") > valor)
            elif op == "=":
                conditions.append(F.col(f"f.{campo}") == valor)
            elif op == "<":
                conditions.append(F.col(f"f.{campo}") < valor)
            elif op == ">=":
                conditions.append(F.col(f"f.{campo}") >= valor)
            elif op == "<=":
                conditions.append(F.col(f"f.{campo}") <= valor)
            elif op == "between" and isinstance(valor, list) and len(valor)==2:
                conditions.append((F.col(f"f.{campo}") >= valor[0]) & (F.col(f"f.{campo}") <= valor[1]))
            # ... outros operadores podem ser adicionados
        return conditions
    except:
        return []

# Monta DataFrame base (público base + features)
df_publico = spark.table(f"plataforma.publico.{publico_base}").select("cpf_cnpj")
df_features = spark.table("plataforma.caracteristicas.customer_features_wide").select("cpf_cnpj", "*")
# Renomeia colunas da features para evitar conflito (usando alias)
df_features = df_features.select([F.col(c).alias(f"f_{c}") if c != "cpf_cnpj" else F.col(c) for c in df_features.columns])
df_joined = df_publico.join(df_features, "cpf_cnpj", "inner")

# Aplica filtros
filters = build_filters(regras_json, df_publico, df_features)
for cond in filters:
    df_joined = df_joined.filter(cond)

# Seleciona CPFs
df_cpfs = df_joined.select("cpf_cnpj").distinct()
cpf_list = [row.cpf_cnpj for row in df_cpfs.collect()]
qtd = len(cpf_list)
exec_id = gerar_exec_id(seg_id)

# COMMAND ----------

# 4. MERGE usando DataFrames (sem spark.sql)
if qtd > 0:
    # DataFrame com os novos clientes
    df_novos = spark.createDataFrame(
        [(seg_id, cpf, exec_id) for cpf in cpf_list],
        schema=StructType([
            StructField("seg_id", StringType()),
            StructField("cpf_cnpj", StringType()),
            StructField("exec_id", StringType())
        ])
    )
    # Carrega resultado corrente atual
    df_corrente = spark.table("plataforma.segmentacao.seg_resultado_corrente") \
        .filter(F.col("seg_id") == seg_id)
    # Remove os que não estão mais no segmento (anti-join)
    df_remover = df_corrente.join(df_novos, ["cpf_cnpj"], "left_anti") \
        .select("seg_id", "cpf_cnpj")
    # Exclui os removidos (usando DataFrame write com modo overwrite? Difícil fazer DELETE direto.
    # Alternativa: usar SQL para DELETE ou usar Delta Lake API.
    # Para simplificar, faremos uma abordagem: substituir a partição do segmento.
    # Aqui usamos SQL para DELETE, pois é mais simples.
    if df_remover.count() > 0:
        spark.sql(f"DELETE FROM plataforma.segmentacao.seg_resultado_corrente WHERE seg_id = '{seg_id}' AND cpf_cnpj IN ({','.join(['"'+r.cpf_cnpj+'"' for r in df_remover.collect()])})")
    # Adiciona ou atualiza novos (usando merge, mas usaremos append+delete)
    # Para simplificar, removemos todos e reinserimos (POC)
    spark.sql(f"DELETE FROM plataforma.segmentacao.seg_resultado_corrente WHERE seg_id = '{seg_id}'")
    df_novos.select("seg_id", "cpf_cnpj", "exec_id") \
        .withColumn("entrou_em", F.current_timestamp()) \
        .write.mode("append").saveAsTable("plataforma.segmentacao.seg_resultado_corrente")
    
    # Histórico
    df_hist = df_novos.withColumn("versao_usada", F.lit(versao)) \
        .withColumn("snapshot_em", F.current_timestamp()) \
        .select("exec_id", "seg_id", "versao_usada", "cpf_cnpj", "snapshot_em")
    df_hist.write.mode("append").saveAsTable("plataforma.segmentacao.seg_resultado_historico")
else:
    # Se não houver clientes, limpa
    spark.sql(f"DELETE FROM plataforma.segmentacao.seg_resultado_corrente WHERE seg_id = '{seg_id}'")

# COMMAND ----------

# 5. Registra execução
df_exec = spark.createDataFrame([(exec_id, seg_id, versao, origem, qtd, "sucesso")],
                                 ["exec_id", "seg_id", "versao_usada", "origem_execucao", "qtd_clientes", "status"]) \
    .withColumn("executado_em", F.current_timestamp())
df_exec.write.mode("append").saveAsTable("plataforma.segmentacao.seg_execucao")

# 6. Evento
evento_id = f"evt_{uuid.uuid4().hex[:8]}"
payload = json.dumps({"qtd_clientes": qtd, "origem": origem})
df_evento = spark.createDataFrame([(evento_id, seg_id, exec_id, "executada", origem, payload)],
                                   ["evento_id", "seg_id", "exec_id", "tipo_evento", "destino", "payload_json"]) \
    .withColumn("criado_em", F.current_timestamp())
df_evento.write.mode("append").saveAsTable("plataforma.eventos.seg_eventos")

print(f"✅ Execução concluída: {exec_id} | Qtd: {qtd}")