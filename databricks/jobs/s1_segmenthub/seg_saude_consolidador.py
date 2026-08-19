# Databricks notebook source
"""
===============================================================================
S1-INFRA-01: seg_saude_consolidador — Consolidação de Saúde
===============================================================================

Job de infraestrutura que roda periodicamente (a cada 6h) para:
1. Detectar segmentações ativas que NÃO executaram no prazo esperado
2. Marcar health_status como 'vermelho' para segs com execução atrasada
3. Gerar notificações automáticas para owners de segs problemáticas
4. Recalcular health de segmentações cujo job falhou (status ficou 'rodando')

Este job NÃO recalcula o resultado das segmentações. Apenas verifica
se os jobs individuais estão cumprindo o schedule.

Tabelas envolvidas:
  - plataforma.segmentacao.seg_definicao (leitura)
  - plataforma.segmentacao.seg_execucao (leitura)
  - plataforma.segmentacao.seg_saude (escrita — UPDATE)
  - plataforma.segmentacao.seg_notificacao (escrita — INSERT)

Autor: SegmentHub Platform
Versão: 2.0
===============================================================================
"""

# COMMAND ----------

# DBTITLE 1,Setup
import json
from datetime import datetime, timezone

CATALOG = "plataforma"
SCHEMA_SEG = "segmentacao"

print(f"▶ Consolidação de saúde iniciada: {datetime.now(timezone.utc).isoformat()}")

# COMMAND ----------

# DBTITLE 1,Step 1: Identificar segmentações ativas
# ============================================================
# STEP 1: Detectar TODOS os problemas em Spark SQL puro (RF-06)
# ============================================================
# Substitui o antigo .collect() loop Python por uma única query.
# Escala para 100K+ segmentações sem OOM no driver.
# Retorna APENAS segs com problemas (não todas as ativas).
# ============================================================

# 1a. Contagem total para log
total_ativas = spark.sql(f"""
  SELECT COUNT(*) AS n FROM {CATALOG}.{SCHEMA_SEG}.seg_definicao
  WHERE status = 'ativa' AND habilitado = true
""").collect()[0]["n"]

print(f"✓ {total_ativas} segmentações ativas verificadas")

# 1b. Query unificada: detecta atrasos diários, semanais, e nunca-executou
df_problematicas = spark.sql(f"""
  SELECT
    d.seg_id,
    d.nome,
    d.owner,
    d.email_contato,
    COALESCE(d.recorrencia, 'diario') AS recorrencia,
    e.ultimo_sucesso,
    s.ultima_verificacao,
    CASE
      WHEN e.ultimo_sucesso IS NULL
           AND (s.ultima_verificacao IS NULL
                OR s.ultima_verificacao < current_timestamp() - INTERVAL 3 DAYS)
        THEN 'Nunca executou com sucesso'
      WHEN COALESCE(d.recorrencia, 'diario') = 'diario'
           AND e.ultimo_sucesso < current_timestamp() - INTERVAL 26 HOURS
        THEN CONCAT('Atraso de ',
             CAST(FLOOR((unix_timestamp(current_timestamp()) - unix_timestamp(e.ultimo_sucesso)) / 3600) AS INT),
             'h (esperado: diário)')
      WHEN COALESCE(d.recorrencia, 'diario') = 'semanal'
           AND e.ultimo_sucesso < current_timestamp() - INTERVAL 8 DAYS
        THEN CONCAT('Atraso de ',
             CAST(DATEDIFF(current_timestamp(), e.ultimo_sucesso) AS INT),
             ' dias (esperado: semanal)')
    END AS problema
  FROM {CATALOG}.{SCHEMA_SEG}.seg_definicao d
  LEFT JOIN (
    SELECT seg_id,
           MAX(CASE WHEN status = 'sucesso' THEN executado_em END) AS ultimo_sucesso
    FROM {CATALOG}.{SCHEMA_SEG}.seg_execucao
    GROUP BY seg_id
  ) e ON d.seg_id = e.seg_id
  LEFT JOIN {CATALOG}.{SCHEMA_SEG}.seg_saude s ON d.seg_id = s.seg_id
  WHERE d.status = 'ativa'
    AND d.habilitado = true
  HAVING problema IS NOT NULL
""")

