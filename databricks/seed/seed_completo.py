# Databricks notebook source
# DBTITLE 1,Instalar faker
# MAGIC %pip install faker
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# ============================================================
# SEED COMPLETO PARA PLATAFORMA CDP - VERSÃO FINAL
# ============================================================
# Popula TODAS as tabelas necessárias para a POC.
# %pip install faker
# dbutils.library.restartPython()

# COMMAND ----------

# DBTITLE 1,Geração de dados de clientes
import random
import uuid
from datetime import datetime, timedelta
from faker import Faker
from pyspark.sql import Row
from pyspark.sql.functions import col, lit, when, monotonically_increasing_id
from pyspark.sql.types import *

# Configuração
NUM_CLIENTES = 50000  # Ajuste para teste rápido (ex: 1000)
NUM_RESPONSAVEIS = 20
CATALOG = "plataforma"

fake = Faker("pt_BR")
Faker.seed(42)
random.seed(42)

# Lista de gerentes
gerentes = [f"gerente_{i:03d}" for i in range(NUM_RESPONSAVEIS)]

# Geração de CPFs únicos
cpf_list = [fake.cpf().replace(".", "").replace("-", "") for _ in range(NUM_CLIENTES)]

# Função para gerar dados de um cliente
def gerar_cliente(cpf):
    renda = round(random.uniform(1500, 30000), 2)
    saldo = round(random.uniform(-500, 50000), 2)
    score = random.randint(300, 950)
    endividamento = round(random.uniform(0, 50000), 2)
    idade = random.randint(18, 80)
    return {
        "cpf_cnpj": cpf,
        "nome": fake.name(),
        "email": fake.email(),
        "telefone": fake.phone_number(),
        "segmento": random.choice(["varejo", "uniclass", "private"]),
        "data_nascimento": fake.date_of_birth(minimum_age=18, maximum_age=80),
        "agencia": fake.company()[:20],
        "gerente_nome": fake.name(),
        "tempo_relacionamento_meses": int(random.randint(1, 240)),
        # Wide
        "renda_mensal": renda,
        "faixa_renda": "baixa" if renda < 5000 else "media" if renda < 15000 else "alta",
        "renda_comprovada": random.choice([True, False]),
        "saldo_medio": saldo,
        "saldo_atual": saldo + random.uniform(-1000, 1000),
        "faixa_saldo": "baixo" if saldo < 5000 else "medio" if saldo < 20000 else "alto",
        "score": int(score),
        "faixa_score": "baixo" if score < 500 else "medio" if score < 700 else "alto",
        "valor_endividamento": endividamento,
        "comprometimento_renda_pct": round(endividamento / (renda + 1) * 100, 2) if renda > 0 else 0,
        "inadimplente": random.choice([True, False]),
        "idade": int(idade),
        "faixa_etaria": "18-25" if idade < 26 else "26-35" if idade < 36 else "36-50" if idade < 51 else "51-65" if idade < 66 else "65+",
        "genero": random.choice(["M", "F"]),
        "estado": fake.state_abbr(),
        "cidade": fake.city(),
        "estado_civil": random.choice(["solteiro", "casado", "divorciado", "viúvo"]),
        "profissao": random.choice(["Administrador", "Engenheiro", "Médico", "Professor", "Autônomo", "Empresário"]),
        "setor": random.choice(["Público", "Privado", "ONG"]),
        "tipo_vinculo": random.choice(["CLT", "PJ", "Servidor Público", "Aposentado"]),
        "escolaridade": random.choice(["Ensino Médio", "Graduação", "Pós-graduação", "Mestrado"]),
        "possui_conta": random.choice([True, False]),
        "tempo_conta_meses": int(random.randint(1, 240)),
        "tipo_conta": random.choice(["Comum", "Universitária", "Digital"]),
        "possui_cartao": random.choice([True, False]),
        "qtd_cartoes": int(random.randint(0, 5)),
        "limite_total": round(random.uniform(0, 30000), 2),
        "bandeira": random.choice(["Visa", "Mastercard", "Amex"]),
        "fatura_media": round(random.uniform(0, 5000), 2),
        "possui_investimento": random.choice([True, False]),
        "valor_investido": round(random.uniform(0, 100000), 2),
        "perfil_investidor": random.choice(["Conservador", "Moderado", "Agressivo"]),
        "possui_seguro": random.choice([True, False]),
        "tipos_seguro": random.sample(["Vida", "Auto", "Residencial", "Saúde"], k=random.randint(0, 3)),
        "possui_credito": random.choice([True, False]),
        "valor_credito_contratado": round(random.uniform(0, 50000), 2),
        "tipo_credito": random.choice(["Pessoal", "Consignado", "Imobiliário"]),
        "qtd_transacoes_mes": int(random.randint(0, 50)),
        "ticket_medio": round(random.uniform(10, 500), 2),
        "valor_movimentado_mes": round(random.uniform(0, 20000), 2),
        "usa_app": random.choice([True, False]),
        "usa_internet_banking": random.choice([True, False]),
        "canal_preferido": random.choice(["App", "Internet", "Agência"]),
        "frequencia_acesso": random.choice(["Diário", "Semanal", "Mensal", "Esporádico"]),
        "nps": int(random.randint(-100, 100)),
        "churn_score": round(random.uniform(0, 100), 2),
        "engajamento_score": round(random.uniform(0, 100), 2),
        "dias_desde_ultimo_acesso": int(random.randint(0, 120)),
    }

clientes_data = [gerar_cliente(cpf) for cpf in cpf_list]

# COMMAND ----------

# 1. GOLDEN RECORD
print("1. Golden Record...")
schema_golden = StructType([
    StructField("cpf_cnpj", StringType(), False),
    StructField("nome", StringType(), True),
    StructField("email", StringType(), True),
    StructField("telefone", StringType(), True),
    StructField("segmento", StringType(), True),
    StructField("data_nascimento", DateType(), True),
    StructField("agencia", StringType(), True),
    StructField("gerente_nome", StringType(), True),
    StructField("tempo_relacionamento_meses", IntegerType(), True)
])
golden_rows = [(d["cpf_cnpj"], d["nome"], d["email"], d["telefone"], d["segmento"], 
                d["data_nascimento"], d["agencia"], d["gerente_nome"], d["tempo_relacionamento_meses"]) 
               for d in clientes_data]
spark.createDataFrame(golden_rows, schema_golden).write.mode("overwrite").saveAsTable(f"{CATALOG}.core_cliente.golden_record")
print("  OK")

# COMMAND ----------

# DBTITLE 1,2. Customer Features Wide (com segmento + dias_desde_ultimo_acesso)
# 2. CUSTOMER_FEATURES_WIDE
print("2. Customer Features Wide...")
schema_wide = StructType([
    StructField("cpf_cnpj", StringType(), False),
    StructField("renda_mensal", DoubleType(), True),
    StructField("faixa_renda", StringType(), True),
    StructField("renda_comprovada", BooleanType(), True),
    StructField("saldo_medio", DoubleType(), True),
    StructField("saldo_atual", DoubleType(), True),
    StructField("faixa_saldo", StringType(), True),
    StructField("score", IntegerType(), True),
    StructField("faixa_score", StringType(), True),
    StructField("valor_endividamento", DoubleType(), True),
    StructField("comprometimento_renda_pct", DoubleType(), True),
    StructField("inadimplente", BooleanType(), True),
    StructField("idade", IntegerType(), True),
    StructField("faixa_etaria", StringType(), True),
    StructField("genero", StringType(), True),
    StructField("estado", StringType(), True),
    StructField("cidade", StringType(), True),
    StructField("estado_civil", StringType(), True),
    StructField("profissao", StringType(), True),
    StructField("setor", StringType(), True),
    StructField("tipo_vinculo", StringType(), True),
    StructField("escolaridade", StringType(), True),
    StructField("possui_conta", BooleanType(), True),
    StructField("tempo_conta_meses", IntegerType(), True),
    StructField("tipo_conta", StringType(), True),
    StructField("possui_cartao", BooleanType(), True),
    StructField("qtd_cartoes", IntegerType(), True),
    StructField("limite_total", DoubleType(), True),
    StructField("bandeira", StringType(), True),
    StructField("fatura_media", DoubleType(), True),
    StructField("possui_investimento", BooleanType(), True),
    StructField("valor_investido", DoubleType(), True),
    StructField("perfil_investidor", StringType(), True),
    StructField("possui_seguro", BooleanType(), True),
    StructField("tipos_seguro", ArrayType(StringType()), True),
    StructField("possui_credito", BooleanType(), True),
    StructField("valor_credito_contratado", DoubleType(), True),
    StructField("tipo_credito", StringType(), True),
    StructField("qtd_transacoes_mes", IntegerType(), True),
    StructField("ticket_medio", DoubleType(), True),
    StructField("valor_movimentado_mes", DoubleType(), True),
    StructField("usa_app", BooleanType(), True),
    StructField("usa_internet_banking", BooleanType(), True),
    StructField("canal_preferido", StringType(), True),
    StructField("frequencia_acesso", StringType(), True),
    StructField("nps", IntegerType(), True),
    StructField("churn_score", DoubleType(), True),
    StructField("engajamento_score", DoubleType(), True),
    StructField("dias_desde_ultimo_acesso", IntegerType(), True),
    StructField("segmento", StringType(), True),
    StructField("atualizado_em", TimestampType(), True)
])
wide_rows = [(d["cpf_cnpj"],
d["renda_mensal"], d["faixa_renda"], d["renda_comprovada"], d["saldo_medio"], d["saldo_atual"], 
                d["faixa_saldo"], d["score"], d["faixa_score"], d["valor_endividamento"], d["comprometimento_renda_pct"], 
                d["inadimplente"], d["idade"], d["faixa_etaria"], d["genero"], d["estado"], d["cidade"], 
                d["estado_civil"], d["profissao"], d["setor"], d["tipo_vinculo"], d["escolaridade"], 
                d["possui_conta"], d["tempo_conta_meses"], d["tipo_conta"], d["possui_cartao"], d["qtd_cartoes"], 
                d["limite_total"], d["bandeira"], d["fatura_media"], d["possui_investimento"], d["valor_investido"], 
                d["perfil_investidor"], d["possui_seguro"], d["tipos_seguro"], d["possui_credito"], 
                d["valor_credito_contratado"], d["tipo_credito"], d["qtd_transacoes_mes"], d["ticket_medio"], 
                d["valor_movimentado_mes"], d["usa_app"], d["usa_internet_banking"], d["canal_preferido"], 
                d["frequencia_acesso"], d["nps"], d["churn_score"], d["engajamento_score"],
                d["dias_desde_ultimo_acesso"], d["segmento"], datetime.now()) 
               for d in clientes_data]
