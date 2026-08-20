"""API Operação — Dashboard + Alertas (BACK-12).

Monitoramento operacional do EngagementHub:
  GET    /operacao/dashboard        — Métricas consolidadas (fila, envios, taxas)
  GET    /operacao/saude            — Status de saúde dos componentes
  POST   /operacao/saude/verificar  — Forçar verificação de saúde
  GET    /operacao/alertas          — Notificações/alertas ativos
  POST   /operacao/alertas/{id}/lida— Marcar alerta como lido
  GET    /operacao/fila/resumo      — Breakdown da fila por status/canal
  GET    /operacao/metricas/envios  — Métricas de envio (por dia/canal)
  POST   /operacao/notificar        — Criar notificação manual
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from src.core.config import (
    TABLE_FILA,
    TABLE_NOTIFICACAO,
    TABLE_SAUDE_OP,
    TABLE_TRACKING,
    TABLE_DISPARO_EVENTOS,
    TABLE_CAMPANHA,
)
from src.core.security import require_perfil
from src.db.databricks_client import get_client

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class NotificarRequest(BaseModel):
    destinatario: str
    tipo: str = "manual"
    entidade_tipo: Optional[str] = None
    entidade_id: Optional[str] = None
    titulo: str
    mensagem: str
    severidade: str = "info"  # info, warning, critical


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/dashboard")
async def dashboard_operacional(
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    """Métricas consolidadas para o dashboard operacional."""
    client = get_client()

    # Fila por status
    fila_stats = client.fetch_all(
        f"SELECT status, COUNT(*) as qtd FROM {TABLE_FILA} GROUP BY status"
    )
    fila_map = {r[0]: int(r[1]) for r in (fila_stats or [])}

    # Tracking por status
    tracking_stats = client.fetch_all(
        f"SELECT status_atual, COUNT(*) as qtd FROM {TABLE_TRACKING} GROUP BY status_atual"
    )
    tracking_map = {r[0]: int(r[1]) for r in (tracking_stats or [])}

    # Campanhas ativas
    campanhas_ativas = client.fetch_one(
        f"SELECT COUNT(*) FROM {TABLE_CAMPANHA} WHERE status = 'ativa'"
    )

    # Alertas não lidos
    alertas_pendentes = client.fetch_one(
        f"SELECT COUNT(*) FROM {TABLE_NOTIFICACAO} WHERE lida = 0"
    )

    # Taxas de funil
    total_enviados = tracking_map.get("enviado", 0) + tracking_map.get("entregue", 0) + \
                     tracking_map.get("aberto", 0) + tracking_map.get("clicou", 0) + \
                     tracking_map.get("converteu", 0)
    total_abertos = tracking_map.get("aberto", 0) + tracking_map.get("clicou", 0) + \
                    tracking_map.get("converteu", 0)
    total_clicou = tracking_map.get("clicou", 0) + tracking_map.get("converteu", 0)

    taxa_abertura = round(total_abertos / total_enviados * 100, 2) if total_enviados > 0 else 0
    taxa_clique = round(total_clicou / total_enviados * 100, 2) if total_enviados > 0 else 0

    return {
        "data": {
            "fila": fila_map,
            "tracking": tracking_map,
            "campanhas_ativas": int(campanhas_ativas[0]) if campanhas_ativas else 0,
            "alertas_pendentes": int(alertas_pendentes[0]) if alertas_pendentes else 0,
            "funil": {
                "total_enviados": total_enviados,
                "total_abertos": total_abertos,
                "total_clicou": total_clicou,
                "total_converteu": tracking_map.get("converteu", 0),
                "taxa_abertura_pct": taxa_abertura,
                "taxa_clique_pct": taxa_clique,
            },
        }
    }


@router.get("/saude")
async def saude_sistema(
    user: dict = Depends(require_perfil(["admin"])),
):
    """Status de saúde dos componentes do sistema (latest per escopo)."""
    client = get_client()

    # Buscar apenas a última verificação por escopo (evita histórico poluindo status)
    rows = client.fetch_all(
        f"""
        SELECT s.metrica_id, s.escopo, s.valor, s.status, s.detalhe, s.ultima_verificacao
        FROM {TABLE_SAUDE_OP} s
        INNER JOIN (
            SELECT escopo, MAX(ultima_verificacao) as max_verif
            FROM {TABLE_SAUDE_OP}
            GROUP BY escopo
        ) latest ON s.escopo = latest.escopo AND s.ultima_verificacao = latest.max_verif
        ORDER BY s.escopo
        """
    )

    componentes = [
        {
            "metrica_id": r[0], "escopo": r[1], "valor": r[2],
            "status": r[3], "detalhe": r[4], "ultima_verificacao": r[5],
        }
        for r in (rows or [])
    ]

    # Calcular status global
    status_global = "saudavel"
    for c in componentes:
        if c["status"] == "critico":
            status_global = "critico"
            break
        elif c["status"] == "degradado":
            status_global = "degradado"

    return {"data": {"status_global": status_global, "componentes": componentes}}


@router.post("/saude/verificar")
async def verificar_saude(
    user: dict = Depends(require_perfil(["admin"])),
):
    """Força verificação de saúde e atualiza métricas."""
    client = get_client()
    agora = _utc_now()

    # Check 1: Fila com itens travados (status=processando há muito tempo)
    fila_travada = client.fetch_one(
        f"SELECT COUNT(*) FROM {TABLE_FILA} WHERE status = 'processando'"
    )
    qtd_travada = int(fila_travada[0]) if fila_travada else 0
    status_fila = "critico" if qtd_travada > 50 else "degradado" if qtd_travada > 10 else "saudavel"

    client.execute_insert(
        f"""
        INSERT INTO {TABLE_SAUDE_OP} (metrica_id, escopo, valor, status, detalhe, ultima_verificacao)
        VALUES (?, 'fila_disparo', ?, ?, ?, ?)
        """,
        (f"saude_{uuid4().hex[:8]}", qtd_travada, status_fila,
         f"{qtd_travada} itens travados em 'processando'", agora),
    )

    # Check 2: Erros recentes (eventos tipo=erro nas últimas horas)
    erros_recentes = client.fetch_one(
        f"SELECT COUNT(*) FROM {TABLE_DISPARO_EVENTOS} WHERE tipo_evento = 'erro'"
    )
    qtd_erros = int(erros_recentes[0]) if erros_recentes else 0
    status_erros = "critico" if qtd_erros > 100 else "degradado" if qtd_erros > 20 else "saudavel"

    client.execute_insert(
        f"""
        INSERT INTO {TABLE_SAUDE_OP} (metrica_id, escopo, valor, status, detalhe, ultima_verificacao)
        VALUES (?, 'erros_disparo', ?, ?, ?, ?)
        """,
        (f"saude_{uuid4().hex[:8]}", qtd_erros, status_erros,
         f"{qtd_erros} eventos de erro", agora),
    )

    # Check 3: Fila pendente acumulada
    fila_pendente = client.fetch_one(
        f"SELECT COUNT(*) FROM {TABLE_FILA} WHERE status = 'pendente'"
    )
    qtd_pendente = int(fila_pendente[0]) if fila_pendente else 0
    status_pendente = "degradado" if qtd_pendente > 1000 else "saudavel"

    client.execute_insert(
        f"""
        INSERT INTO {TABLE_SAUDE_OP} (metrica_id, escopo, valor, status, detalhe, ultima_verificacao)
        VALUES (?, 'fila_pendente', ?, ?, ?, ?)
        """,
        (f"saude_{uuid4().hex[:8]}", qtd_pendente, status_pendente,
         f"{qtd_pendente} itens pendentes na fila", agora),
    )

    # Emitir alerta se crítico
    if status_fila == "critico" or status_erros == "critico":
        client.execute_insert(
            f"""
            INSERT INTO {TABLE_NOTIFICACAO}
            (notif_id, destinatario, tipo, entidade_tipo, entidade_id,
             titulo, mensagem, severidade, lida, criado_em)
            VALUES (?, 'admin', 'automatico', 'sistema', 'saude',
                    ?, ?, 'critical', 0, ?)
            """,
            (
                f"notif_{uuid4().hex[:12]}",
                "Alerta crítico de saúde",
                f"Fila travada: {qtd_travada} | Erros: {qtd_erros}",
                agora,
            ),
        )

    return {
        "data": {
            "verificado_em": agora,
            "resultados": {
                "fila_travada": {"valor": qtd_travada, "status": status_fila},
                "erros_disparo": {"valor": qtd_erros, "status": status_erros},
                "fila_pendente": {"valor": qtd_pendente, "status": status_pendente},
            },
            "alerta_emitido": status_fila == "critico" or status_erros == "critico",
        }
    }


@router.get("/alertas")
async def listar_alertas(
    lida: int | None = Query(default=None, description="0=não lidos, 1=lidos"),
    severidade: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    """Lista notificações/alertas com filtros."""
    client = get_client()

    where_clauses = []
    params = []
    if lida is not None:
        where_clauses.append("lida = ?")
        params.append(lida)
    if severidade:
        where_clauses.append("severidade = ?")
        params.append(severidade)

    where = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    rows = client.fetch_all(
        f"""
        SELECT notif_id, destinatario, tipo, entidade_tipo, entidade_id,
               titulo, mensagem, severidade, lida, criado_em
        FROM {TABLE_NOTIFICACAO}
        {where}
        ORDER BY criado_em DESC
        LIMIT {int(limit)}
        """,
        tuple(params) if params else (),
    )
    return {
        "data": [
            {
                "notif_id": r[0], "destinatario": r[1], "tipo": r[2],
                "entidade_tipo": r[3], "entidade_id": r[4],
                "titulo": r[5], "mensagem": r[6], "severidade": r[7],
                "lida": bool(r[8]), "criado_em": r[9],
            }
            for r in (rows or [])
        ]
    }


@router.post("/alertas/{notif_id}/lida")
async def marcar_alerta_lido(
    notif_id: str,
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    """Marca um alerta como lido."""
    client = get_client()

    existing = client.fetch_one(
        f"SELECT notif_id FROM {TABLE_NOTIFICACAO} WHERE notif_id = ?",
        (notif_id,),
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Alerta não encontrado")

    client.execute_insert(
        f"UPDATE {TABLE_NOTIFICACAO} SET lida = 1 WHERE notif_id = ?",
        (notif_id,),
    )
    return {"data": {"notif_id": notif_id, "lida": True}}


@router.get("/fila/resumo")
async def resumo_fila(
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    """Breakdown da fila de disparo por status e canal."""
    client = get_client()

    # Por status
    por_status = client.fetch_all(
        f"SELECT status, COUNT(*) FROM {TABLE_FILA} GROUP BY status"
    )

    # Por canal
    por_canal = client.fetch_all(
        f"SELECT canal, COUNT(*) FROM {TABLE_FILA} GROUP BY canal"
    )

    # Por canal + status (matrix)
    matrix = client.fetch_all(
        f"SELECT canal, status, COUNT(*) FROM {TABLE_FILA} GROUP BY canal, status"
    )

    return {
        "data": {
            "por_status": {r[0]: int(r[1]) for r in (por_status or [])},
            "por_canal": {r[0]: int(r[1]) for r in (por_canal or [])},
            "matrix": [
                {"canal": r[0], "status": r[1], "qtd": int(r[2])}
                for r in (matrix or [])
            ],
        }
    }


@router.get("/metricas/envios")
async def metricas_envios(
    dias: int = Query(default=7, ge=1, le=90),
    canal: str | None = Query(default=None),
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    """Métricas de envio agregadas por dia."""
    client = get_client()

    where_canal = "AND canal = ?" if canal else ""
    params = (canal,) if canal else ()

    # Agrupando por data (substr do campo criado_em ISO)
    rows = client.fetch_all(
        f"""
        SELECT SUBSTR(criado_em, 1, 10) as dia, canal, COUNT(*) as qtd
        FROM {TABLE_FILA}
        WHERE criado_em IS NOT NULL {where_canal}
        GROUP BY SUBSTR(criado_em, 1, 10), canal
        ORDER BY dia DESC
        LIMIT {int(dias * 5)}
        """,
        params,
    )

    return {
        "data": [
            {"dia": r[0], "canal": r[1], "qtd": int(r[2])}
            for r in (rows or [])
        ]
    }


@router.post("/notificar")
async def criar_notificacao(
    body: NotificarRequest,
    user: dict = Depends(require_perfil(["admin"])),
):
    """Cria notificação/alerta manual."""
    client = get_client()
    agora = _utc_now()
    notif_id = f"notif_{uuid4().hex[:12]}"

    if body.severidade not in ("info", "warning", "critical"):
        raise HTTPException(status_code=400, detail="severidade deve ser: info, warning, critical")

    client.execute_insert(
        f"""
        INSERT INTO {TABLE_NOTIFICACAO}
        (notif_id, destinatario, tipo, entidade_tipo, entidade_id,
         titulo, mensagem, severidade, lida, criado_em)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
        """,
        (
            notif_id, body.destinatario, body.tipo,
            body.entidade_tipo, body.entidade_id,
            body.titulo, body.mensagem, body.severidade, agora,
        ),
    )
    return {"data": {"notif_id": notif_id, "severidade": body.severidade}}