print(f"✓ {df_problematicas.count()} segmentações com problemas detectadas")

# COMMAND ----------

# DBTITLE 1,Step 2: Detectar travadas + montar arrays
# ============================================================
# STEP 2: Detectar travadas + montar arrays de problemas (RF-06)
# ============================================================
# O .collect() agora roda APENAS sobre segs problemáticas (dezenas),
# não sobre TODAS as ativas (milhares). Escalabilidade garantida.
# ============================================================

# 2a. Detectar execuções travadas (>2h em 'rodando' ou 'em_execucao')
df_travadas = spark.sql(f"""
  SELECT seg_id, exec_id
  FROM {CATALOG}.{SCHEMA_SEG}.seg_execucao
  WHERE status IN ('rodando', 'em_execucao')
    AND executado_em < current_timestamp() - INTERVAL 2 HOURS
""")

travadas_count = df_travadas.count()
if travadas_count > 0:
    # Marca todas como falha_timeout em bulk
    df_travadas.createOrReplaceTempView("travadas_batch")
    spark.sql(f"""
      MERGE INTO {CATALOG}.{SCHEMA_SEG}.seg_execucao AS target
      USING travadas_batch AS source
      ON target.exec_id = source.exec_id
      WHEN MATCHED THEN UPDATE SET status = 'falha_timeout'
    """)
    print(f"⚠️ {travadas_count} execuções travadas → falha_timeout")
else:
    print("✓ Nenhuma execução travada")

# 2b. Monta saude_updates e alertas_gerados a partir do resultado SQL
# Apenas segs problemáticas (tipicamente <5% do total) são coletadas
alertas_gerados = []
saude_updates = []

for row in df_problematicas.collect():
    problemas = [row["problema"]]
    saude_updates.append({
        "seg_id": row["seg_id"],
        "health_status": "vermelho",
        "alertas_json": json.dumps(problemas),
    })
    alertas_gerados.append({
        "seg_id": row["seg_id"],
        "nome": row["nome"],
        "owner": row["owner"] or "",
        "email_contato": row["email_contato"] or "",
        "problemas": problemas,
    })

# 2c. Adiciona segs travadas que não estão já no array
if travadas_count > 0:
    segs_ja = set(u["seg_id"] for u in saude_updates)
    for row in df_travadas.select("seg_id").distinct().collect():
        if row["seg_id"] not in segs_ja:
            problema_trav = ["Execução travada (timeout > 2h)"]
            saude_updates.append({
                "seg_id": row["seg_id"],
                "health_status": "vermelho",
                "alertas_json": json.dumps(problema_trav),
            })
            alertas_gerados.append({
                "seg_id": row["seg_id"],
                "nome": "(timeout detectado)",
                "owner": "",
                "email_contato": "",
                "problemas": problema_trav,
            })

print(f"✓ Total alertas: {len(alertas_gerados)} | Saude updates: {len(saude_updates)}")

# COMMAND ----------

# DBTITLE 1,Step 3: (RF-06 — movido para Steps 1+2)
# ============================================================
# STEP 3: (RF-06) Lógica de detecção movida para Steps 1+2
# ============================================================
# Antes: .collect() de TODAS as segs ativas (1000+) → loop Python.
# Agora: Query SQL pura (Step 1) retorna só problemáticas (dezenas).
#        Step 2 faz .collect() apenas das problemáticas + marca travadas.
# Este cell mantido como no-op para preservar numeração de cells.
# ============================================================
print(f"✓ Steps 1+2 completados. Prosseguindo para MERGE bulk (Step 4).")

# COMMAND ----------