spark.createDataFrame(wide_rows, schema_wide).write.mode("overwrite").saveAsTable(f"{CATALOG}.caracteristicas.customer_features_wide")
print("  OK")

# COMMAND ----------

# 3. TABELAS TB_*
print("3. Tabelas tb_*...")

# tb_renda
tb_renda = [(d["cpf_cnpj"], d["renda_mensal"], d["faixa_renda"], d["renda_comprovada"]) for d in clientes_data]
spark.createDataFrame(tb_renda, StructType([StructField("cpf_cnpj", StringType(), False), StructField("renda_mensal", DoubleType(), True), StructField("faixa_renda", StringType(), True), StructField("comprovada", BooleanType(), True)])).write.mode("overwrite").saveAsTable(f"{CATALOG}.caracteristicas.tb_renda")

# tb_saldo
tb_saldo = [(d["cpf_cnpj"], d["saldo_medio"], d["saldo_atual"], d["faixa_saldo"]) for d in clientes_data]
spark.createDataFrame(tb_saldo, StructType([StructField("cpf_cnpj", StringType(), False), StructField("saldo_medio", DoubleType(), True), StructField("saldo_atual", DoubleType(), True), StructField("faixa_saldo", StringType(), True)])).write.mode("overwrite").saveAsTable(f"{CATALOG}.caracteristicas.tb_saldo_conta")

# tb_score
tb_score = [(d["cpf_cnpj"], d["score"], d["faixa_score"]) for d in clientes_data]
spark.createDataFrame(tb_score, StructType([StructField("cpf_cnpj", StringType(), False), StructField("score", IntegerType(), True), StructField("faixa_score", StringType(), True)])).write.mode("overwrite").saveAsTable(f"{CATALOG}.caracteristicas.tb_score_credito")

# tb_endividamento
tb_endividamento = [(d["cpf_cnpj"], d["valor_endividamento"], d["comprometimento_renda_pct"], d["inadimplente"]) for d in clientes_data]
spark.createDataFrame(tb_endividamento, StructType([StructField("cpf_cnpj", StringType(), False), StructField("valor_endividamento", DoubleType(), True), StructField("comprometimento_renda_pct", DoubleType(), True), StructField("inadimplente", BooleanType(), True)])).write.mode("overwrite").saveAsTable(f"{CATALOG}.caracteristicas.tb_endividamento")

# tb_demografico
tb_demografico = [(d["cpf_cnpj"], d["idade"], d["faixa_etaria"], d["genero"], d["estado"], d["cidade"], d["estado_civil"]) for d in clientes_data]
spark.createDataFrame(tb_demografico, StructType([StructField("cpf_cnpj", StringType(), False), StructField("idade", IntegerType(), True), StructField("faixa_etaria", StringType(), True), StructField("genero", StringType(), True), StructField("estado", StringType(), True), StructField("cidade", StringType(), True), StructField("estado_civil", StringType(), True)])).write.mode("overwrite").saveAsTable(f"{CATALOG}.caracteristicas.tb_demografico")

# tb_profissao
tb_profissao = [(d["cpf_cnpj"], d["profissao"], d["setor"], d["tipo_vinculo"]) for d in clientes_data]
spark.createDataFrame(tb_profissao, StructType([StructField("cpf_cnpj", StringType(), False), StructField("profissao", StringType(), True), StructField("setor", StringType(), True), StructField("tipo_vinculo", StringType(), True)])).write.mode("overwrite").saveAsTable(f"{CATALOG}.caracteristicas.tb_profissao")

# tb_escolaridade
tb_escolaridade = [(d["cpf_cnpj"], d["escolaridade"]) for d in clientes_data]
spark.createDataFrame(tb_escolaridade, StructType([StructField("cpf_cnpj", StringType(), False), StructField("escolaridade", StringType(), True)])).write.mode("overwrite").saveAsTable(f"{CATALOG}.caracteristicas.tb_escolaridade")

# tb_conta
tb_conta = [(d["cpf_cnpj"], d["possui_conta"], d["tempo_conta_meses"], d["tipo_conta"]) for d in clientes_data]
spark.createDataFrame(tb_conta, StructType([StructField("cpf_cnpj", StringType(), False), StructField("possui_conta", BooleanType(), True), StructField("tempo_conta_meses", IntegerType(), True), StructField("tipo_conta", StringType(), True)])).write.mode("overwrite").saveAsTable(f"{CATALOG}.caracteristicas.tb_conta_corrente")

# tb_cartao
tb_cartao = [(d["cpf_cnpj"], d["possui_cartao"], d["qtd_cartoes"], d["limite_total"], d["bandeira"], d["fatura_media"]) for d in clientes_data]
spark.createDataFrame(tb_cartao, StructType([StructField("cpf_cnpj", StringType(), False), StructField("possui_cartao", BooleanType(), True), StructField("qtd_cartoes", IntegerType(), True), StructField("limite_total", DoubleType(), True), StructField("bandeira", StringType(), True), StructField("fatura_media", DoubleType(), True)])).write.mode("overwrite").saveAsTable(f"{CATALOG}.caracteristicas.tb_cartao")

# tb_invest
tb_invest = [(d["cpf_cnpj"], d["possui_investimento"], d["valor_investido"], d["perfil_investidor"]) for d in clientes_data]
spark.createDataFrame(tb_invest, StructType([StructField("cpf_cnpj", StringType(), False), StructField("possui_investimento", BooleanType(), True), StructField("valor_investido", DoubleType(), True), StructField("perfil_investidor", StringType(), True)])).write.mode("overwrite").saveAsTable(f"{CATALOG}.caracteristicas.tb_investimentos")

# tb_seguros
tb_seguros = [(d["cpf_cnpj"], d["possui_seguro"], d["tipos_seguro"]) for d in clientes_data]
spark.createDataFrame(tb_seguros, StructType([StructField("cpf_cnpj", StringType(), False), StructField("possui_seguro", BooleanType(), True), StructField("tipos_seguro", ArrayType(StringType()), True)])).write.mode("overwrite").saveAsTable(f"{CATALOG}.caracteristicas.tb_seguros")

# tb_credito
tb_credito = [(d["cpf_cnpj"], d["possui_credito"], d["valor_credito_contratado"], d["tipo_credito"]) for d in clientes_data]
spark.createDataFrame(tb_credito, StructType([StructField("cpf_cnpj", StringType(), False), StructField("possui_credito", BooleanType(), True), StructField("valor_credito_contratado", DoubleType(), True), StructField("tipo_credito", StringType(), True)])).write.mode("overwrite").saveAsTable(f"{CATALOG}.caracteristicas.tb_credito")

# tb_transacional
tb_transacional = [(d["cpf_cnpj"], d["qtd_transacoes_mes"], d["ticket_medio"], d["valor_movimentado_mes"]) for d in clientes_data]
spark.createDataFrame(tb_transacional, StructType([StructField("cpf_cnpj", StringType(), False), StructField("qtd_transacoes_mes", IntegerType(), True), StructField("ticket_medio", DoubleType(), True), StructField("valor_movimentado_mes", DoubleType(), True)])).write.mode("overwrite").saveAsTable(f"{CATALOG}.caracteristicas.tb_transacional")

# tb_canais
tb_canais = [(d["cpf_cnpj"], d["usa_app"], d["usa_internet_banking"], d["canal_preferido"], d["frequencia_acesso"]) for d in clientes_data]
spark.createDataFrame(tb_canais, StructType([StructField("cpf_cnpj", StringType(), False), StructField("usa_app", BooleanType(), True), StructField("usa_internet_banking", BooleanType(), True), StructField("canal_preferido", StringType(), True), StructField("frequencia_acesso", StringType(), True)])).write.mode("overwrite").saveAsTable(f"{CATALOG}.caracteristicas.tb_canais_digitais")

# tb_engajamento
tb_engajamento = [(d["cpf_cnpj"], d["nps"], d["churn_score"], d["engajamento_score"]) for d in clientes_data]
spark.createDataFrame(tb_engajamento, StructType([StructField("cpf_cnpj", StringType(), False), StructField("nps", IntegerType(), True), StructField("churn_score", DoubleType(), True), StructField("engajamento_score", DoubleType(), True)])).write.mode("overwrite").saveAsTable(f"{CATALOG}.caracteristicas.tb_engajamento")

print("  OK")

# COMMAND ----------

# 4. PÚBLICOS-BASE
print("4. Públicos-base...")
pub_varejo = [Row(cpf_cnpj=d["cpf_cnpj"]) for d in clientes_data if d["segmento"] == "varejo"]
pub_uniclass = [Row(cpf_cnpj=d["cpf_cnpj"]) for d in clientes_data if d["segmento"] == "uniclass"]
pub_private = [Row(cpf_cnpj=d["cpf_cnpj"]) for d in clientes_data if d["segmento"] == "private"]
if pub_varejo: spark.createDataFrame(pub_varejo).write.mode("overwrite").saveAsTable(f"{CATALOG}.publico.pub_varejo")
if pub_uniclass: spark.createDataFrame(pub_uniclass).write.mode("overwrite").saveAsTable(f"{CATALOG}.publico.pub_uniclass")
if pub_private: spark.createDataFrame(pub_private).write.mode("overwrite").saveAsTable(f"{CATALOG}.publico.pub_private")
print("  OK")

# COMMAND ----------

# 5. ENCARTEIRAMENTO
print("5. Vínculo cliente-responsável...")
vinculo_rows = []
for cpf in cpf_list:
    vinculo_rows.append(Row(cpf_cnpj=cpf, responsavel_id=random.choice(gerentes), tipo_responsavel="gerente"))
spark.createDataFrame(vinculo_rows).write.mode("overwrite").saveAsTable(f"{CATALOG}.analitico.vinculo_cliente_responsavel")
print("  OK")

# COMMAND ----------

# 6. CONSENTIMENTO
print("6. Consentimento...")
consent_rows = []
for cpf in cpf_list:
    for canal in ["email", "whatsapp", "push"]:
        consent_rows.append(Row(cpf_cnpj=cpf, canal=canal, status="opt_in", base_legal="consentimento", origem="seed", atualizado_em=datetime.now()))
