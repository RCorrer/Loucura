# Databricks notebook source
# S1-JOB-02: seg_guardiao (vigência)
# Operações leves – mantém cliente SQL (sem PySpark)

# ATENÇÃO: Ajuste o caminho do projeto se necessário.
# Caminho esperado: /Workspace/Users/rafael_correr@hotmail.com/campaign_databricks_app/databricks/jobs/seg_guardiao

# COMMAND ----------

# MAGIC %md
# MAGIC ### Job de Vigência
# MAGIC Ativa segmentações com vigencia_inicio <= agora e status APROVADA.
# MAGIC Encerra segmentações com vigencia_fim <= agora e status ATIVA.

# COMMAND ----------

import sys
import os
import json
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

from src.db.databricks_client import get_client

# COMMAND ----------

def main():
    client = get_client()
    now = datetime.now().isoformat()
    print(f"🕐 Executando guardião em: {now}")

    # 1. Ativar segmentações agendadas
    sql_ativar = """
        SELECT seg_id, owner
        FROM plataforma.segmentacao.seg_definicao
        WHERE status = 'aprovada'
          AND vigencia_inicio <= current_timestamp()
          AND habilitado = true
    """
    rows_ativar = client.execute_query(sql_ativar)

    for row in rows_ativar:
        seg_id = row["seg_id"]
        sql_update = """
            UPDATE plataforma.segmentacao.seg_definicao
            SET status = 'ativa', atualizado_em = current_timestamp()
            WHERE seg_id = ?
        """
        client.execute_insert(sql_update, (seg_id,))
        hist_id = f"hist_{uuid.uuid4().hex[:8]}"
        sql_hist = """
            INSERT INTO plataforma.segmentacao.seg_historico_estado
            (hist_id, seg_id, estado_anterior, estado_novo, motivo, alterado_por)
            VALUES (?, ?, 'aprovada', 'ativa', 'guardiao_vigencia', 'system')
        """
        client.execute_insert(sql_hist, (hist_id, seg_id))
        print(f"✅ Ativada: {seg_id}")

    # 2. Encerrar segmentações expiradas
    sql_encerrar = """
        SELECT seg_id, owner
        FROM plataforma.segmentacao.seg_definicao
        WHERE status = 'ativa'
          AND vigencia_fim <= current_timestamp()
          AND habilitado = true
    """
    rows_encerrar = client.execute_query(sql_encerrar)

    for row in rows_encerrar:
        seg_id = row["seg_id"]
        sql_update = """
            UPDATE plataforma.segmentacao.seg_definicao
            SET status = 'encerrada', atualizado_em = current_timestamp()
            WHERE seg_id = ?
        """
        client.execute_insert(sql_update, (seg_id,))
        hist_id = f"hist_{uuid.uuid4().hex[:8]}"
        sql_hist = """
            INSERT INTO plataforma.segmentacao.seg_historico_estado
            (hist_id, seg_id, estado_anterior, estado_novo, motivo, alterado_por)
            VALUES (?, ?, 'ativa', 'encerrada', 'guardiao_vigencia', 'system')
        """
        client.execute_insert(sql_hist, (hist_id, seg_id))
        print(f"⛔ Encerrada: {seg_id}")

    print("✅ Guardião concluído.")

# COMMAND ----------

if __name__ == "__main__":
    main()