# DBTITLE 1,Step 4: Atualizar seg_saude (MERGE bulk)
# ============================================================
# STEP 4: Atualizar seg_saude (MERGE bulk — RF-03)
# ============================================================
# Substitui loop de N MERGEs por 1 único MERGE via DataFrame.
# Performance: N queries → 1 query, N commits Delta → 1 commit.
# ============================================================

if saude_updates:
    from pyspark.sql.types import StructType, StructField, StringType

    # RF-07: escape aspas simples no alertas_json antes de persistir
    for u in saude_updates:
        u["alertas_json"] = u["alertas_json"].replace("'", "''")

    schema = StructType([
        StructField("seg_id", StringType(), False),
        StructField("health_status", StringType(), False),
        StructField("alertas_json", StringType(), True),
    ])
    df_saude_batch = spark.createDataFrame(saude_updates, schema=schema)
    df_saude_batch.createOrReplaceTempView("saude_batch")

    spark.sql(f"""
      MERGE INTO {CATALOG}.{SCHEMA_SEG}.seg_saude AS target
      USING saude_batch AS source
      ON target.seg_id = source.seg_id
      WHEN MATCHED THEN UPDATE SET
        health_status = source.health_status,
        ultima_verificacao = current_timestamp(),
        alertas_json = source.alertas_json
      WHEN NOT MATCHED THEN INSERT
        (seg_id, health_status, ultima_verificacao, alertas_json, publico_atual)
      VALUES
        (source.seg_id, source.health_status, current_timestamp(),
         source.alertas_json, 0)
    """)

print(f"✓ seg_saude atualizada para {len(saude_updates)} segmentações (1 MERGE bulk)")

# COMMAND ----------

# DBTITLE 1,Step 5: Gerar notificações para owners
# ============================================================
# STEP 5: Gerar notificações para owners
# ============================================================

for alerta in alertas_gerados:
    titulo = f"⚠️ Saúde crítica: {alerta['nome']}".replace("'", "''")
    mensagem = f"Problemas detectados: {'; '.join(alerta['problemas'])}".replace("'", "''")
    import uuid as _uuid
    notif_id = f"notif_saude_{_uuid.uuid4().hex[:12]}"
    owner_safe = alerta['owner'].replace("'", "''") if alerta.get('owner') else 'system'

    spark.sql(f"""
      INSERT INTO {CATALOG}.{SCHEMA_SEG}.seg_notificacao
      (notif_id, destinatario, tipo, seg_id, titulo, mensagem, lida, criado_em)
      VALUES (
        '{notif_id}',
        '{owner_safe}',
        'alerta_saude',
        '{alerta['seg_id']}',
        '{titulo}',
        '{mensagem}',
        false,
        current_timestamp()
      )
    """)

print(f"✓ {len(alertas_gerados)} notificações geradas")

# COMMAND ----------

# DBTITLE 1,Step 6: (movido para Step 2)
# ============================================================
# STEP 6: (RF-04/RF-06) Detecção de travadas integrada no Step 2
# ============================================================
# Travadas são detectadas e marcadas como falha_timeout em bulk
# (MERGE) no Step 2, junto com a montagem dos arrays.
print(f"✓ Travadas processadas no Step 2: {travadas_count}")

# COMMAND ----------

# DBTITLE 1,Resumo
# ============================================================
# RESUMO
# ============================================================

result = {
    "status": "sucesso",
    "segmentacoes_verificadas": total_ativas,
    "alertas_gerados": len(alertas_gerados),
    "saude_atualizada": len(saude_updates),
    "execucoes_travadas": travadas_count,
}

print(f"\n{'='*60}")
print(f"✅ CONSOLIDAÇÃO CONCLUÍDA")
print(f"   Verificadas:  {result['segmentacoes_verificadas']}")
print(f"   Alertas:      {result['alertas_gerados']}")
print(f"   Travadas:     {result['execucoes_travadas']}")
print(f"{'='*60}")

dbutils.notebook.exit(json.dumps(result))
