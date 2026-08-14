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

import json
from datetime import datetime, timezone, timedelta
from pyspark.sql import functions as F

CATALOG = "plataforma"
SCHEMA_SEG = "segmentacao"

print(f"▶ Consolidação de saúde iniciada: {datetime.now(timezone.utc).isoformat()}")

# COMMAND ----------

# ============================================================
# STEP 1: Identificar segmentações ativas com execução atrasada
# ============================================================

# Busca segmentações ativas com agendamento
df_ativas = spark.sql(f"""
  SELECT d.seg_id, d.nome, d.agendamento_cron, d.recorrencia,
         d.owner, d.email_contato, d.area_responsavel,
         s.ultima_verificacao, s.health_status AS health_atual
  FROM {CATALOG}.{SCHEMA_SEG}.seg_definicao d
  LEFT JOIN {CATALOG}.{SCHEMA_SEG}.seg_saude s ON d.seg_id = s.seg_id
  WHERE d.status = 'ativa'
    AND d.habilitado = true
""")

print(f"✓ {df_ativas.count()} segmentações ativas encontradas")

# COMMAND ----------

# ============================================================
# STEP 2: Verificar última execução de cada segmentação
# ============================================================

# Última execução com sucesso de cada seg
df_ultima_exec = spark.sql(f"""
  SELECT seg_id,
         MAX(executado_em) AS ultima_execucao,
         MAX(CASE WHEN status = 'sucesso' THEN executado_em END) AS ultimo_sucesso
  FROM {CATALOG}.{SCHEMA_SEG}.seg_execucao
  GROUP BY seg_id
""")

# Join com ativas
df_check = df_ativas.join(df_ultima_exec, "seg_id", "left")

# COMMAND ----------

# ============================================================
# STEP 3: Detectar atrasos e falhas
# ============================================================

agora = datetime.now(timezone.utc)
limite_diario = agora - timedelta(hours=26)      # tolerancia: 26h para diario
limite_semanal = agora - timedelta(days=8)        # tolerancia: 8 dias para semanal
limite_sem_exec = agora - timedelta(days=3)       # 3 dias sem nenhuma exec = problema

alertas_gerados = []
saude_updates = []

for row in df_check.collect():
    seg_id = row["seg_id"]
    ultimo_sucesso = row["ultimo_sucesso"]
    recorrencia = row["recorrencia"] or "diario"
    problemas = []

    # Sem nenhuma execução?
    if ultimo_sucesso is None:
        if row["ultima_verificacao"] and row["ultima_verificacao"] < limite_sem_exec:
            problemas.append("Nunca executou com sucesso")
    else:
        # Verifica atraso baseado na recorrência
        if recorrencia == "diario" and ultimo_sucesso < limite_diario:
            horas_atraso = int((agora - ultimo_sucesso).total_seconds() / 3600)
            problemas.append(f"Atraso de {horas_atraso}h (esperado: diário)")
        elif recorrencia == "semanal" and ultimo_sucesso < limite_semanal:
            dias_atraso = (agora - ultimo_sucesso).days
            problemas.append(f"Atraso de {dias_atraso} dias (esperado: semanal)")

    # Determina novo health
    if problemas:
        novo_health = "vermelho"
        alertas_gerados.append({
            "seg_id": seg_id,
            "nome": row["nome"],
            "owner": row["owner"],
            "email_contato": row["email_contato"],
            "problemas": problemas,
        })
        saude_updates.append({
            "seg_id": seg_id,
            "health_status": novo_health,
            "alertas_json": json.dumps(problemas),
        })

print(f"✓ Alertas gerados: {len(alertas_gerados)}")

# COMMAND ----------

# ============================================================
# STEP 4: Atualizar seg_saude para os problemáticos
# ============================================================

for update in saude_updates:
    spark.sql(f"""
      MERGE INTO {CATALOG}.{SCHEMA_SEG}.seg_saude AS target
      USING (SELECT '{update['seg_id']}' AS seg_id) AS source
      ON target.seg_id = source.seg_id
      WHEN MATCHED THEN UPDATE SET
        health_status = '{update['health_status']}',
        ultima_verificacao = current_timestamp(),
        alertas_json = '{update['alertas_json']}'
      WHEN NOT MATCHED THEN INSERT
        (seg_id, health_status, ultima_verificacao, alertas_json, publico_atual)
      VALUES
        ('{update['seg_id']}', '{update['health_status']}', current_timestamp(),
         '{update['alertas_json']}', 0)
    """)

print(f"✓ seg_saude atualizada para {len(saude_updates)} segmentações")

# COMMAND ----------

# ============================================================
# STEP 5: Gerar notificações para owners
# ============================================================

for alerta in alertas_gerados:
    titulo = f"⚠️ Saúde crítica: {alerta['nome']}"
    mensagem = f"Problemas detectados: {'; '.join(alerta['problemas'])}"

    spark.sql(f"""
      INSERT INTO {CATALOG}.{SCHEMA_SEG}.seg_notificacao
      (notif_id, destinatario, tipo, seg_id, titulo, mensagem, lida, criado_em)
      VALUES (
        '{f"notif_saude_{alerta['seg_id']}_{datetime.now().strftime('%Y%m%d%H%M')}"  }',
        '{alerta['owner']}',
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

# ============================================================
# STEP 6: Detectar execuções 'travadas' (status 'rodando' > 2h)
# ============================================================

df_travadas = spark.sql(f"""
  SELECT seg_id, exec_id, executado_em
  FROM {CATALOG}.{SCHEMA_SEG}.seg_execucao
  WHERE status = 'rodando'
    AND executado_em < current_timestamp() - INTERVAL 2 HOURS
""")

if df_travadas.count() > 0:
    print(f"\n⚠️ {df_travadas.count()} execuções travadas detectadas")
    # Marca como 'falha_timeout'
    travadas_ids = [row["exec_id"] for row in df_travadas.collect()]
    for eid in travadas_ids:
        spark.sql(f"""
          UPDATE {CATALOG}.{SCHEMA_SEG}.seg_execucao
          SET status = 'falha_timeout'
          WHERE exec_id = '{eid}'
        """)
    print(f"✓ Marcadas como 'falha_timeout'")
else:
    print("✓ Nenhuma execução travada")

# COMMAND ----------

# ============================================================
# RESUMO
# ============================================================

result = {
    "status": "sucesso",
    "segmentacoes_verificadas": df_ativas.count(),
    "alertas_gerados": len(alertas_gerados),
    "saude_atualizada": len(saude_updates),
    "execucoes_travadas": df_travadas.count() if df_travadas else 0,
}

print(f"\n{'='*60}")
print(f"✅ CONSOLIDAÇÃO CONCLUÍDA")
print(f"   Verificadas:  {result['segmentacoes_verificadas']}")
print(f"   Alertas:      {result['alertas_gerados']}")
print(f"   Travadas:     {result['execucoes_travadas']}")
print(f"{'='*60}")

dbutils.notebook.exit(json.dumps(result))
