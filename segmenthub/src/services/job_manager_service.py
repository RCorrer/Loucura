"""
JobManagerService — Gerenciamento de Databricks Jobs para Segmentações

Arquitetura job-per-segment: cada segmentação ativa possui seu próprio
Databricks Job com schedule individual.

Este service é chamado pelo SegmentacaoService durante transições de
ciclo de vida (ativar, pausar, reativar, encerrar, executar manual).

Dependências:
  - databricks-sdk >= 0.20.0
  - Variável de ambiente ou contexto do Databricks App para auth
"""

import os
import uuid
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.jobs import (
    Task,
    NotebookTask,
    CronSchedule,
    JobEmailNotifications,
    QueueSettings,
)

logger = logging.getLogger(__name__)


class JobManagerService:
    """
    Gerencia o ciclo de vida de Databricks Jobs para segmentações.

    Cada segmentação ativa tem 1 job no formato:
      Nome: S1-SEG-{seg_codigo}
      Notebook: seg_exec.py (parametrizado com seg_id)
      Schedule: cron da segmentação
    """

    # Path do notebook de execução (relativo ao workspace)
    NOTEBOOK_PATH = os.getenv(
        "SEG_EXEC_NOTEBOOK_PATH",
        "/Workspace/Users/rafael.correr@bradesco.com.br/Loucura/databricks/jobs/s1_segmenthub/seg_exec"
    )

    # Timezone padrão para schedules
    TIMEZONE = "America/Sao_Paulo"

    # Timeout padrão (1 hora)
    TIMEOUT_SECONDS = 3600

    # Retries padrão
    MAX_RETRIES = 2

    def __init__(self):
        """
        Inicializa o WorkspaceClient.
        Em contexto de Databricks App, a autenticação é automática.
        """
        self.client = WorkspaceClient()
        self._repository = None  # lazy import para evitar circular

    @property
    def repository(self):
        """Lazy import do repository para evitar import circular."""
        if self._repository is None:
            from src.repositories.segmentacao_repository import SegmentacaoRepository
            self._repository = SegmentacaoRepository()
        return self._repository

    # ==================== OPERAÇÕES PRINCIPAIS ====================

    def criar_job(self, seg_id: str, seg_codigo: str, agendamento_cron: str,
                  owner: str = "", email_contato: str = "",
                  area_responsavel: str = "") -> str:
        """
        Cria um Databricks Job para a segmentação.

        Args:
            seg_id: ID da segmentação
            seg_codigo: Código amigável (ex: SEG-ALTA-RENDA-3F2A)
            agendamento_cron: Expressão cron quartz (6 campos)
            owner: Dono da segmentação
            email_contato: Email para notificações de falha
            area_responsavel: Área do owner

        Returns:
            job_id: ID do job criado no Databricks

        Raises:
            Exception: Se a criação falhar
        """
        job_name = f"S1-SEG-{seg_codigo}"

        logger.info(f"Criando job '{job_name}' para segmentação {seg_id}")

        try:
            # Configura schedule (se cron fornecido)
            schedule = None
            if agendamento_cron:
                schedule = CronSchedule(
                    quartz_cron_expression=agendamento_cron,
                    timezone_id=self.TIMEZONE,
                )

            # Configura notificações
            notifications = None
            if email_contato:
                notifications = JobEmailNotifications(
                    on_failure=[email_contato],
                )

            # Cria o job
            job = self.client.jobs.create(
                name=job_name,
                tasks=[
                    Task(
                        task_key="executar_segmentacao",
                        notebook_task=NotebookTask(
                            notebook_path=self.NOTEBOOK_PATH,
                            base_parameters={
                                "seg_id": seg_id,
                                "origem_execucao": "agendada",
                            },
                        ),
                        timeout_seconds=self.TIMEOUT_SECONDS,
                        max_retries=self.MAX_RETRIES,
                        retry_on_timeout=False,
                    )
                ],
                schedule=schedule,
                max_concurrent_runs=1,
                tags={
                    "plataforma": "segmenthub",
                    "seg_id": seg_id,
                    "area": area_responsavel,
                    "owner": owner,
                },
                email_notifications=notifications,
                queue=QueueSettings(enabled=True),
            )

            job_id = str(job.job_id)
            logger.info(f"Job criado com sucesso: {job_name} (ID: {job_id})")

            # Registra no log de auditoria
            self._registrar_log(seg_id, "criar", job_id, None, "sucesso", owner)

            return job_id

        except Exception as e:
            logger.error(f"Erro ao criar job para {seg_id}: {e}")
            self._registrar_log(seg_id, "criar", None, None, "erro", owner, str(e))
            raise

    def pausar_job(self, seg_id: str, job_id: str, usuario: str = "system") -> bool:
        """
        Pausa o job removendo o schedule (job continua existindo).
        Permite reativação posterior sem recriar.
        """
        logger.info(f"Pausando job {job_id} da segmentação {seg_id}")

        try:
            # Remove schedule (job fica sem agendamento)
            self.client.jobs.update(
                job_id=int(job_id),
                new_settings={"schedule": None},
            )

            self._registrar_log(seg_id, "pausar", job_id, None, "sucesso", usuario)
            logger.info(f"Job {job_id} pausado (schedule removido)")
            return True

        except Exception as e:
            logger.error(f"Erro ao pausar job {job_id}: {e}")
            self._registrar_log(seg_id, "pausar", job_id, None, "erro", usuario, str(e))
            raise

    def reativar_job(self, seg_id: str, job_id: str, agendamento_cron: str,
                     usuario: str = "system") -> bool:
        """
        Reativa o job restaurando o schedule.
        """
        logger.info(f"Reativando job {job_id} da segmentação {seg_id}")

        try:
            schedule = CronSchedule(
                quartz_cron_expression=agendamento_cron,
                timezone_id=self.TIMEZONE,
            )

            self.client.jobs.update(
                job_id=int(job_id),
                new_settings={"schedule": schedule},
            )

            self._registrar_log(seg_id, "reativar", job_id, None, "sucesso", usuario)
            logger.info(f"Job {job_id} reativado com cron: {agendamento_cron}")
            return True

        except Exception as e:
            logger.error(f"Erro ao reativar job {job_id}: {e}")
            self._registrar_log(seg_id, "reativar", job_id, None, "erro", usuario, str(e))
            raise

    def deletar_job(self, seg_id: str, job_id: str, usuario: str = "system") -> bool:
        """
        Deleta o job completamente (encerrar/arquivar segmentação).
        """
        logger.info(f"Deletando job {job_id} da segmentação {seg_id}")

        try:
            self.client.jobs.delete(job_id=int(job_id))

            self._registrar_log(seg_id, "deletar", job_id, None, "sucesso", usuario)
            logger.info(f"Job {job_id} deletado")
            return True

        except Exception as e:
            # Se job já não existe, considera sucesso
            if "does not exist" in str(e).lower() or "RESOURCE_DOES_NOT_EXIST" in str(e):
                logger.warning(f"Job {job_id} já não existe, ignorando")
                self._registrar_log(seg_id, "deletar", job_id, None, "sucesso", usuario,
                                    "Job já não existia")
                return True

            logger.error(f"Erro ao deletar job {job_id}: {e}")
            self._registrar_log(seg_id, "deletar", job_id, None, "erro", usuario, str(e))
            raise

    def executar_agora(self, seg_id: str, job_id: str,
                       origem: str = "manual", usuario: str = "system") -> str:
        """
        Dispara execução imediata do job (run_now).

        Returns:
            run_id: ID do run criado
        """
        logger.info(f"Executando job {job_id} (segmentação {seg_id}, origem: {origem})")

        try:
            run = self.client.jobs.run_now(
                job_id=int(job_id),
                notebook_params={
                    "seg_id": seg_id,
                    "origem_execucao": origem,
                },
            )

            run_id = str(run.run_id)
            self._registrar_log(seg_id, "executar", job_id, run_id, "sucesso", usuario)
            logger.info(f"Run disparado: {run_id}")
            return run_id

        except Exception as e:
            logger.error(f"Erro ao executar job {job_id}: {e}")
            self._registrar_log(seg_id, "executar", job_id, None, "erro", usuario, str(e))
            raise

    def atualizar_schedule(self, seg_id: str, job_id: str,
                           agendamento_cron: str, usuario: str = "system") -> bool:
        """
        Atualiza o schedule (cron) de um job existente.
        """
        logger.info(f"Atualizando schedule do job {job_id}: {agendamento_cron}")

        try:
            schedule = CronSchedule(
                quartz_cron_expression=agendamento_cron,
                timezone_id=self.TIMEZONE,
            )

            self.client.jobs.update(
                job_id=int(job_id),
                new_settings={"schedule": schedule},
            )

            self._registrar_log(seg_id, "atualizar_schedule", job_id, None, "sucesso",
                                usuario, f"Novo cron: {agendamento_cron}")
            logger.info(f"Schedule atualizado")
            return True

        except Exception as e:
            logger.error(f"Erro ao atualizar schedule do job {job_id}: {e}")
            self._registrar_log(seg_id, "atualizar_schedule", job_id, None, "erro",
                                usuario, str(e))
            raise

    # ==================== CONSULTAS ====================

    def obter_status_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtém status atual do job (schedule, último run, etc).
        """
        try:
            job = self.client.jobs.get(job_id=int(job_id))
            last_run = None

            # Busca último run
            runs = list(self.client.jobs.list_runs(job_id=int(job_id), limit=1))
            if runs:
                last_run = {
                    "run_id": str(runs[0].run_id),
                    "state": runs[0].state.life_cycle_state.value if runs[0].state else None,
                    "result": runs[0].state.result_state.value if runs[0].state and runs[0].state.result_state else None,
                    "start_time": runs[0].start_time,
                }

            return {
                "job_id": str(job.job_id),
                "name": job.settings.name if job.settings else None,
                "schedule": job.settings.schedule.quartz_cron_expression if job.settings and job.settings.schedule else None,
                "is_paused": job.settings.schedule is None if job.settings else True,
                "last_run": last_run,
            }

        except Exception as e:
            logger.error(f"Erro ao obter status do job {job_id}: {e}")
            return None

    # ==================== AUDITORIA ====================

    def _registrar_log(self, seg_id: str, acao: str, job_id: Optional[str],
                       run_id: Optional[str], status: str,
                       usuario: str = "system", detalhes: str = None):
        """
        Registra operação no log de auditoria (seg_job_log).
        """
        try:
            log_id = f"jlog_{uuid.uuid4().hex[:12]}"
            detalhes_escaped = detalhes.replace("'", "''") if detalhes else None

            from databricks.sdk.runtime import spark
            spark.sql(f"""
                INSERT INTO plataforma.segmentacao.seg_job_log
                (log_id, seg_id, acao, job_id, run_id, status, detalhes, executado_por, criado_em)
                VALUES (
                    '{log_id}',
                    '{seg_id}',
                    '{acao}',
                    {f"'{job_id}'" if job_id else "NULL"},
                    {f"'{run_id}'" if run_id else "NULL"},
                    '{status}',
                    {f"'{detalhes_escaped}'" if detalhes_escaped else "NULL"},
                    '{usuario}',
                    current_timestamp()
                )
            """)
        except Exception as e:
            # Não falha se o log der erro (operação principal já foi executada)
            logger.warning(f"Falha ao registrar log de auditoria: {e}")

    # ==================== HELPERS ====================

    def _job_existe(self, job_id: str) -> bool:
        """Verifica se um job existe no Databricks."""
        try:
            self.client.jobs.get(job_id=int(job_id))
            return True
        except Exception:
            return False
