# Databricks notebook source
# ============================================================
# SEED COMPLETO PARA PLATAFORMA CDP - VERSÃO FINAL
# ============================================================
# Popula TODAS as tabelas necessárias para a POC.
# %pip install faker
# dbutils.library.restartPython()

# COMMAND ----------

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
        "tempo_relacionamento_meses": random.randint(1, 240),
        # Wide
        "renda_mensal": renda,
        "faixa_renda": "baixa" if renda < 5000 else "media" if renda < 15000 else "alta",
        "renda_comprovada": random.choice([True, False]),
        "saldo_medio": saldo,
        "saldo_atual": saldo + random.uniform(-1000, 1000),
        "faixa_saldo": "baixo" if saldo < 5000 else "medio" if saldo < 20000 else "alto",
        "score": score,
        "faixa_score": "baixo" if score < 500 else "medio" if score < 700 else "alto",
        "valor_endividamento": endividamento,
        "comprometimento_renda_pct": round(endividamento / (renda + 1) * 100, 2) if renda > 0 else 0,
        "inadimplente": random.choice([True, False]),
        "idade": idade,
        "faixa_etaria": "18-25" if idade < 26 else "26-35" if idade < 36 else "36-50" if idade < 51 else "51-65" if idade < 66 else "65+",
        "genero": random.choice(["M", "F"]),
        "estado": fake.state_abbr(),
        "cidade": fake.city(),
        "estado_civil": random.choice(["Solteiro", "Casado", "Divorciado", "Viúvo"]),
        "profissao": random.choice(["Administrador", "Engenheiro", "Médico", "Professor", "Autônomo", "Empresário"]),
        "setor": random.choice(["Público", "Privado", "ONG"]),
        "tipo_vinculo": random.choice(["CLT", "PJ", "Servidor Público", "Aposentado"]),
        "escolaridade": random.choice(["Ensino Médio", "Graduação", "Pós-graduação", "Mestrado"]),
        "possui_conta": random.choice([True, False]),
        "tempo_conta_meses": random.randint(1, 240),
        "tipo_conta": random.choice(["Comum", "Universitária", "Digital"]),
        "possui_cartao": random.choice([True, False]),
        "qtd_cartoes": random.randint(0, 5),
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
        "qtd_transacoes_mes": random.randint(0, 50),
        "ticket_medio": round(random.uniform(10, 500), 2),
        "valor_movimentado_mes": round(random.uniform(0, 20000), 2),
        "usa_app": random.choice([True, False]),
        "usa_internet_banking": random.choice([True, False]),
        "canal_preferido": random.choice(["App", "Internet", "Agência"]),
        "frequencia_acesso": random.choice(["Diário", "Semanal", "Mensal", "Esporádico"]),
        "nps": random.randint(-100, 100),
        "churn_score": round(random.uniform(0, 100), 2),
        "engajamento_score": round(random.uniform(0, 100), 2),
    }

clientes_data = [gerar_cliente(cpf) for cpf in cpf_list]

# COMMAND ----------

# 1. GOLDEN RECORD
print("1. Golden Record...")
golden_rows = [Row(
    cpf_cnpj=d["cpf_cnpj"],
    nome=d["nome"],
    email=d["email"],
    telefone=d["telefone"],
    segmento=d["segmento"],
    data_nascimento=d["data_nascimento"],
    agencia=d["agencia"],
    gerente_nome=d["gerente_nome"],
    tempo_relacionamento_meses=d["tempo_relacionamento_meses"]
) for d in clientes_data]
spark.createDataFrame(golden_rows).write.mode("overwrite").saveAsTable(f"{CATALOG}.core_cliente.golden_record")
print("  OK")

# COMMAND ----------