spark.createDataFrame(consent_rows).write.mode("overwrite").saveAsTable(f"{CATALOG}.governanca.consentimento")
print("  OK")

# COMMAND ----------

# DBTITLE 1,7. RBAC (usuarios_perfil)
# 7. RBAC (usuarios_perfil)
# O backend usa o email do header X-Forwarded-Email para lookup.
# Precisamos de usuários com EMAIL como usuario_id.
print("7. RBAC...")
schema_rbac = StructType([
    StructField("usuario_id", StringType(), False),
    StructField("nome", StringType(), True),
    StructField("sistema", StringType(), True),
    StructField("perfil", StringType(), True),
    StructField("ativo", BooleanType(), True),
    StructField("concedido_por", StringType(), True),
    StructField("concedido_em", TimestampType(), True),
    StructField("revogado_por", StringType(), True),
    StructField("revogado_em", TimestampType(), True)
])

# Usuário principal (OBO) — email real que chega via Databricks Apps
MAIN_USER = "rafael.correr@bradesco.com.br"

now = datetime.now()
rbac_rows = [
    # Admin principal em todos os sistemas
    (MAIN_USER, "Rafael Correr", "segmenthub", "admin", True, "bootstrap", now, None, None),
    (MAIN_USER, "Rafael Correr", "clientview360", "admin", True, "bootstrap", now, None, None),
    (MAIN_USER, "Rafael Correr", "engagement", "admin", True, "bootstrap", now, None, None),
    (MAIN_USER, "Rafael Correr", "analytics", "admin", True, "bootstrap", now, None, None),
    # Usuário dev fallback (DEV_USER env)
    ("admin", "Admin Dev", "segmenthub", "admin", True, "bootstrap", now, None, None),
    ("admin", "Admin Dev", "clientview360", "admin", True, "bootstrap", now, None, None),
    ("admin", "Admin Dev", "engagement", "admin", True, "bootstrap", now, None, None),
    ("admin", "Admin Dev", "analytics", "admin", True, "bootstrap", now, None, None),
    # Analistas para teste
    ("analista1@bradesco.com.br", "Analista Um", "segmenthub", "analista", True, "bootstrap", now, None, None),
    ("analista2@bradesco.com.br", "Analista Dois", "segmenthub", "analista", True, "bootstrap", now, None, None),
    ("analista1@bradesco.com.br", "Analista Um", "engagement", "analista", True, "bootstrap", now, None, None),
]
# Gerentes para S2
for i in range(1, 6):
    uid = f"gerente{i}@bradesco.com.br"
    rbac_rows.append((uid, f"Gerente {i}", "clientview360", "gerente", True, "bootstrap", now, None, None))

spark.createDataFrame(rbac_rows, schema_rbac).write.mode("overwrite").saveAsTable(f"{CATALOG}.governanca.usuarios_perfil")
print(f"  OK — {len(rbac_rows)} registros")

# COMMAND ----------

# DBTITLE 1,8. Catálogos (metadata) — ALINHADO COM BACKEND
# 8. CATÁLOGOS (metadata) — alinhado com QueryEngine + Validator
# IMPORTANTE: tabela_fisica DEVE ser fully qualified (plataforma.schema.table)
# IMPORTANTE: catalogo_publicos DEVE ter join_key
# IMPORTANTE: operadores devem incluir todos os suportados pelo query_engine
print("8. Catálogos...")

# Operadores padrão por tipo
OPS_NUMERIC = ["=", "!=", ">", "<", ">=", "<=", "between", "in", "not_in", "is_null", "is_not_null"]
OPS_CATEGORICAL = ["=", "!=", "in", "not_in", "contains", "starts_with", "is_null", "is_not_null"]
OPS_BOOLEAN = ["=", "is_null", "is_not_null"]
OPS_DATE = ["=", "!=", ">", "<", ">=", "<=", "between", "is_null", "is_not_null"]

FEATURES_TABLE = f"{CATALOG}.caracteristicas.customer_features_wide"

carac_data = [
    # Financeiro
    ("renda_mensal", "Financeiro", 1, FEATURES_TABLE, "Renda", "renda_mensal", "Renda Mensal", "numeric", OPS_NUMERIC, None, "cpf_cnpj", "normal", True, True, "financeiro", True, "Renda mensal declarada"),
    ("faixa_renda", "Financeiro", 2, FEATURES_TABLE, "Renda", "faixa_renda", "Faixa de Renda", "categorical", OPS_CATEGORICAL, ["baixa","media","alta"], "cpf_cnpj", "normal", True, True, "financeiro", True, "Faixa de renda"),
    ("saldo_medio", "Financeiro", 3, FEATURES_TABLE, "Saldo", "saldo_medio", "Saldo Médio", "numeric", OPS_NUMERIC, None, "cpf_cnpj", "normal", True, True, "financeiro", True, "Saldo médio em conta"),
    ("score", "Financeiro", 4, FEATURES_TABLE, "Score", "score", "Score de Crédito", "numeric", OPS_NUMERIC, None, "cpf_cnpj", "sensivel", False, True, "financeiro", True, "Score de crédito (300-950)"),
    ("inadimplente", "Financeiro", 5, FEATURES_TABLE, "Inadimplência", "inadimplente", "Inadimplente", "boolean", OPS_BOOLEAN, None, "cpf_cnpj", "sensivel", False, True, "financeiro", True, "Cliente inadimplente"),
    ("valor_endividamento", "Financeiro", 6, FEATURES_TABLE, "Dívida", "valor_endividamento", "Valor Endividamento", "numeric", OPS_NUMERIC, None, "cpf_cnpj", "sensivel", False, True, "financeiro", True, "Valor total de endividamento"),
    # Demográfico
    ("idade", "Demográfico", 1, FEATURES_TABLE, "Idade", "idade", "Idade", "numeric", OPS_NUMERIC, None, "cpf_cnpj", "normal", True, True, "cadastral", True, "Idade do cliente"),
    ("faixa_etaria", "Demográfico", 2, FEATURES_TABLE, "Faixa Etária", "faixa_etaria", "Faixa Etária", "categorical", OPS_CATEGORICAL, ["18-25","26-35","36-50","51-65","65+"], "cpf_cnpj", "normal", True, True, "cadastral", True, "Faixa etária"),
    ("genero", "Demográfico", 3, FEATURES_TABLE, "Gênero", "genero", "Gênero", "categorical", OPS_CATEGORICAL, ["M","F","Outro"], "cpf_cnpj", "normal", True, True, "cadastral", True, "Gênero"),
    ("estado", "Demográfico", 4, FEATURES_TABLE, "Estado", "estado", "Estado (UF)", "categorical", OPS_CATEGORICAL, None, "cpf_cnpj", "normal", False, True, "cadastral", True, "UF"),
    ("estado_civil", "Demográfico", 5, FEATURES_TABLE, "Estado Civil", "estado_civil", "Estado Civil", "categorical", OPS_CATEGORICAL, ["solteiro","casado","divorciado","viúvo"], "cpf_cnpj", "normal", True, True, "cadastral", True, "Estado civil"),
    ("segmento", "Demográfico", 6, FEATURES_TABLE, "Segmento", "segmento", "Segmento Bancário", "categorical", OPS_CATEGORICAL, ["varejo","uniclass","private"], "cpf_cnpj", "normal", True, True, "cadastral", True, "Segmento do cliente"),
    # Produtos
    ("possui_cartao", "Produtos", 1, FEATURES_TABLE, "Cartão", "possui_cartao", "Possui Cartão", "boolean", OPS_BOOLEAN, None, "cpf_cnpj", "normal", True, True, "produtos", True, "Possui cartão de crédito"),
    ("qtd_cartoes", "Produtos", 2, FEATURES_TABLE, "Cartão", "qtd_cartoes", "Qtd Cartões", "numeric", OPS_NUMERIC, None, "cpf_cnpj", "normal", False, True, "produtos", True, "Quantidade de cartões ativos"),
    ("possui_investimento", "Produtos", 3, FEATURES_TABLE, "Investimentos", "possui_investimento", "Possui Investimento", "boolean", OPS_BOOLEAN, None, "cpf_cnpj", "normal", True, True, "produtos", True, "Possui investimentos"),
    # Comportamento
    ("engajamento_score", "Comportamento", 1, FEATURES_TABLE, "Engajamento", "engajamento_score", "Score Engajamento", "numeric", OPS_NUMERIC, None, "cpf_cnpj", "normal", True, True, "comportamento", True, "Score de engajamento digital (0-100)"),
    ("usa_app", "Comportamento", 2, FEATURES_TABLE, "App", "usa_app", "Usa App Mobile", "boolean", OPS_BOOLEAN, None, "cpf_cnpj", "normal", True, True, "comportamento", True, "Utiliza app mobile"),
    ("dias_desde_ultimo_acesso", "Comportamento", 3, FEATURES_TABLE, "Acesso", "dias_desde_ultimo_acesso", "Dias s/ Acesso", "numeric", OPS_NUMERIC, None, "cpf_cnpj", "normal", True, True, "comportamento", True, "Dias desde último acesso digital"),
]

schema_carac = StructType([
    StructField("caracteristica_id", StringType(), False),
    StructField("tema", StringType(), True),
    StructField("tema_ordem", IntegerType(), True),
    StructField("tabela_fisica", StringType(), True),
    StructField("tabela_label", StringType(), True),
    StructField("campo_fisico", StringType(), True),
    StructField("campo_label", StringType(), True),
    StructField("tipo_dado", StringType(), True),
    StructField("operadores", ArrayType(StringType()), True),
    StructField("valores_dominio", ArrayType(StringType()), True),
    StructField("join_key", StringType(), True),
    StructField("sensibilidade", StringType(), True),
    StructField("usavel_em_peca", BooleanType(), True),
    StructField("usavel_em_visao360", BooleanType(), True),
    StructField("bloco_visao360", StringType(), True),
    StructField("ativo", BooleanType(), True),
    StructField("descricao", StringType(), True)
])
spark.createDataFrame(carac_data, schema_carac).write.mode("overwrite").saveAsTable(f"{CATALOG}.metadata.catalogo_caracteristicas")
print(f"  catalogo_caracteristicas: {len(carac_data)} campos")

