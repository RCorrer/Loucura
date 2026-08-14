#!/usr/bin/env python3
"""
[DEPRECATED] Este script foi substituído pela arquitetura job-per-segment.

A criação de jobs agora é feita pelo JobManagerService (backend)
automaticamente quando uma segmentação é ativada.

Veja: databricks/jobs/s1_segmenthub/JOBS_MANIFEST.md
"""

import os
import json
from databricks.sdk import WorkspaceClient
from databricks.sdk.service import jobs

# ============================================================
# CONFIGURAÇÃO
# ============================================================
# ⚠️ ATENÇÃO: Ajuste este caminho para o local dos notebooks no seu workspace
NOTEBOOK_BASE_PATH = "/Workspace/Users/rafael_correr@hotmail.com/campaign_databricks_app/databricks/jobs"

# Definição dos jobs
JOBS = [
    {
        "name": "S1-JOB-01 - seg_exec",
        "notebook_path": f"{NOTEBOOK_BASE_PATH}/seg_exec",
        "parameters": [
            {"name": "seg_id", "default": ""},
            {"name": "origem_execucao", "default": "agendada"}
        ],
        "schedule": None,  # Será disparado manualmente ou via API
        "timeout_seconds": 3600,
        "max_retries": 1,
    },
    {
        "name": "S1-JOB-02 - seg_guardiao",
        "notebook_path": f"{NOTEBOOK_BASE_PATH}/seg_guardiao",
        "parameters": [],
        "schedule": {
            "quartz_cron_expression": "0 0 * * * ?",  # Diário à meia-noite
            "timezone_id": "America/Sao_Paulo"
        },
        "timeout_seconds": 600,
        "max_retries": 1,
    },
    {
        "name": "S1-JOB-03 - seg_saude",
        "notebook_path": f"{NOTEBOOK_BASE_PATH}/seg_saude",
        "parameters": [],
        "schedule": {
            "quartz_cron_expression": "0 0 * * * ?",  # Diário
            "timezone_id": "America/Sao_Paulo"
        },
        "timeout_seconds": 600,
        "max_retries": 1,
    },
    {
        "name": "S1-JOB-04 - seg_overlap",
        "notebook_path": f"{NOTEBOOK_BASE_PATH}/seg_overlap",
        "parameters": [],
        "schedule": {
            "quartz_cron_expression": "0 0 * * * ?",  # Diário
            "timezone_id": "America/Sao_Paulo"
        },
        "timeout_seconds": 600,
        "max_retries": 1,
    },
]

# ============================================================
# CRIAÇÃO DOS JOBS
# ============================================================

def create_jobs():
    """Cria os jobs no Databricks Workflows."""
    w = WorkspaceClient()

    for job_def in JOBS:
        print(f"📦 Criando job: {job_def['name']}")

        # Configura a tarefa do notebook
        notebook_task = jobs.NotebookTask(
            notebook_path=job_def["notebook_path"],
            base_parameters={
                p["name"]: p.get("default", "")
                for p in job_def.get("parameters", [])
            }
        )

        # Configura o schedule se existir
        schedule = None
        if job_def.get("schedule"):
            schedule = jobs.CronSchedule(
                quartz_cron_expression=job_def["schedule"]["quartz_cron_expression"],
                timezone_id=job_def["schedule"]["timezone_id"],
            )

        # Cria o job
        job = w.jobs.create(
            name=job_def["name"],
            tasks=[
                jobs.Task(
                    task_key="notebook_task",
                    notebook_task=notebook_task,
                    timeout_seconds=job_def.get("timeout_seconds", 3600),
                    max_retries=job_def.get("max_retries", 1),
                    retry_on_timeout=False,
                )
            ],
            schedule=schedule,
        )

        print(f"✅ Job criado: {job_def['name']} (ID: {job.job_id})")

# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":
    create_jobs()