# 2. CUSTOMER_FEATURES_WIDE
print("2. Customer Features Wide...")
wide_rows = [Row(
    cpf_cnpj=d["cpf_cnpj"],
    renda_mensal=d["renda_mensal"],
    faixa_renda=d["faixa_renda"],
    renda_comprovada=d["renda_comprovada"],
    saldo_medio=d["saldo_medio"],
    saldo_atual=d["saldo_atual"],
    faixa_saldo=d["faixa_saldo"],
    score=d["score"],
    faixa_score=d["faixa_score"],
    valor_endividamento=d["valor_endividamento"],
    comprometimento_renda_pct=d["comprometimento_renda_pct"],
    inadimplente=d["inadimplente"],
    idade=d["idade"],
    faixa_etaria=d["faixa_etaria"],
    genero=d["genero"],
    estado=d["estado"],
    cidade=d["cidade"],
    estado_civil=d["estado_civil"],
    profissao=d["profissao"],
    setor=d["setor"],
    tipo_vinculo=d["tipo_vinculo"],
    escolaridade=d["escolaridade"],
    possui_conta=d["possui_conta"],
    tempo_conta_meses=d["tempo_conta_meses"],
    tipo_conta=d["tipo_conta"],
    possui_cartao=d["possui_cartao"],
    qtd_cartoes=d["qtd_cartoes"],
    limite_total=d["limite_total"],
    bandeira=d["bandeira"],
    fatura_media=d["fatura_media"],
    possui_investimento=d["possui_investimento"],
    valor_investido=d["valor_investido"],
    perfil_investidor=d["perfil_investidor"],
    possui_seguro=d["possui_seguro"],
    tipos_seguro=d["tipos_seguro"],
    possui_credito=d["possui_credito"],
    valor_credito_contratado=d["valor_credito_contratado"],
    tipo_credito=d["tipo_credito"],
    qtd_transacoes_mes=d["qtd_transacoes_mes"],
    ticket_medio=d["ticket_medio"],
    valor_movimentado_mes=d["valor_movimentado_mes"],
    usa_app=d["usa_app"],
    usa_internet_banking=d["usa_internet_banking"],
    canal_preferido=d["canal_preferido"],
    frequencia_acesso=d["frequencia_acesso"],
    nps=d["nps"],
    churn_score=d["churn_score"],
    engajamento_score=d["engajamento_score"],
    atualizado_em=datetime.now()
) for d in clientes_data]
spark.createDataFrame(wide_rows).write.mode("overwrite").saveAsTable(f"{CATALOG}.caracteristicas.customer_features_wide")
print("  OK")

# COMMAND ----------