# catalogo_publicos — COM join_key (obrigatório para QueryEngine)
schema_pub = StructType([
    StructField("publico_id", StringType(), False),
    StructField("nome", StringType(), True),
    StructField("descricao", StringType(), True),
    StructField("tabela_fisica", StringType(), True),
    StructField("join_key", StringType(), True),
    StructField("criado_por_time", StringType(), True),
    StructField("ativo", BooleanType(), True)
])
pub_cat_data = [
    ("pub_varejo", "Base Varejo", "Todos os clientes varejo", f"{CATALOG}.publico.pub_varejo", "cpf_cnpj", "Marketing", True),
    ("pub_uniclass", "Base Uniclass", "Clientes uniclass", f"{CATALOG}.publico.pub_uniclass", "cpf_cnpj", "Marketing", True),
    ("pub_private", "Base Private", "Clientes private", f"{CATALOG}.publico.pub_private", "cpf_cnpj", "Private Banking", True),
]
spark.createDataFrame(pub_cat_data, schema_pub).write.mode("overwrite").saveAsTable(f"{CATALOG}.metadata.catalogo_publicos")
print(f"  catalogo_publicos: {len(pub_cat_data)} públicos")
print("  OK — catálogos prontos para segmentação via API")

# NOTA: catalogo_canais do S3 movido para seed específico do EngagementHub
# para manter independência entre sistemas.
print("  OK"), descricao="Score de crédito"),
    Row(caracteristica_id="idade", tema="Demográfico", tema_ordem=1, tabela_fisica="caracteristicas.customer_features_wide", tabela_label="Idade", campo_fisico="idade", campo_label="Idade", tipo_dado="numeric", operadores=["=", ">", "<", "between"], valores_dominio=None, join_key="cpf_cnpj", sensibilidade="normal", usavel_em_peca=True, usavel_em_visao360=True, bloco_visao360="cadastral", ativo=True, descricao="Idade do cliente"),
    Row(caracteristica_id="faixa_etaria", tema="Demográfico", tema_ordem=2, tabela_fisica="caracteristicas.customer_features_wide", tabela_label="Faixa Etária", campo_fisico="faixa_etaria", campo_label="Faixa Etária", tipo_dado="categorical", operadores=["="], valores_dominio=["18-25","26-35","36-50","51-65","65+"], join_key="cpf_cnpj", sensibilidade="normal", usavel_em_peca=True, usavel_em_visao360=True, bloco_visao360="cadastral", ativo=True, descricao="Faixa etária"),
    Row(caracteristica_id="estado", tema="Demográfico", tema_ordem=3, tabela_fisica="caracteristicas.customer_features_wide", tabela_label="Estado", campo_fisico="estado", campo_label="Estado", tipo_dado="categorical", operadores=["="], valores_dominio=None, join_key="cpf_cnpj", sensibilidade="normal", usavel_em_peca=False, usavel_em_visao360=True, bloco_visao360="cadastral", ativo=True, descricao="UF"),
    Row(caracteristica_id="possui_cartao", tema="Produtos", tema_ordem=1, tabela_fisica="caracteristicas.customer_features_wide", tabela_label="Possui Cartão", campo_fisico="possui_cartao", campo_label="Possui Cartão", tipo_dado="boolean", operadores=["="], valores_dominio=None, join_key="cpf_cnpj", sensibilidade="normal", usavel_em_peca=True, usavel_em_visao360=True, bloco_visao360="produtos", ativo=True, descricao="Cliente possui cartão de crédito"),
    Row(caracteristica_id="qtd_cartoes", tema="Produtos", tema_ordem=2, tabela_fisica="caracteristicas.customer_features_wide", tabela_label="Qtd Cartões", campo_fisico="qtd_cartoes", campo_label="Quantidade de Cartões", tipo_dado="numeric", operadores=["=", ">", "<"], valores_dominio=None, join_key="cpf_cnpj", sensibilidade="normal", usavel_em_peca=False, usavel_em_visao360=True, bloco_visao360="produtos", ativo=True, descricao="Número de cartões"),
    Row(caracteristica_id="engajamento_score", tema="Comportamento", tema_ordem=1, tabela_fisica="caracteristicas.customer_features_wide", tabela_label="Engajamento", campo_fisico="engajamento_score", campo_label="Score de Engajamento", tipo_dado="numeric", operadores=["=", ">", "<"], valores_dominio=None, join_key="cpf_cnpj", sensibilidade="normal", usavel_em_peca=True, usavel_em_visao360=True, bloco_visao360="comportamento", ativo=True, descricao="Score de engajamento digital"),
]
schema_carac = StructType([
    StructField("caracteristica_id", StringType(), False),
    StructField("tema", StringType(), True),
    StructField("tema_ordem", IntegerType(), True),
    StructField("tabela_fisica", StringType(), True),
    StructField("tabela_label", StringType(), True),
    StructField("campo_fisico", StringType(), True),
    StructField("campo_label", StringType(), True),
    StructField("tipo_dado", StringType(), True),
    StructField("operadores", ArrayType(StringType()), True),
    StructField("valores_dominio", ArrayType(StringType()), True),
    StructField("join_key", StringType(), True),
    StructField("sensibilidade", StringType(), True),
    StructField("usavel_em_peca", BooleanType(), True),
    StructField("usavel_em_visao360", BooleanType(), True),
    StructField("bloco_visao360", StringType(), True),
    StructField("ativo", BooleanType(), True),
    StructField("descricao", StringType(), True)
])
carac_tuples = [(r.caracteristica_id, r.tema, r.tema_ordem, r.tabela_fisica, r.tabela_label, r.campo_fisico, r.campo_label, r.tipo_dado, r.operadores, r.valores_dominio, r.join_key, r.sensibilidade, r.usavel_em_peca, r.usavel_em_visao360, r.bloco_visao360, r.ativo, r.descricao) for r in carac_rows]
spark.createDataFrame(carac_tuples, schema_carac).write.mode("overwrite").saveAsTable(f"{CATALOG}.metadata.catalogo_caracteristicas")

# catalogo_publicos
pub_cat_rows = [
    Row(publico_id="pub_varejo", nome="Base Varejo", descricao="Clientes do segmento varejo", tabela_fisica=f"{CATALOG}.publico.pub_varejo", criado_por_time="Marketing", ativo=True),
    Row(publico_id="pub_uniclass", nome="Base Uniclass", descricao="Clientes do segmento uniclass", tabela_fisica=f"{CATALOG}.publico.pub_uniclass", criado_por_time="Marketing", ativo=True),
    Row(publico_id="pub_private", nome="Base Private", descricao="Clientes do segmento private", tabela_fisica=f"{CATALOG}.publico.pub_private", criado_por_time="Private", ativo=True),
]
spark.createDataFrame(pub_cat_rows).write.mode("overwrite").saveAsTable(f"{CATALOG}.metadata.catalogo_publicos")

# catalogo_canais
canais_rows = [
    Row(canal_id="email", nome_exibicao="E-mail", icone="email", suporta_html=True, suporta_imagem=False, suporta_botoes=False, suporta_video=False, max_caracteres=None, formato_editor="rico_html", campos_obrigatorios=["assunto", "corpo"], provider_class="EmailProvider", rate_limit_por_segundo=10, rate_limit_por_dia=100000, ativo=True),
    Row(canal_id="whatsapp", nome_exibicao="WhatsApp", icone="whatsapp", suporta_html=False, suporta_imagem=True, suporta_botoes=True, suporta_video=True, max_caracteres=1600, formato_editor="mensagem_simples", campos_obrigatorios=["mensagem"], provider_class="WhatsAppProvider", rate_limit_por_segundo=5, rate_limit_por_dia=10000, ativo=True),
    Row(canal_id="push", nome_exibicao="Push Notification", icone="push", suporta_html=False, suporta_imagem=False, suporta_botoes=False, suporta_video=False, max_caracteres=200, formato_editor="mensagem_simples", campos_obrigatorios=["titulo", "corpo"], provider_class="PushProvider", rate_limit_por_segundo=20, rate_limit_por_dia=50000, ativo=True),
]
schema_canais = StructType([
    StructField("canal_id", StringType(), False),
    StructField("nome_exibicao", StringType(), True),
    StructField("icone", StringType(), True),
    StructField("suporta_html", BooleanType(), True),
    StructField("suporta_imagem", BooleanType(), True),
    StructField("suporta_botoes", BooleanType(), True),
    StructField("suporta_video", BooleanType(), True),
    StructField("max_caracteres", IntegerType(), True),
    StructField("formato_editor", StringType(), True),
    StructField("campos_obrigatorios", ArrayType(StringType()), True),
    StructField("provider_class", StringType(), True),
    StructField("rate_limit_por_segundo", IntegerType(), True),
    StructField("rate_limit_por_dia", IntegerType(), True),
    StructField("ativo", BooleanType(), True)
])
canais_tuples = [(r.canal_id, r.nome_exibicao, r.icone, r.suporta_html, r.suporta_imagem, r.suporta_botoes, r.suporta_video, r.max_caracteres, r.formato_editor, r.campos_obrigatorios, r.provider_class, r.rate_limit_por_segundo, r.rate_limit_por_dia, r.ativo) for r in canais_rows]
spark.createDataFrame(canais_tuples, schema_canais).write.mode("overwrite").saveAsTable(f"{CATALOG}.engagement.catalogo_canais")
print("  OK")

# COMMAND ----------

# 9. CONFIGURAÇÕES DO S2 E S3 (FALTANTES)
print("9. Configurações...")

# config.catalogo_metricas
metricas_rows = [
    Row(metrica_id="total_clientes", nome_exibicao="Total de Clientes", descricao="Quantos clientes na carteira", icone="group", categoria="carteira", tipo_valor="numero", query_template="SELECT COUNT(DISTINCT cpf_cnpj) FROM plataforma.analitico.vinculo_cliente_responsavel WHERE responsavel_id = ':responsavel_id'", formato="numero", ordem=1, ativo=True, destaque=True, criado_por="admin", atualizado_em=datetime.now()),
    Row(metrica_id="taxa_conversao", nome_exibicao="Taxa de Conversão", descricao="% de clientes que converteram", icone="percentual", categoria="conversao", tipo_valor="percentual", query_template="SELECT (COUNT(CASE WHEN resultado = 'aceitou' THEN 1 END) * 100.0 / NULLIF(COUNT(*),0)) FROM plataforma.atendimento.interacao WHERE responsavel_id = ':responsavel_id'", formato="percentual", ordem=2, ativo=True, destaque=True, criado_por="admin", atualizado_em=datetime.now()),
    Row(metrica_id="follow_ups_pendentes", nome_exibicao="Follow-ups Pendentes", descricao="Clientes aguardando retorno", icone="numero", categoria="atendimento", tipo_valor="numero", query_template="SELECT COUNT(*) FROM plataforma.atendimento.follow_ups WHERE responsavel_id = ':responsavel_id'", formato="numero", ordem=3, ativo=True, destaque=False, criado_por="admin", atualizado_em=datetime.now()),
]
schema_metricas = StructType([StructField("metrica_id", StringType(), False), StructField("nome_exibicao", StringType(), True), StructField("descricao", StringType(), True), StructField("icone", StringType(), True), StructField("categoria", StringType(), True), StructField("tipo_valor", StringType(), True), StructField("query_template", StringType(), True), StructField("formato", StringType(), True), StructField("ordem", IntegerType(), True), StructField("ativo", BooleanType(), True), StructField("destaque", BooleanType(), True), StructField("criado_por", StringType(), True), StructField("atualizado_em", TimestampType(), True)])
metricas_tuples = [(r.metrica_id, r.nome_exibicao, r.descricao, r.icone, r.categoria, r.tipo_valor, r.query_template, r.formato, r.ordem, r.ativo, r.destaque, r.criado_por, r.atualizado_em) for r in metricas_rows]
spark.createDataFrame(metricas_tuples, schema_metricas).write.mode("overwrite").saveAsTable(f"{CATALOG}.config.catalogo_metricas")

# config.regras_priorizacao
prior_rows = [
    Row(fator_id="potencial_renda", nome_exibicao="Potencial de Renda", descricao="Clientes com maior renda", peso=30, condicao_sql="renda_mensal > 15000", mensagem_insight="Cliente com alta renda", ativo=True, atualizado_por="admin", atualizado_em=datetime.now()),
    Row(fator_id="engajamento", nome_exibicao="Engajamento Digital", descricao="Clientes com alto engajamento", peso=25, condicao_sql="engajamento_score > 70", mensagem_insight="Cliente engajado digitalmente", ativo=True, atualizado_por="admin", atualizado_em=datetime.now()),
    Row(fator_id="churn_risk", nome_exibicao="Risco de Churn", descricao="Clientes com risco de saída", peso=20, condicao_sql="churn_score > 60", mensagem_insight="Cliente em risco", ativo=True, atualizado_por="admin", atualizado_em=datetime.now()),
    Row(fator_id="inadimplencia", nome_exibicao="Inadimplência", descricao="Clientes inadimplentes", peso=-10, condicao_sql="inadimplente = true", mensagem_insight="Cliente inadimplente", ativo=True, atualizado_por="admin", atualizado_em=datetime.now()),
]
schema_prior = StructType([StructField("fator_id", StringType(), False), StructField("nome_exibicao", StringType(), True), StructField("descricao", StringType(), True), StructField("peso", IntegerType(), True), StructField("condicao_sql", StringType(), True), StructField("mensagem_insight", StringType(), True), StructField("ativo", BooleanType(), True), StructField("atualizado_por", StringType(), True), StructField("atualizado_em", TimestampType(), True)])
prior_tuples = [(r.fator_id, r.nome_exibicao, r.descricao, r.peso, r.condicao_sql, r.mensagem_insight, r.ativo, r.atualizado_por, r.atualizado_em) for r in prior_rows]
spark.createDataFrame(prior_tuples, schema_prior).write.mode("overwrite").saveAsTable(f"{CATALOG}.config.regras_priorizacao")

# config.visao360_blocos
blocos_rows = [
    Row(bloco_id="cadastral", nome="Dados Cadastrais", icone="person", ordem=1, visivel=True, tipo="fixo", atualizado_por="admin", atualizado_em=datetime.now()),
    Row(bloco_id="financeiro", nome="Financeiro", icone="account_balance", ordem=2, visivel=True, tipo="fixo", atualizado_por="admin", atualizado_em=datetime.now()),
    Row(bloco_id="produtos", nome="Produtos", icone="shopping_bag", ordem=3, visivel=True, tipo="fixo", atualizado_por="admin", atualizado_em=datetime.now()),
    Row(bloco_id="comportamento", nome="Comportamento", icone="trending_up", ordem=4, visivel=True, tipo="customizavel", atualizado_por="admin", atualizado_em=datetime.now()),
]
schema_blocos = StructType([StructField("bloco_id", StringType(), False), StructField("nome", StringType(), True), StructField("icone", StringType(), True), StructField("ordem", IntegerType(), True), StructField("visivel", BooleanType(), True), StructField("tipo", StringType(), True), StructField("atualizado_por", StringType(), True), StructField("atualizado_em", TimestampType(), True)])
blocos_tuples = [(r.bloco_id, r.nome, r.icone, r.ordem, r.visivel, r.tipo, r.atualizado_por, r.atualizado_em) for r in blocos_rows]
spark.createDataFrame(blocos_tuples, schema_blocos).write.mode("overwrite").saveAsTable(f"{CATALOG}.config.visao360_blocos")

# config.visao360_campos
campos_rows = [
    Row(campo_id="renda_mensal", bloco_id="financeiro", visivel=True, ordem=1, label_override="Renda Mensal", atualizado_por="admin", atualizado_em=datetime.now()),
    Row(campo_id="faixa_renda", bloco_id="financeiro", visivel=True, ordem=2, label_override="Faixa de Renda", atualizado_por="admin", atualizado_em=datetime.now()),
    Row(campo_id="score", bloco_id="financeiro", visivel=False, ordem=3, label_override=None, atualizado_por="admin", atualizado_em=datetime.now()),
    Row(campo_id="idade", bloco_id="cadastral", visivel=True, ordem=1, label_override="Idade", atualizado_por="admin", atualizado_em=datetime.now()),
    Row(campo_id="faixa_etaria", bloco_id="cadastral", visivel=True, ordem=2, label_override="Faixa Etária", atualizado_por="admin", atualizado_em=datetime.now()),
    Row(campo_id="estado", bloco_id="cadastral", visivel=True, ordem=3, label_override="Estado", atualizado_por="admin", atualizado_em=datetime.now()),
    Row(campo_id="possui_cartao", bloco_id="produtos", visivel=True, ordem=1, label_override="Possui Cartão", atualizado_por="admin", atualizado_em=datetime.now()),
    Row(campo_id="engajamento_score", bloco_id="comportamento", visivel=True, ordem=1, label_override="Score Engajamento", atualizado_por="admin", atualizado_em=datetime.now()),
]
schema_campos = StructType([StructField("campo_id", StringType(), False), StructField("bloco_id", StringType(), True), StructField("visivel", BooleanType(), True), StructField("ordem", IntegerType(), True), StructField("label_override", StringType(), True), StructField("atualizado_por", StringType(), True), StructField("atualizado_em", TimestampType(), True)])
campos_tuples = [(r.campo_id, r.bloco_id, r.visivel, r.ordem, r.label_override, r.atualizado_por, r.atualizado_em) for r in campos_rows]
spark.createDataFrame(campos_tuples, schema_campos).write.mode("overwrite").saveAsTable(f"{CATALOG}.config.visao360_campos")

# config.visao360_contexto_segmentacao
contexto_rows = [
    Row(campo_seg="objetivo_negocio", visivel=True, ordem=1, label_override="Objetivo de Negócio", atualizado_por="admin", atualizado_em=datetime.now()),
    Row(campo_seg="publico_alvo_descricao", visivel=True, ordem=2, label_override="Público-Alvo", atualizado_por="admin", atualizado_em=datetime.now()),
    Row(campo_seg="seg_tags", visivel=False, ordem=3, label_override=None, atualizado_por="admin", atualizado_em=datetime.now()),
]
schema_contexto = StructType([StructField("campo_seg", StringType(), False), StructField("visivel", BooleanType(), True), StructField("ordem", IntegerType(), True), StructField("label_override", StringType(), True), StructField("atualizado_por", StringType(), True), StructField("atualizado_em", TimestampType(), True)])
contexto_tuples = [(r.campo_seg, r.visivel, r.ordem, r.label_override, r.atualizado_por, r.atualizado_em) for r in contexto_rows]
spark.createDataFrame(contexto_tuples, schema_contexto).write.mode("overwrite").saveAsTable(f"{CATALOG}.config.visao360_contexto_segmentacao")

# engagement.config_janela_envio
janela_rows = [
    Row(config_id="janela_email", canal="email", hora_inicio=8, hora_fim=22, dias_semana=["mon","tue","wed","thu","fri"], timezone="America/Sao_Paulo", ativo=True, atualizado_por="admin", atualizado_em=datetime.now()),
    Row(config_id="janela_whatsapp", canal="whatsapp", hora_inicio=9, hora_fim=21, dias_semana=["mon","tue","wed","thu","fri","sat"], timezone="America/Sao_Paulo", ativo=True, atualizado_por="admin", atualizado_em=datetime.now()),
    Row(config_id="janela_push", canal="push", hora_inicio=7, hora_fim=23, dias_semana=["mon","tue","wed","thu","fri","sat","sun"], timezone="America/Sao_Paulo", ativo=True, atualizado_por="admin", atualizado_em=datetime.now()),
]
schema_janela = StructType([StructField("config_id", StringType(), False), StructField("canal", StringType(), True), StructField("hora_inicio", IntegerType(), True), StructField("hora_fim", IntegerType(), True), StructField("dias_semana", ArrayType(StringType()), True), StructField("timezone", StringType(), True), StructField("ativo", BooleanType(), True), StructField("atualizado_por", StringType(), True), StructField("atualizado_em", TimestampType(), True)])
janela_tuples = [(r.config_id, r.canal, r.hora_inicio, r.hora_fim, r.dias_semana, r.timezone, r.ativo, r.atualizado_por, r.atualizado_em) for r in janela_rows]
spark.createDataFrame(janela_tuples, schema_janela).write.mode("overwrite").saveAsTable(f"{CATALOG}.engagement.config_janela_envio")