# 3. TABELAS TB_*
print("3. Tabelas tb_*...")
# (código compacto)
tb_renda = [Row(cpf_cnpj=d["cpf_cnpj"], renda_mensal=d["renda_mensal"], faixa_renda=d["faixa_renda"], comprovada=d["renda_comprovada"]) for d in clientes_data]
spark.createDataFrame(tb_renda).write.mode("overwrite").saveAsTable(f"{CATALOG}.caracteristicas.tb_renda")
tb_saldo = [Row(cpf_cnpj=d["cpf_cnpj"], saldo_medio=d["saldo_medio"], saldo_atual=d["saldo_atual"], faixa_saldo=d["faixa_saldo"]) for d in clientes_data]
spark.createDataFrame(tb_saldo).write.mode("overwrite").saveAsTable(f"{CATALOG}.caracteristicas.tb_saldo_conta")
tb_score = [Row(cpf_cnpj=d["cpf_cnpj"], score=d["score"], faixa_score=d["faixa_score"]) for d in clientes_data]
spark.createDataFrame(tb_score).write.mode("overwrite").saveAsTable(f"{CATALOG}.caracteristicas.tb_score_credito")
tb_endividamento = [Row(cpf_cnpj=d["cpf_cnpj"], valor_endividamento=d["valor_endividamento"], comprometimento_renda_pct=d["comprometimento_renda_pct"], inadimplente=d["inadimplente"]) for d in clientes_data]
spark.createDataFrame(tb_endividamento).write.mode("overwrite").saveAsTable(f"{CATALOG}.caracteristicas.tb_endividamento")
tb_demografico = [Row(cpf_cnpj=d["cpf_cnpj"], idade=d["idade"], faixa_etaria=d["faixa_etaria"], genero=d["genero"], estado=d["estado"], cidade=d["cidade"], estado_civil=d["estado_civil"]) for d in clientes_data]
spark.createDataFrame(tb_demografico).write.mode("overwrite").saveAsTable(f"{CATALOG}.caracteristicas.tb_demografico")
tb_profissao = [Row(cpf_cnpj=d["cpf_cnpj"], profissao=d["profissao"], setor=d["setor"], tipo_vinculo=d["tipo_vinculo"]) for d in clientes_data]
spark.createDataFrame(tb_profissao).write.mode("overwrite").saveAsTable(f"{CATALOG}.caracteristicas.tb_profissao")
tb_escolaridade = [Row(cpf_cnpj=d["cpf_cnpj"], escolaridade=d["escolaridade"]) for d in clientes_data]
spark.createDataFrame(tb_escolaridade).write.mode("overwrite").saveAsTable(f"{CATALOG}.caracteristicas.tb_escolaridade")
tb_conta = [Row(cpf_cnpj=d["cpf_cnpj"], possui_conta=d["possui_conta"], tempo_conta_meses=d["tempo_conta_meses"], tipo_conta=d["tipo_conta"]) for d in clientes_data]
spark.createDataFrame(tb_conta).write.mode("overwrite").saveAsTable(f"{CATALOG}.caracteristicas.tb_conta_corrente")
tb_cartao = [Row(cpf_cnpj=d["cpf_cnpj"], possui_cartao=d["possui_cartao"], qtd_cartoes=d["qtd_cartoes"], limite_total=d["limite_total"], bandeira=d["bandeira"], fatura_media=d["fatura_media"]) for d in clientes_data]
spark.createDataFrame(tb_cartao).write.mode("overwrite").saveAsTable(f"{CATALOG}.caracteristicas.tb_cartao")
tb_invest = [Row(cpf_cnpj=d["cpf_cnpj"], possui_investimento=d["possui_investimento"], valor_investido=d["valor_investido"], perfil_investidor=d["perfil_investidor"]) for d in clientes_data]
spark.createDataFrame(tb_invest).write.mode("overwrite").saveAsTable(f"{CATALOG}.caracteristicas.tb_investimentos")
tb_seguros = [Row(cpf_cnpj=d["cpf_cnpj"], possui_seguro=d["possui_seguro"], tipos_seguro=d["tipos_seguro"]) for d in clientes_data]
spark.createDataFrame(tb_seguros).write.mode("overwrite").saveAsTable(f"{CATALOG}.caracteristicas.tb_seguros")
tb_credito = [Row(cpf_cnpj=d["cpf_cnpj"], possui_credito=d["possui_credito"], valor_credito_contratado=d["valor_credito_contratado"], tipo_credito=d["tipo_credito"]) for d in clientes_data]
spark.createDataFrame(tb_credito).write.mode("overwrite").saveAsTable(f"{CATALOG}.caracteristicas.tb_credito")
tb_transacional = [Row(cpf_cnpj=d["cpf_cnpj"], qtd_transacoes_mes=d["qtd_transacoes_mes"], ticket_medio=d["ticket_medio"], valor_movimentado_mes=d["valor_movimentado_mes"]) for d in clientes_data]
spark.createDataFrame(tb_transacional).write.mode("overwrite").saveAsTable(f"{CATALOG}.caracteristicas.tb_transacional")
tb_canais = [Row(cpf_cnpj=d["cpf_cnpj"], usa_app=d["usa_app"], usa_internet_banking=d["usa_internet_banking"], canal_preferido=d["canal_preferido"], frequencia_acesso=d["frequencia_acesso"]) for d in clientes_data]
spark.createDataFrame(tb_canais).write.mode("overwrite").saveAsTable(f"{CATALOG}.caracteristicas.tb_canais_digitais")
tb_engajamento = [Row(cpf_cnpj=d["cpf_cnpj"], nps=d["nps"], churn_score=d["churn_score"], engajamento_score=d["engajamento_score"]) for d in clientes_data]
spark.createDataFrame(tb_engajamento).write.mode("overwrite").saveAsTable(f"{CATALOG}.caracteristicas.tb_engajamento")
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

# 7. RBAC
print("7. RBAC...")
rbac_rows = [
    Row(usuario_id="admin", nome="Administrador", sistema="segmenthub", perfil="admin", ativo=True, concedido_por="bootstrap", concedido_em=datetime.now(), revogado_por=None, revogado_em=None),
    Row(usuario_id="admin", nome="Administrador", sistema="clientview360", perfil="admin", ativo=True, concedido_por="bootstrap", concedido_em=datetime.now(), revogado_por=None, revogado_em=None),
    Row(usuario_id="admin", nome="Administrador", sistema="engagement", perfil="admin", ativo=True, concedido_por="bootstrap", concedido_em=datetime.now(), revogado_por=None, revogado_em=None),
    Row(usuario_id="admin", nome="Administrador", sistema="analytics", perfil="admin", ativo=True, concedido_por="bootstrap", concedido_em=datetime.now(), revogado_por=None, revogado_em=None),
]
for i in range(1, 6):
    uid = f"gerente_{i:03d}"
    rbac_rows.append(Row(usuario_id=uid, nome=f"Gerente {i}", sistema="clientview360", perfil="gerente", ativo=True, concedido_por="bootstrap", concedido_em=datetime.now(), revogado_por=None, revogado_em=None))