# engagement.config_retry
retry_rows = [
    Row(config_id="retry_email", canal="email", max_tentativas=3, backoff_minutos=[1,5,30], ativo=True, atualizado_por="admin", atualizado_em=datetime.now()),
    Row(config_id="retry_whatsapp", canal="whatsapp", max_tentativas=2, backoff_minutos=[5,30], ativo=True, atualizado_por="admin", atualizado_em=datetime.now()),
    Row(config_id="retry_push", canal="push", max_tentativas=3, backoff_minutos=[1,10,60], ativo=True, atualizado_por="admin", atualizado_em=datetime.now()),
]
schema_retry = StructType([StructField("config_id", StringType(), False), StructField("canal", StringType(), True), StructField("max_tentativas", IntegerType(), True), StructField("backoff_minutos", ArrayType(IntegerType()), True), StructField("ativo", BooleanType(), True), StructField("atualizado_por", StringType(), True), StructField("atualizado_em", TimestampType(), True)])
retry_tuples = [(r.config_id, r.canal, r.max_tentativas, r.backoff_minutos, r.ativo, r.atualizado_por, r.atualizado_em) for r in retry_rows]
spark.createDataFrame(retry_tuples, schema_retry).write.mode("overwrite").saveAsTable(f"{CATALOG}.engagement.config_retry")

# engagement.config_conversao
conv_rows = [
    Row(config_id="conv_global", escopo="global", evento_conversao="converteu", janela_dias=30, ativo=True, atualizado_por="admin", atualizado_em=datetime.now()),
    Row(config_id="conv_campanha_default", escopo="por_campanha", evento_conversao="clicou", janela_dias=14, ativo=True, atualizado_por="admin", atualizado_em=datetime.now()),
]
schema_conv = StructType([StructField("config_id", StringType(), False), StructField("escopo", StringType(), True), StructField("evento_conversao", StringType(), True), StructField("janela_dias", IntegerType(), True), StructField("ativo", BooleanType(), True), StructField("atualizado_por", StringType(), True), StructField("atualizado_em", TimestampType(), True)])
conv_tuples = [(r.config_id, r.escopo, r.evento_conversao, r.janela_dias, r.ativo, r.atualizado_por, r.atualizado_em) for r in conv_rows]
spark.createDataFrame(conv_tuples, schema_conv).write.mode("overwrite").saveAsTable(f"{CATALOG}.engagement.config_conversao")

# engagement.config_otimizacao
otim_rows = [
    Row(config_id="mab_global", escopo="global", metrica_alvo="conversao", metrica_custom_json=None, janela_avaliacao_horas=72, trafego_minimo_pct=10, min_amostras_por_variante=100, frequencia_recalculo="diario", otimizacao_ativa=True, ativo=True, atualizado_por="admin", atualizado_em=datetime.now()),
    Row(config_id="mab_jornada_default", escopo="por_jornada", metrica_alvo="clique", metrica_custom_json=None, janela_avaliacao_horas=48, trafego_minimo_pct=20, min_amostras_por_variante=200, frequencia_recalculo="diario", otimizacao_ativa=True, ativo=True, atualizado_por="admin", atualizado_em=datetime.now()),
]
schema_otim = StructType([StructField("config_id", StringType(), False), StructField("escopo", StringType(), True), StructField("metrica_alvo", StringType(), True), StructField("metrica_custom_json", StringType(), True), StructField("janela_avaliacao_horas", IntegerType(), True), StructField("trafego_minimo_pct", IntegerType(), True), StructField("min_amostras_por_variante", IntegerType(), True), StructField("frequencia_recalculo", StringType(), True), StructField("otimizacao_ativa", BooleanType(), True), StructField("ativo", BooleanType(), True), StructField("atualizado_por", StringType(), True), StructField("atualizado_em", TimestampType(), True)])
otim_tuples = [(r.config_id, r.escopo, r.metrica_alvo, r.metrica_custom_json, r.janela_avaliacao_horas, r.trafego_minimo_pct, r.min_amostras_por_variante, r.frequencia_recalculo, r.otimizacao_ativa, r.ativo, r.atualizado_por, r.atualizado_em) for r in otim_rows]
spark.createDataFrame(otim_tuples, schema_otim).write.mode("overwrite").saveAsTable(f"{CATALOG}.engagement.config_otimizacao")

# engagement.config_jornada_politica
politica_rows = [
    Row(politica_id="politica_global", escopo="global", ao_sair_segmento="continua", ao_pausar_campanha="termina_quem_entrou", cap_estourado="pula", reentrada="permitida", reentrada_dias=30, ao_editar_ativa="versao_congelada", permite_loop=True, loop_max_iteracoes_teto=3, loop_max_dias_teto=15, ativo=True, atualizado_por="admin", atualizado_em=datetime.now()),
]
schema_politica = StructType([StructField("politica_id", StringType(), False), StructField("escopo", StringType(), True), StructField("ao_sair_segmento", StringType(), True), StructField("ao_pausar_campanha", StringType(), True), StructField("cap_estourado", StringType(), True), StructField("reentrada", StringType(), True), StructField("reentrada_dias", IntegerType(), True), StructField("ao_editar_ativa", StringType(), True), StructField("permite_loop", BooleanType(), True), StructField("loop_max_iteracoes_teto", IntegerType(), True), StructField("loop_max_dias_teto", IntegerType(), True), StructField("ativo", BooleanType(), True), StructField("atualizado_por", StringType(), True), StructField("atualizado_em", TimestampType(), True)])
politica_tuples = [(r.politica_id, r.escopo, r.ao_sair_segmento, r.ao_pausar_campanha, r.cap_estourado, r.reentrada, r.reentrada_dias, r.ao_editar_ativa, r.permite_loop, r.loop_max_iteracoes_teto, r.loop_max_dias_teto, r.ativo, r.atualizado_por, r.atualizado_em) for r in politica_rows]
spark.createDataFrame(politica_tuples, schema_politica).write.mode("overwrite").saveAsTable(f"{CATALOG}.engagement.config_jornada_politica")

print("  OK")

# COMMAND ----------

# 10. DADOS DE CAMPANHA, JORNADA, PEÇA (mais completos)
print("10. Campanhas, Jornadas, Peças...")
# Campanha
campanha_id = "camp_001"
schema_camp = StructType([StructField("campanha_id", StringType(), False), StructField("campanha_codigo", StringType(), True), StructField("nome", StringType(), True), StructField("descricao", StringType(), True), StructField("objetivo", StringType(), True), StructField("tags", ArrayType(StringType()), True), StructField("resumo", StringType(), True), StructField("objetivo_negocio", StringType(), True), StructField("observacoes", StringType(), True), StructField("owner", StringType(), True), StructField("area_responsavel", StringType(), True), StructField("email_contato", StringType(), True), StructField("criado_por", StringType(), True), StructField("status", StringType(), True), StructField("vigencia_inicio", TimestampType(), True), StructField("vigencia_fim", TimestampType(), True), StructField("limite_envios", LongType(), True), StructField("alerta_pct_limite", IntegerType(), True), StructField("envios_realizados", LongType(), True), StructField("versao_atual", IntegerType(), True), StructField("atualizado_em", TimestampType(), True)])
camp_tuples = [(campanha_id, "CAM-2025-CROSSSELL-00001", "Campanha Cross-Sell Q3", "Oferta de produtos financeiros", "RENTABILIZACAO", ["cross-sell","q3"], "Oferta de produtos financeiros", "Aumentar rentabilidade", "Usar segmentos de alta renda", "marketing", "Marketing", "marketing@banco.com", "admin", "ativa", datetime.now(), datetime.now()+timedelta(days=90), int(100000), int(80), int(0), int(1), datetime.now())]
spark.createDataFrame(camp_tuples, schema_camp).write.mode("overwrite").saveAsTable(f"{CATALOG}.engagement.campanha")

# Jornada (conforme DDL real)
jornada_id = "jorn_001"
schema_jorn = StructType([StructField("jornada_id", StringType(), False), StructField("jornada_codigo", StringType(), True), StructField("nome", StringType(), True), StructField("descricao", StringType(), True), StructField("tags", ArrayType(StringType()), True), StructField("tipo", StringType(), True), StructField("tipo_gatilho", StringType(), True), StructField("gatilho_seg_id", StringType(), True), StructField("gatilho_evento", StringType(), True), StructField("gatilho_data", TimestampType(), True), StructField("multiplo_envio_permitido", BooleanType(), True), StructField("intervalo_reenvio_dias", IntegerType(), True), StructField("fluxo_json", StringType(), True), StructField("criado_por", StringType(), True), StructField("criado_em", TimestampType(), True), StructField("versao_atual", IntegerType(), True), StructField("status", StringType(), True), StructField("atualizado_em", TimestampType(), True)])
jorn_tuples = [(jornada_id, "JOR-2025-00001", "Jornada Cross-Sell", "Fluxo de oferta com 3 etapas", ["cross-sell","email"], "scheduled", "segmento", "seg_alta_renda", None, None, False, int(7), '{"nodes":[{"id":"n1","type":"start","data":{"label":"Início"}},{"id":"n2","type":"email","data":{"label":"Envio Email"}},{"id":"n3","type":"wait","data":{"label":"Aguardar"}},{"id":"n4","type":"end","data":{"label":"Fim"}}],"edges":[{"source":"n1","target":"n2"},{"source":"n2","target":"n3"},{"source":"n3","target":"n4"}]}', "admin", datetime.now(), int(1), "ativa", datetime.now())]
spark.createDataFrame(jorn_tuples, schema_jorn).write.mode("overwrite").saveAsTable(f"{CATALOG}.engagement.jornada")

# Relação campanha_jornada (removida - não existe no DDL)

# Peça (conforme DDL real)
peca_id = "peca_001"
schema_peca = StructType([StructField("peca_id", StringType(), False), StructField("peca_codigo", StringType(), True), StructField("nome", StringType(), True), StructField("descricao", StringType(), True), StructField("canal_id", StringType(), True), StructField("tipo_conteudo", StringType(), True), StructField("template_html", StringType(), True), StructField("template_texto", StringType(), True), StructField("subject", StringType(), True), StructField("personalizacao_json", StringType(), True), StructField("bloco_variaveis_permitidas_json", StringType(), True), StructField("preview_desktop_url", StringType(), True), StructField("preview_mobile_url", StringType(), True), StructField("tags", ArrayType(StringType()), True), StructField("criado_por", StringType(), True), StructField("criado_em", TimestampType(), True), StructField("versao_atual", IntegerType(), True), StructField("atualizado_em", TimestampType(), True), StructField("ativo", BooleanType(), True)])
peca_tuples = [(peca_id, "PEC-2025-EMAIL-00001", "Oferta Cross-Sell Email", "Email com oferta de cartão e investimentos", "email", "html", "<p>Olá {{nome}}, aproveite nossa oferta exclusiva!</p><p>Renda: {{renda_mensal}}</p>", "Olá [nome], aproveite nossa oferta exclusiva! Renda: [renda_mensal]", "Aproveite a oferta exclusiva", '{"nome": "string", "renda_mensal": "double"}', '{"permitidas": ["renda_mensal", "possui_cartao"]}', None, None, ["cross-sell","email"], "admin", datetime.now(), int(1), datetime.now(), True)]
spark.createDataFrame(peca_tuples, schema_peca).write.mode("overwrite").saveAsTable(f"{CATALOG}.engagement.peca")

print("  OK")

# COMMAND ----------

# DBTITLE 1,11. Segmentação S1 (regras_json alinhado com RegrasJson model)
# 11. DADOS INICIAIS DE SEGMENTAÇÃO (S1)
# Formato correto: RegrasJson { publico_base, inclusao: RegraNo, exclusao: RegraNo|null }
# RegraNo: { operator: AND|OR, rules: [RegraFolha|RegraNo] }
# RegraFolha: { campo_id, op, value }
print("11. Segmentação (S1)...")
import json as _json

seg_ids = ["seg_alta_renda", "seg_digital"]

# Regras no formato CORRETO do modelo RegrasJson
regras_alta_renda = _json.dumps({
    "publico_base": "pub_varejo",
    "inclusao": {
        "operator": "AND",
        "rules": [
            {"campo_id": "renda_mensal", "op": ">=", "value": 10000},
            {"campo_id": "score", "op": ">", "value": 600}
        ]
    },
    "exclusao": {
        "operator": "OR",
        "rules": [
            {"campo_id": "inadimplente", "op": "=", "value": True}
        ]
    }
})
regras_digital = _json.dumps({
    "publico_base": "pub_varejo",
    "inclusao": {
        "operator": "AND",
        "rules": [
            {"campo_id": "usa_app", "op": "=", "value": True},
            {"campo_id": "engajamento_score", "op": ">", "value": 60}
        ]
    },
    "exclusao": None
})

# Inserir definições
seg_def_rows = [
    Row(seg_id=seg_ids[0], seg_codigo="SEG-ALTA-RENDA", seg_slug="alta-renda", nome="Alta Renda Varejo", descricao="Clientes varejo com renda > 10k", objetivo="AQUISICAO", seg_tags=["varejo","alta-renda"], resumo="Público de alta renda do varejo", objetivo_negocio="Aumentar cross-sell", publico_alvo_descricao="Clientes varejo com alta renda", observacoes=None, documentacao_md="# Alta Renda\nSegmento para ofertas de produtos premium.", owner=MAIN_USER, area_responsavel="Marketing", email_contato="marketing@banco.com", criado_por=MAIN_USER, criado_em=datetime.now(), seg_origem_id=None, tipo_origem="nova", tipo="direta", publico_base_id="pub_varejo", regras_json=regras_alta_renda, status="ativa", vigencia_inicio=datetime.now(), vigencia_fim=datetime.now()+timedelta(days=90), agendamento_cron=None, recorrencia="once", aprovado_por=MAIN_USER, aprovado_em=datetime.now(), checklist_validacao_json=None, versao_atual=1, atualizado_em=datetime.now(), habilitado=True),
    Row(seg_id=seg_ids[1], seg_codigo="SEG-DIGITAL", seg_slug="digital", nome="Clientes Digitais", descricao="Clientes que usam app e têm alto engajamento", objetivo="ENGAJAMENTO", seg_tags=["digital","app"], resumo="Público digital engajado", objetivo_negocio="Aumentar uso digital", publico_alvo_descricao="Clientes com alta interação digital", observacoes=None, documentacao_md="# Digital\nSegmento para ofertas digitais.", owner=MAIN_USER, area_responsavel="Digital", email_contato="digital@banco.com", criado_por=MAIN_USER, criado_em=datetime.now(), seg_origem_id=None, tipo_origem="nova", tipo="direta", publico_base_id="pub_varejo", regras_json=regras_digital, status="ativa", vigencia_inicio=datetime.now(), vigencia_fim=datetime.now()+timedelta(days=90), agendamento_cron=None, recorrencia="once", aprovado_por=MAIN_USER, aprovado_em=datetime.now(), checklist_validacao_json=None, versao_atual=1, atualizado_em=datetime.now(), habilitado=True),
]
schema_seg_def = StructType([StructField("seg_id", StringType(), False), StructField("seg_codigo", StringType(), True), StructField("seg_slug", StringType(), True), StructField("nome", StringType(), True), StructField("descricao", StringType(), True), StructField("objetivo", StringType(), True), StructField("seg_tags", ArrayType(StringType()), True), StructField("resumo", StringType(), True), StructField("objetivo_negocio", StringType(), True), StructField("publico_alvo_descricao", StringType(), True), StructField("observacoes", StringType(), True), StructField("documentacao_md", StringType(), True), StructField("owner", StringType(), True), StructField("area_responsavel", StringType(), True), StructField("email_contato", StringType(), True), StructField("criado_por", StringType(), True), StructField("criado_em", TimestampType(), True), StructField("seg_origem_id", StringType(), True), StructField("tipo_origem", StringType(), True), StructField("tipo", StringType(), True), StructField("publico_base_id", StringType(), True), StructField("regras_json", StringType(), True), StructField("status", StringType(), True), StructField("vigencia_inicio", TimestampType(), True), StructField("vigencia_fim", TimestampType(), True), StructField("agendamento_cron", StringType(), True), StructField("recorrencia", StringType(), True), StructField("aprovado_por", StringType(), True), StructField("aprovado_em", TimestampType(), True), StructField("checklist_validacao_json", StringType(), True), StructField("versao_atual", IntegerType(), True), StructField("atualizado_em", TimestampType(), True), StructField("habilitado", BooleanType(), True), StructField("job_id_databricks", StringType(), True)])
seg_def_tuples = [(r.seg_id, r.seg_codigo, r.seg_slug, r.nome, r.descricao, r.objetivo, r.seg_tags, r.resumo, r.objetivo_negocio, r.publico_alvo_descricao, r.observacoes, r.documentacao_md, r.owner, r.area_responsavel, r.email_contato, r.criado_por, r.criado_em, r.seg_origem_id, r.tipo_origem, r.tipo, r.publico_base_id, r.regras_json, r.status, r.vigencia_inicio, r.vigencia_fim, r.agendamento_cron, r.recorrencia, r.aprovado_por, r.aprovado_em, r.checklist_validacao_json, r.versao_atual, r.atualizado_em, r.habilitado, None) for r in seg_def_rows]
spark.createDataFrame(seg_def_tuples, schema_seg_def).write.mode("overwrite").saveAsTable(f"{CATALOG}.segmentacao.seg_definicao")

# Destino (seg_destino - conforme DDL: seg_id, destino, habilitado, criado_em)
seg_dest_rows = [
    Row(seg_id=seg_ids[0], destino="sistema2", habilitado=True, criado_em=datetime.now()),
    Row(seg_id=seg_ids[0], destino="sistema3", habilitado=True, criado_em=datetime.now()),
    Row(seg_id=seg_ids[1], destino="sistema2", habilitado=True, criado_em=datetime.now()),
    Row(seg_id=seg_ids[1], destino="sistema3", habilitado=True, criado_em=datetime.now()),
]
schema_seg_dest = StructType([StructField("seg_id", StringType(), False), StructField("destino", StringType(), True), StructField("habilitado", BooleanType(), True), StructField("criado_em", TimestampType(), True)])
seg_dest_tuples = [(r.seg_id, r.destino, r.habilitado, r.criado_em) for r in seg_dest_rows]
spark.createDataFrame(seg_dest_tuples, schema_seg_dest).write.mode("overwrite").saveAsTable(f"{CATALOG}.segmentacao.seg_destino")

# Execução (simulada) - para cada segmento, gerar resultado corrente
print("  Gerando seg_execucao e seg_resultado_corrente...")
exec_id1 = f"exec_{uuid.uuid4().hex[:12]}"
exec_id2 = f"exec_{uuid.uuid4().hex[:12]}"

# Simular execução: para cada segmento, selecionar CPFs que atendem às regras
# Vamos fazer uma consulta simples no Spark, mas para simplificar, usamos a lógica manual baseada nos dados gerados.
# Como temos os dados em clientes_data, podemos filtrar.
# Para "Alta Renda": segmento varejo e renda > 10000
# Filtro alinhado com regras_json: pub_varejo(segmento==varejo) + renda>=10000 + score>600 - inadimplentes
alta_renda_cpfs = [d["cpf_cnpj"] for d in clientes_data if d["segmento"] == "varejo" and d["renda_mensal"] >= 10000 and d["score"] > 600 and not d["inadimplente"]]
digital_cpfs = [d["cpf_cnpj"] for d in clientes_data if d["usa_app"] and d["engajamento_score"] > 60]

# Inserir execuções
exec_rows = [
    Row(exec_id=exec_id1, seg_id=seg_ids[0], versao_usada=1, origem_execucao="manual", executado_em=datetime.now(), qtd_clientes=len(alta_renda_cpfs), status="sucesso", job_id=None, run_id=None, job_run_url=None),
    Row(exec_id=exec_id2, seg_id=seg_ids[1], versao_usada=1, origem_execucao="manual", executado_em=datetime.now(), qtd_clientes=len(digital_cpfs), status="sucesso", job_id=None, run_id=None, job_run_url=None),
]
schema_exec = StructType([StructField("exec_id", StringType(), False), StructField("seg_id", StringType(), True), StructField("versao_usada", IntegerType(), True), StructField("origem_execucao", StringType(), True), StructField("executado_em", TimestampType(), True), StructField("qtd_clientes", LongType(), True), StructField("status", StringType(), True), StructField("job_id", StringType(), True), StructField("run_id", StringType(), True), StructField("job_run_url", StringType(), True)])
exec_tuples = [(r.exec_id, r.seg_id, r.versao_usada, r.origem_execucao, r.executado_em, r.qtd_clientes, r.status, r.job_id, r.run_id, r.job_run_url) for r in exec_rows]
spark.createDataFrame(exec_tuples, schema_exec).write.mode("overwrite").saveAsTable(f"{CATALOG}.segmentacao.seg_execucao")