spark.createDataFrame(rbac_rows).write.mode("overwrite").saveAsTable(f"{CATALOG}.governanca.usuarios_perfil")
print("  OK")

# COMMAND ----------

# 8. CATÁLOGOS (metadados)
print("8. Catálogos...")
# catalogo_caracteristicas
carac_rows = [
    Row(caracteristica_id="renda_mensal", tema="Financeiro", tema_ordem=1, tabela_fisica="caracteristicas.customer_features_wide", tabela_label="Renda Mensal", campo_fisico="renda_mensal", campo_label="Renda Mensal", tipo_dado="numeric", operadores=["=", ">", "<", "between"], valores_dominio=None, join_key="cpf_cnpj", sensibilidade="normal", usavel_em_peca=True, usavel_em_visao360=True, bloco_visao360="financeiro", ativo=True, descricao="Renda mensal do cliente"),
    Row(caracteristica_id="faixa_renda", tema="Financeiro", tema_ordem=2, tabela_fisica="caracteristicas.customer_features_wide", tabela_label="Faixa de Renda", campo_fisico="faixa_renda", campo_label="Faixa de Renda", tipo_dado="categorical", operadores=["="], valores_dominio=["baixa","media","alta"], join_key="cpf_cnpj", sensibilidade="normal", usavel_em_peca=True, usavel_em_visao360=True, bloco_visao360="financeiro", ativo=True, descricao="Faixa de renda"),
    Row(caracteristica_id="score", tema="Financeiro", tema_ordem=3, tabela_fisica="caracteristicas.customer_features_wide", tabela_label="Score de Crédito", campo_fisico="score", campo_label="Score", tipo_dado="numeric", operadores=["=", ">", "<"], valores_dominio=None, join_key="cpf_cnpj", sensibilidade="sensivel", usavel_em_peca=False, usavel_em_visao360=True, bloco_visao360="financeiro", ativo=True, descricao="Score de crédito"),
    Row(caracteristica_id="idade", tema="Demográfico", tema_ordem=1, tabela_fisica="caracteristicas.customer_features_wide", tabela_label="Idade", campo_fisico="idade", campo_label="Idade", tipo_dado="numeric", operadores=["=", ">", "<", "between"], valores_dominio=None, join_key="cpf_cnpj", sensibilidade="normal", usavel_em_peca=True, usavel_em_visao360=True, bloco_visao360="cadastral", ativo=True, descricao="Idade do cliente"),
    Row(caracteristica_id="faixa_etaria", tema="Demográfico", tema_ordem=2, tabela_fisica="caracteristicas.customer_features_wide", tabela_label="Faixa Etária", campo_fisico="faixa_etaria", campo_label="Faixa Etária", tipo_dado="categorical", operadores=["="], valores_dominio=["18-25","26-35","36-50","51-65","65+"], join_key="cpf_cnpj", sensibilidade="normal", usavel_em_peca=True, usavel_em_visao360=True, bloco_visao360="cadastral", ativo=True, descricao="Faixa etária"),
    Row(caracteristica_id="estado", tema="Demográfico", tema_ordem=3, tabela_fisica="caracteristicas.customer_features_wide", tabela_label="Estado", campo_fisico="estado", campo_label="Estado", tipo_dado="categorical", operadores=["="], valores_dominio=None, join_key="cpf_cnpj", sensibilidade="normal", usavel_em_peca=False, usavel_em_visao360=True, bloco_visao360="cadastral", ativo=True, descricao="UF"),
    Row(caracteristica_id="possui_cartao", tema="Produtos", tema_ordem=1, tabela_fisica="caracteristicas.customer_features_wide", tabela_label="Possui Cartão", campo_fisico="possui_cartao", campo_label="Possui Cartão", tipo_dado="boolean", operadores=["="], valores_dominio=None, join_key="cpf_cnpj", sensibilidade="normal", usavel_em_peca=True, usavel_em_visao360=True, bloco_visao360="produtos", ativo=True, descricao="Cliente possui cartão de crédito"),
    Row(caracteristica_id="qtd_cartoes", tema="Produtos", tema_ordem=2, tabela_fisica="caracteristicas.customer_features_wide", tabela_label="Qtd Cartões", campo_fisico="qtd_cartoes", campo_label="Quantidade de Cartões", tipo_dado="numeric", operadores=["=", ">", "<"], valores_dominio=None, join_key="cpf_cnpj", sensibilidade="normal", usavel_em_peca=False, usavel_em_visao360=True, bloco_visao360="produtos", ativo=True, descricao="Número de cartões"),
    Row(caracteristica_id="engajamento_score", tema="Comportamento", tema_ordem=1, tabela_fisica="caracteristicas.customer_features_wide", tabela_label="Engajamento", campo_fisico="engajamento_score", campo_label="Score de Engajamento", tipo_dado="numeric", operadores=["=", ">", "<"], valores_dominio=None, join_key="cpf_cnpj", sensibilidade="normal", usavel_em_peca=True, usavel_em_visao360=True, bloco_visao360="comportamento", ativo=True, descricao="Score de engajamento digital"),
]
spark.createDataFrame(carac_rows).write.mode("overwrite").saveAsTable(f"{CATALOG}.metadata.catalogo_caracteristicas")

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
spark.createDataFrame(canais_rows).write.mode("overwrite").saveAsTable(f"{CATALOG}.engagement.catalogo_canais")
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
spark.createDataFrame(metricas_rows).write.mode("overwrite").saveAsTable(f"{CATALOG}.config.catalogo_metricas")

# config.regras_priorizacao
prior_rows = [
    Row(fator_id="potencial_renda", nome_exibicao="Potencial de Renda", descricao="Clientes com maior renda", peso=30, condicao_sql="renda_mensal > 15000", mensagem_insight="Cliente com alta renda", ativo=True, atualizado_por="admin", atualizado_em=datetime.now()),
    Row(fator_id="engajamento", nome_exibicao="Engajamento Digital", descricao="Clientes com alto engajamento", peso=25, condicao_sql="engajamento_score > 70", mensagem_insight="Cliente engajado digitalmente", ativo=True, atualizado_por="admin", atualizado_em=datetime.now()),
    Row(fator_id="churn_risk", nome_exibicao="Risco de Churn", descricao="Clientes com risco de saída", peso=20, condicao_sql="churn_score > 60", mensagem_insight="Cliente em risco", ativo=True, atualizado_por="admin", atualizado_em=datetime.now()),
    Row(fator_id="inadimplencia", nome_exibicao="Inadimplência", descricao="Clientes inadimplentes", peso=-10, condicao_sql="inadimplente = true", mensagem_insight="Cliente inadimplente", ativo=True, atualizado_por="admin", atualizado_em=datetime.now()),
]
spark.createDataFrame(prior_rows).write.mode("overwrite").saveAsTable(f"{CATALOG}.config.regras_priorizacao")

# config.visao360_blocos
blocos_rows = [
    Row(bloco_id="cadastral", nome="Dados Cadastrais", icone="person", ordem=1, visivel=True, tipo="fixo", atualizado_por="admin", atualizado_em=datetime.now()),
    Row(bloco_id="financeiro", nome="Financeiro", icone="account_balance", ordem=2, visivel=True, tipo="fixo", atualizado_por="admin", atualizado_em=datetime.now()),
    Row(bloco_id="produtos", nome="Produtos", icone="shopping_bag", ordem=3, visivel=True, tipo="fixo", atualizado_por="admin", atualizado_em=datetime.now()),
    Row(bloco_id="comportamento", nome="Comportamento", icone="trending_up", ordem=4, visivel=True, tipo="customizavel", atualizado_por="admin", atualizado_em=datetime.now()),
]
spark.createDataFrame(blocos_rows).write.mode("overwrite").saveAsTable(f"{CATALOG}.config.visao360_blocos")

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
spark.createDataFrame(campos_rows).write.mode("overwrite").saveAsTable(f"{CATALOG}.config.visao360_campos")

# config.visao360_contexto_segmentacao
contexto_rows = [
    Row(campo_seg="objetivo_negocio", visivel=True, ordem=1, label_override="Objetivo de Negócio", atualizado_por="admin", atualizado_em=datetime.now()),
    Row(campo_seg="publico_alvo_descricao", visivel=True, ordem=2, label_override="Público-Alvo", atualizado_por="admin", atualizado_em=datetime.now()),
    Row(campo_seg="seg_tags", visivel=False, ordem=3, label_override=None, atualizado_por="admin", atualizado_em=datetime.now()),
]
spark.createDataFrame(contexto_rows).write.mode("overwrite").saveAsTable(f"{CATALOG}.config.visao360_contexto_segmentacao")