# Inserir resultado corrente
result_rows = []
for cpf in alta_renda_cpfs:
    result_rows.append(Row(seg_id=seg_ids[0], cpf_cnpj=cpf, exec_id=exec_id1, entrou_em=datetime.now()))
for cpf in digital_cpfs:
    result_rows.append(Row(seg_id=seg_ids[1], cpf_cnpj=cpf, exec_id=exec_id2, entrou_em=datetime.now()))
if result_rows:
    spark.createDataFrame(result_rows).write.mode("overwrite").saveAsTable(f"{CATALOG}.segmentacao.seg_resultado_corrente")
else:
    # Caso não haja clientes, cria vazio com schema correto
    spark.createDataFrame([], schema=StructType([
        StructField("seg_id", StringType(), True),
        StructField("cpf_cnpj", StringType(), True),
        StructField("exec_id", StringType(), True),
        StructField("entrou_em", TimestampType(), True)
    ])).write.mode("overwrite").saveAsTable(f"{CATALOG}.segmentacao.seg_resultado_corrente")

# Atualizar o gatilho_seg_id da jornada para o primeiro segmento (para testar S3)
spark.sql(f"UPDATE {CATALOG}.engagement.jornada SET gatilho_seg_id = '{seg_ids[0]}' WHERE jornada_id = 'jorn_001'")

print("  OK")

# COMMAND ----------

# DBTITLE 1,12. Tabelas auxiliares S1 (saúde + histórico estado + versão)
# 12. TABELAS AUXILIARES S1
# Garantir que tabelas acessíveis pelo backend existam com dados mínimos.
# Estas tabelas são lidas durante transições de estado e dashboards.
print("12. Tabelas auxiliares S1...")

# seg_saude (dashboard de saúde)
saude_rows = [
    Row(seg_id="seg_alta_renda", health_status="verde", ultima_verificacao=datetime.now(),
        variacao_publico_pct=2.5, taxa_sucesso_exec=100.0, tempo_medio_exec_seg=15,
        alertas_json=None, publico_atual=int(len(alta_renda_cpfs))),
    Row(seg_id="seg_digital", health_status="verde", ultima_verificacao=datetime.now(),
        variacao_publico_pct=-1.2, taxa_sucesso_exec=100.0, tempo_medio_exec_seg=12,
        alertas_json=None, publico_atual=int(len(digital_cpfs))),
]
schema_saude = StructType([
    StructField("seg_id", StringType(), False),
    StructField("health_status", StringType(), True),
    StructField("ultima_verificacao", TimestampType(), True),
    StructField("variacao_publico_pct", DoubleType(), True),
    StructField("taxa_sucesso_exec", DoubleType(), True),
    StructField("tempo_medio_exec_seg", IntegerType(), True),
    StructField("alertas_json", StringType(), True),
    StructField("publico_atual", LongType(), True)
])
saude_tuples = [(r.seg_id, r.health_status, r.ultima_verificacao, r.variacao_publico_pct, r.taxa_sucesso_exec, r.tempo_medio_exec_seg, r.alertas_json, r.publico_atual) for r in saude_rows]
spark.createDataFrame(saude_tuples, schema_saude).write.mode("overwrite").saveAsTable(f"{CATALOG}.segmentacao.seg_saude")
print("  seg_saude: 2 registros")

# seg_versao (histórico de versões)
versao_rows = [
    Row(versao_id=f"v_{uuid.uuid4().hex[:8]}", seg_id="seg_alta_renda", versao=1,
        regras_json=regras_alta_renda, motivo="Criação inicial",
        alterado_por=MAIN_USER, alterado_em=datetime.now()),
    Row(versao_id=f"v_{uuid.uuid4().hex[:8]}", seg_id="seg_digital", versao=1,
        regras_json=regras_digital, motivo="Criação inicial",
        alterado_por=MAIN_USER, alterado_em=datetime.now()),
]
schema_versao = StructType([
    StructField("versao_id", StringType(), False),
    StructField("seg_id", StringType(), True),
    StructField("versao", IntegerType(), True),
    StructField("regras_json", StringType(), True),
    StructField("motivo", StringType(), True),
    StructField("alterado_por", StringType(), True),
    StructField("alterado_em", TimestampType(), True)
])
versao_tuples = [(r.versao_id, r.seg_id, r.versao, r.regras_json, r.motivo, r.alterado_por, r.alterado_em) for r in versao_rows]
spark.createDataFrame(versao_tuples, schema_versao).write.mode("overwrite").saveAsTable(f"{CATALOG}.segmentacao.seg_versao")
print("  seg_versao: 2 registros")

# seg_historico_estado (auditoria de transições)
hist_rows = [
    Row(hist_id=f"h_{uuid.uuid4().hex[:8]}", seg_id="seg_alta_renda",
        estado_anterior="rascunho", estado_novo="em_aprovacao",
        motivo="Pronto para revisão", alterado_por=MAIN_USER, alterado_em=datetime.now() - timedelta(hours=2)),
    Row(hist_id=f"h_{uuid.uuid4().hex[:8]}", seg_id="seg_alta_renda",
        estado_anterior="em_aprovacao", estado_novo="aprovada",
        motivo="Checklist OK", alterado_por=MAIN_USER, alterado_em=datetime.now() - timedelta(hours=1)),
    Row(hist_id=f"h_{uuid.uuid4().hex[:8]}", seg_id="seg_alta_renda",
        estado_anterior="aprovada", estado_novo="ativa",
        motivo="Job criado", alterado_por=MAIN_USER, alterado_em=datetime.now()),
]
schema_hist = StructType([
    StructField("hist_id", StringType(), False),
    StructField("seg_id", StringType(), True),
    StructField("estado_anterior", StringType(), True),
    StructField("estado_novo", StringType(), True),
    StructField("motivo", StringType(), True),
    StructField("alterado_por", StringType(), True),
    StructField("alterado_em", TimestampType(), True)
])
hist_tuples = [(r.hist_id, r.seg_id, r.estado_anterior, r.estado_novo, r.motivo, r.alterado_por, r.alterado_em) for r in hist_rows]
spark.createDataFrame(hist_tuples, schema_hist).write.mode("overwrite").saveAsTable(f"{CATALOG}.segmentacao.seg_historico_estado")
print("  seg_historico_estado: 3 registros")

# seg_comentario (vazio com schema)
spark.createDataFrame([], StructType([
    StructField("comentario_id", StringType(), False),
    StructField("seg_id", StringType(), True),
    StructField("versao_referencia", IntegerType(), True),
    StructField("tipo", StringType(), True),
    StructField("autor", StringType(), True),
    StructField("texto", StringType(), True),
    StructField("respondendo_a", StringType(), True),
    StructField("mencoes", ArrayType(StringType()), True),
    StructField("resolvido", BooleanType(), True),
    StructField("criado_em", TimestampType(), True),
    StructField("editado_em", TimestampType(), True)
])).write.mode("overwrite").saveAsTable(f"{CATALOG}.segmentacao.seg_comentario")

# seg_notificacao (vazio com schema)
spark.createDataFrame([], StructType([
    StructField("notif_id", StringType(), False),
    StructField("destinatario", StringType(), True),
    StructField("tipo", StringType(), True),
    StructField("seg_id", StringType(), True),
    StructField("titulo", StringType(), True),
    StructField("mensagem", StringType(), True),
    StructField("lida", BooleanType(), True),
    StructField("criado_em", TimestampType(), True)
])).write.mode("overwrite").saveAsTable(f"{CATALOG}.segmentacao.seg_notificacao")

# seg_job_log (vazio com schema)
spark.createDataFrame([], StructType([
    StructField("log_id", StringType(), False),
    StructField("seg_id", StringType(), True),
    StructField("acao", StringType(), True),
    StructField("job_id", StringType(), True),
    StructField("run_id", StringType(), True),
    StructField("status", StringType(), True),
    StructField("detalhes", StringType(), True),
    StructField("executado_por", StringType(), True),
    StructField("criado_em", TimestampType(), True)
])).write.mode("overwrite").saveAsTable(f"{CATALOG}.segmentacao.seg_job_log")

# seg_resultado_historico (vazio)
spark.createDataFrame([], StructType([
    StructField("exec_id", StringType(), False),
    StructField("seg_id", StringType(), True),
    StructField("versao_usada", IntegerType(), True),
    StructField("cpf_cnpj", StringType(), True),
    StructField("snapshot_em", TimestampType(), True)
])).write.mode("overwrite").saveAsTable(f"{CATALOG}.segmentacao.seg_resultado_historico")

# seg_eventos (vazio)
spark.createDataFrame([], StructType([
    StructField("evento_id", StringType(), False),
    StructField("seg_id", StringType(), True),
    StructField("exec_id", StringType(), True),
    StructField("tipo_evento", StringType(), True),
    StructField("destino", StringType(), True),
    StructField("payload_json", StringType(), True),
    StructField("criado_em", TimestampType(), True)
])).write.mode("overwrite").saveAsTable(f"{CATALOG}.eventos.seg_eventos")

# catalogo_governanca_hist (vazio)
spark.createDataFrame([], StructType([
    StructField("hist_id", StringType(), False),
    StructField("caracteristica_id", StringType(), True),
    StructField("campo_label", StringType(), True),
    StructField("flag_alterada", StringType(), True),
    StructField("sistema_alvo", StringType(), True),
    StructField("valor_anterior", StringType(), True),
    StructField("valor_novo", StringType(), True),
    StructField("acao", StringType(), True),
    StructField("alterado_por", StringType(), True),
    StructField("alterado_em", TimestampType(), True)
])).write.mode("overwrite").saveAsTable(f"{CATALOG}.metadata.catalogo_governanca_hist")

print("  Tabelas auxiliares (vazias com schema): seg_comentario, seg_notificacao, seg_job_log, seg_resultado_historico, seg_eventos, catalogo_governanca_hist")
print("  OK")

# COMMAND ----------

print("\n🎉 SEED 100% CONCLUÍDO COM SUCESSO!")
print(f"Foram gerados {NUM_CLIENTES} clientes.")
print("Todas as tabelas necessárias para a POC estão populadas.")
print("Agora você pode iniciar a implementação dos cartões ou testar os endpoints.")