# engagement.config_janela_envio
janela_rows = [
    Row(config_id="janela_email", canal="email", hora_inicio=8, hora_fim=22, dias_semana=["mon","tue","wed","thu","fri"], timezone="America/Sao_Paulo", ativo=True, atualizado_por="admin", atualizado_em=datetime.now()),
    Row(config_id="janela_whatsapp", canal="whatsapp", hora_inicio=9, hora_fim=21, dias_semana=["mon","tue","wed","thu","fri","sat"], timezone="America/Sao_Paulo", ativo=True, atualizado_por="admin", atualizado_em=datetime.now()),
    Row(config_id="janela_push", canal="push", hora_inicio=7, hora_fim=23, dias_semana=["mon","tue","wed","thu","fri","sat","sun"], timezone="America/Sao_Paulo", ativo=True, atualizado_por="admin", atualizado_em=datetime.now()),
]
spark.createDataFrame(janela_rows).write.mode("overwrite").saveAsTable(f"{CATALOG}.engagement.config_janela_envio")

# engagement.config_retry
retry_rows = [
    Row(config_id="retry_email", canal="email", max_tentativas=3, backoff_minutos=[1,5,30], ativo=True, atualizado_por="admin", atualizado_em=datetime.now()),
    Row(config_id="retry_whatsapp", canal="whatsapp", max_tentativas=2, backoff_minutos=[5,30], ativo=True, atualizado_por="admin", atualizado_em=datetime.now()),
    Row(config_id="retry_push", canal="push", max_tentativas=3, backoff_minutos=[1,10,60], ativo=True, atualizado_por="admin", atualizado_em=datetime.now()),
]
spark.createDataFrame(retry_rows).write.mode("overwrite").saveAsTable(f"{CATALOG}.engagement.config_retry")

# engagement.config_conversao
conv_rows = [
    Row(config_id="conv_global", escopo="global", evento_conversao="converteu", janela_dias=30, ativo=True, atualizado_por="admin", atualizado_em=datetime.now()),
    Row(config_id="conv_campanha_default", escopo="por_campanha", evento_conversao="clicou", janela_dias=14, ativo=True, atualizado_por="admin", atualizado_em=datetime.now()),
]
spark.createDataFrame(conv_rows).write.mode("overwrite").saveAsTable(f"{CATALOG}.engagement.config_conversao")

# engagement.config_otimizacao
otim_rows = [
    Row(config_id="mab_global", escopo="global", metrica_alvo="conversao", metrica_custom_json=None, janela_avaliacao_horas=72, trafego_minimo_pct=10, min_amostras_por_variante=100, frequencia_recalculo="diario", otimizacao_ativa=True, ativo=True, atualizado_por="admin", atualizado_em=datetime.now()),
    Row(config_id="mab_jornada_default", escopo="por_jornada", metrica_alvo="clique", metrica_custom_json=None, janela_avaliacao_horas=48, trafego_minimo_pct=20, min_amostras_por_variante=200, frequencia_recalculo="diario", otimizacao_ativa=True, ativo=True, atualizado_por="admin", atualizado_em=datetime.now()),
]
spark.createDataFrame(otim_rows).write.mode("overwrite").saveAsTable(f"{CATALOG}.engagement.config_otimizacao")

# engagement.config_jornada_politica
politica_rows = [
    Row(politica_id="politica_global", escopo="global", ao_sair_segmento="continua", ao_pausar_campanha="termina_quem_entrou", cap_estourado="pula", reentrada="permitida", reentrada_dias=30, ao_editar_ativa="versao_congelada", permite_loop=True, loop_max_iteracoes_teto=3, loop_max_dias_teto=15, ativo=True, atualizado_por="admin", atualizado_em=datetime.now()),
]
spark.createDataFrame(politica_rows).write.mode("overwrite").saveAsTable(f"{CATALOG}.engagement.config_jornada_politica")

print("  OK")

# COMMAND ----------

# 10. DADOS DE CAMPANHA, JORNADA, PEÇA (mais completos)
print("10. Campanhas, Jornadas, Peças...")
# Campanha
campanha_id = "camp_001"
camp_rows = [
    Row(campanha_id=campanha_id, campanha_codigo="CAM-2025-CROSSSELL-00001", nome="Campanha Cross-Sell Q3", descricao="Oferta de produtos financeiros", objetivo="RENTABILIZACAO", tags=["cross-sell","q3"], resumo="Oferta de produtos financeiros", objetivo_negocio="Aumentar rentabilidade", observacoes="Usar segmentos de alta renda", owner="marketing", area_responsavel="Marketing", email_contato="marketing@banco.com", criado_por="admin", status="ativa", vigencia_inicio=datetime.now(), vigencia_fim=datetime.now()+timedelta(days=90), limite_envios=100000, alerta_pct_limite=80, envios_realizados=0, versao_atual=1, atualizado_em=datetime.now())
]
spark.createDataFrame(camp_rows).write.mode("overwrite").saveAsTable(f"{CATALOG}.engagement.campanha")

# Jornada (vinculada à campanha)
jornada_id = "jorn_001"
jorn_rows = [
    Row(jornada_id=jornada_id, jornada_codigo="JOR-2025-00001", campanha_id=campanha_id, nome="Jornada Cross-Sell", descricao="Fluxo de oferta com 3 etapas", grafo_json='{"nodes":[{"id":"n1","type":"start","data":{"label":"Início"}},{"id":"n2","type":"email","data":{"label":"Envio Email"}},{"id":"n3","type":"wait","data":{"label":"Aguardar"}},{"id":"n4","type":"end","data":{"label":"Fim"}}],"edges":[{"source":"n1","target":"n2"},{"source":"n2","target":"n3"},{"source":"n3","target":"n4"}]}', seg_entrada_id=None, resumo="Jornada cross-sell", objetivo_negocio="Rentabilização", observacoes="Usar segmentos de alta renda", status="ativa", ao_sair_segmento="continua", ao_pausar_campanha="termina_quem_entrou", cap_estourado="pula", aprovado_por="admin", criado_por="admin", owner="marketing", versao_atual=1, atualizado_em=datetime.now())
]
spark.createDataFrame(jorn_rows).write.mode("overwrite").saveAsTable(f"{CATALOG}.engagement.jornada")

# Relação campanha_jornada
camp_jorn_rows = [
    Row(campanha_id=campanha_id, jornada_id=jornada_id, ordem=1, ativo=True)
]
spark.createDataFrame(camp_jorn_rows).write.mode("overwrite").saveAsTable(f"{CATALOG}.engagement.campanha_jornada")

# Peça
peca_id = "peca_001"
peca_rows = [
    Row(peca_id=peca_id, peca_codigo="PEC-2025-EMAIL-00001", nome="Oferta Cross-Sell Email", descricao="Email com oferta de cartão e investimentos", canal="email", tags=["cross-sell","email"], conteudo_json='{"html":"<p>Olá {{nome}}, aproveite nossa oferta exclusiva!</p><p>Renda: {{renda_mensal}}</p>"}', html_renderizado="<p>Olá [nome], aproveite nossa oferta exclusiva!</p><p>Renda: [renda_mensal]</p>", assunto="Aproveite a oferta exclusiva", variaveis_usadas=["renda_mensal","possui_cartao"], status_aprovacao="aprovada", aprovado_por="admin", criado_por="admin", owner="marketing", area_responsavel="Marketing", versao_atual=1, atualizado_em=datetime.now())
]
spark.createDataFrame(peca_rows).write.mode("overwrite").saveAsTable(f"{CATALOG}.engagement.peca")

print("  OK")

# COMMAND ----------

# 11. DADOS INICIAIS DE SEGMENTAÇÃO (S1)
print("11. Segmentação (S1)...")
# Criar 2 segmentos: "Alta Renda" e "Digital"
seg_ids = ["seg_alta_renda", "seg_digital"]

# Definir regras JSON (exemplo)
regras_alta_renda = '{"operator":"AND","conditions":[{"campo_id":"renda_mensal","operator":">","value":10000},{"campo_id":"segmento","operator":"=","value":"varejo"}]}'
regras_digital = '{"operator":"AND","conditions":[{"campo_id":"usa_app","operator":"=","value":true},{"campo_id":"engajamento_score","operator":">","value":60}]}'

# Inserir definições
seg_def_rows = [
    Row(seg_id=seg_ids[0], seg_codigo="SEG-ALTA-RENDA", seg_slug="alta-renda", nome="Alta Renda Varejo", descricao="Clientes varejo com renda > 10k", objetivo="AQUISICAO", seg_tags=["varejo","alta-renda"], resumo="Público de alta renda do varejo", objetivo_negocio="Aumentar cross-sell", publico_alvo_descricao="Clientes varejo com alta renda", observacoes=None, documentacao_md="# Alta Renda\nSegmento para ofertas de produtos premium.", owner="admin", area_responsavel="Marketing", email_contato="marketing@banco.com", criado_por="admin", criado_em=datetime.now(), seg_origem_id=None, tipo_origem="nova", tipo="direta", publico_base_id="pub_varejo", regras_json=regras_alta_renda, status="ativa", vigencia_inicio=datetime.now(), vigencia_fim=datetime.now()+timedelta(days=90), agendamento_cron=None, recorrencia="once", aprovado_por="admin", aprovado_em=datetime.now(), checklist_validacao_json=None, versao_atual=1, atualizado_em=datetime.now(), habilitado=True),
    Row(seg_id=seg_ids[1], seg_codigo="SEG-DIGITAL", seg_slug="digital", nome="Clientes Digitais", descricao="Clientes que usam app e têm alto engajamento", objetivo="ENGAJAMENTO", seg_tags=["digital","app"], resumo="Público digital engajado", objetivo_negocio="Aumentar uso digital", publico_alvo_descricao="Clientes com alta interação digital", observacoes=None, documentacao_md="# Digital\nSegmento para ofertas digitais.", owner="admin", area_responsavel="Digital", email_contato="digital@banco.com", criado_por="admin", criado_em=datetime.now(), seg_origem_id=None, tipo_origem="nova", tipo="direta", publico_base_id=None, regras_json=regras_digital, status="ativa", vigencia_inicio=datetime.now(), vigencia_fim=datetime.now()+timedelta(days=90), agendamento_cron=None, recorrencia="once", aprovado_por="admin", aprovado_em=datetime.now(), checklist_validacao_json=None, versao_atual=1, atualizado_em=datetime.now(), habilitado=True),
]
spark.createDataFrame(seg_def_rows).write.mode("overwrite").saveAsTable(f"{CATALOG}.segmentacao.seg_definicao")

# Destino (seg_destino)
seg_dest_rows = [
    Row(seg_id=seg_ids[0], destino="sistema2", habilitado=True, criado_em=datetime.now()),
    Row(seg_id=seg_ids[0], destino="sistema3", habilitado=True, criado_em=datetime.now()),
    Row(seg_id=seg_ids[1], destino="sistema2", habilitado=True, criado_em=datetime.now()),
    Row(seg_id=seg_ids[1], destino="sistema3", habilitado=True, criado_em=datetime.now()),
]
spark.createDataFrame(seg_dest_rows).write.mode("overwrite").saveAsTable(f"{CATALOG}.segmentacao.seg_destino")

# Execução (simulada) - para cada segmento, gerar resultado corrente
print("  Gerando seg_execucao e seg_resultado_corrente...")
exec_id1 = f"exec_{seg_ids[0]}_{datetime.now().strftime('%Y%m%d_%H%M')}"
exec_id2 = f"exec_{seg_ids[1]}_{datetime.now().strftime('%Y%m%d_%H%M')}"

# Simular execução: para cada segmento, selecionar CPFs que atendem às regras
# Vamos fazer uma consulta simples no Spark, mas para simplificar, usamos a lógica manual baseada nos dados gerados.
# Como temos os dados em clientes_data, podemos filtrar.
# Para "Alta Renda": segmento varejo e renda > 10000
alta_renda_cpfs = [d["cpf_cnpj"] for d in clientes_data if d["segmento"] == "varejo" and d["renda_mensal"] > 10000]
digital_cpfs = [d["cpf_cnpj"] for d in clientes_data if d["usa_app"] and d["engajamento_score"] > 60]

# Inserir execuções
exec_rows = [
    Row(exec_id=exec_id1, seg_id=seg_ids[0], versao_usada=1, origem_execucao="manual", executado_em=datetime.now(), qtd_clientes=len(alta_renda_cpfs), status="sucesso", job_id=None, run_id=None, job_run_url=None),
    Row(exec_id=exec_id2, seg_id=seg_ids[1], versao_usada=1, origem_execucao="manual", executado_em=datetime.now(), qtd_clientes=len(digital_cpfs), status="sucesso", job_id=None, run_id=None, job_run_url=None),
]
spark.createDataFrame(exec_rows).write.mode("overwrite").saveAsTable(f"{CATALOG}.segmentacao.seg_execucao")

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

# Atualizar o seg_entrada_id da jornada para o primeiro segmento (para testar S3)
spark.sql(f"UPDATE {CATALOG}.engagement.jornada SET seg_entrada_id = '{seg_ids[0]}' WHERE jornada_id = 'jorn_001'")

print("  OK")

# COMMAND ----------

print("\n🎉 SEED 100% CONCLUÍDO COM SUCESSO!")
print(f"Foram gerados {NUM_CLIENTES} clientes.")
print("Todas as tabelas necessárias para a POC estão populadas.")
print("Agora você pode iniciar a implementação dos cartões ou testar os endpoints.")