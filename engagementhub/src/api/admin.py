"""API Admin — Otimização MAB (BACK-11).

Endpoints para gerenciar a otimização Multi-Armed Bandit:
  GET    /admin/mab/variantes         — Listar variantes (com resultados)
  POST   /admin/mab/recalcular        — Disparar recalculo Thompson Sampling
  POST   /admin/mab/pausar            — Pausar uma variante
  POST   /admin/mab/fixar-vencedora   — Fixar vencedora (congela otimização)
  GET    /admin/mab/historico          — Histórico de mudanças de peso
  GET    /admin/mab/config             — Config atual de otimização
  PUT    /admin/mab/config             — Atualizar config
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional

from src.core.config import (
    TABLE_CONFIG_OTIMIZACAO,
    TABLE_OTIMIZACAO_HISTORICO,
)
from src.core.mab import (
    carregar_config_otimizacao,
    carregar_resultados,
    carregar_variantes,
    executar_otimizador_mab,
    fixar_vencedora,
    pausar_variante,
)
from src.core.security import require_perfil
from src.db.databricks_client import get_client

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class PausarRequest(BaseModel):
    variante_id: str
    motivo: Optional[str] = "pausada_manual"


class FixarRequest(BaseModel):
    variante_id: str


class ConfigOtimizacaoUpdate(BaseModel):
    metrica_alvo: Optional[str] = None
    janela_avaliacao_horas: Optional[int] = None
    trafego_minimo_pct: Optional[float] = None
    min_amostras_por_variante: Optional[int] = None
    frequencia_recalculo: Optional[str] = None
    otimizacao_ativa: Optional[bool] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/mab/variantes")
async def listar_variantes_mab(
    jornada_id: str | None = Query(default=None),
    user: dict = Depends(require_perfil(["admin"])),
):
    """Lista variantes com resultados atuais e peso."""
    client = get_client()
    variantes = carregar_variantes(jornada_id, client)

    # Enriquecer com resultados
    resultado = []
    for v in variantes:
        res = carregar_resultados(v["variante_id"], client)
        taxa = 0.0
        if res["envios"] > 0:
            taxa = round(res["aberturas"] / res["envios"] * 100, 2)

        resultado.append({
            **v,
            "resultados": res,
            "taxa_abertura_pct": taxa,
        })

    return {"data": resultado}


@router.post("/mab/recalcular")
async def recalcular_mab(
    user: dict = Depends(require_perfil(["admin"])),
):
    """Dispara recalculo manual de pesos via Thompson Sampling."""
    client = get_client()
    try:
        metricas = executar_otimizador_mab(client)
        return {"data": metricas}
    except Exception as e:
        logger.exception(f"Erro no recálculo MAB: {e}")
        raise HTTPException(status_code=500, detail=f"Erro no recálculo: {e}")


@router.post("/mab/pausar")
async def pausar_variante_endpoint(
    body: PausarRequest,
    user: dict = Depends(require_perfil(["admin"])),
):
    """Pausa uma variante (peso=0, redistribui para restantes)."""
    client = get_client()
    resultado = pausar_variante(body.variante_id, body.motivo or "pausada_manual", client)
    if "erro" in resultado:
        raise HTTPException(status_code=404, detail=resultado["erro"])
    return {"data": resultado}


@router.post("/mab/fixar-vencedora")
async def fixar_vencedora_endpoint(
    body: FixarRequest,
    user: dict = Depends(require_perfil(["admin"])),
):
    """Fixa uma variante como vencedora (peso=1.0, demais desativadas)."""
    client = get_client()
    resultado = fixar_vencedora(body.variante_id, client)
    if "erro" in resultado:
        raise HTTPException(status_code=404, detail=resultado["erro"])
    return {"data": resultado}


@router.get("/mab/historico")
async def historico_mab(
    variante_id: str | None = Query(default=None),
    jornada_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    user: dict = Depends(require_perfil(["admin"])),
):
    """Histórico de mudanças de peso (para auditoria)."""
    client = get_client()

    where_clauses = []
    params = []
    if variante_id:
        where_clauses.append("variante_id = ?")
        params.append(variante_id)
    if jornada_id:
        where_clauses.append("jornada_id = ?")
        params.append(jornada_id)

    where = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    rows = client.fetch_all(
        f"""
        SELECT hist_id, variante_id, jornada_id, peso_anterior, peso_novo,
               motivo, recalculado_em
        FROM {TABLE_OTIMIZACAO_HISTORICO}
        {where}
        ORDER BY recalculado_em DESC
        LIMIT {int(limit)}
        """,
        tuple(params) if params else None,
    )
    return {
        "data": [
            {
                "hist_id": r[0], "variante_id": r[1], "jornada_id": r[2],
                "peso_anterior": r[3], "peso_novo": r[4],
                "motivo": r[5], "recalculado_em": r[6],
            }
            for r in (rows or [])
        ]
    }


@router.get("/mab/config")
async def get_config_otimizacao(
    user: dict = Depends(require_perfil(["admin"])),
):
    """Retorna configuração atual de otimização."""
    config = carregar_config_otimizacao("global")
    return {"data": config}


@router.put("/mab/config")
async def atualizar_config_otimizacao(
    body: ConfigOtimizacaoUpdate,
    user: dict = Depends(require_perfil(["admin"])),
):
    """Atualiza configuração de otimização."""
    client = get_client()
    agora = _utc_now()

    # Verificar se existe registro
    existing = client.fetch_one(
        f"SELECT config_id FROM {TABLE_CONFIG_OTIMIZACAO} WHERE escopo = 'global' AND ativo = 1"
    )

    # Montar SET dinâmico só com campos fornecidos
    updates = []
    params = []
    if body.metrica_alvo is not None:
        if body.metrica_alvo not in ("aberturas", "cliques", "conversoes"):
            raise HTTPException(status_code=400, detail="metrica_alvo deve ser: aberturas, cliques, conversoes")
        updates.append("metrica_alvo = ?")
        params.append(body.metrica_alvo)
    if body.janela_avaliacao_horas is not None:
        updates.append("janela_avaliacao_horas = ?")
        params.append(body.janela_avaliacao_horas)
    if body.trafego_minimo_pct is not None:
        if not (1.0 <= body.trafego_minimo_pct <= 50.0):
            raise HTTPException(status_code=400, detail="trafego_minimo_pct deve estar entre 1.0 e 50.0")
        updates.append("trafego_minimo_pct = ?")
        params.append(body.trafego_minimo_pct)
    if body.min_amostras_por_variante is not None:
        updates.append("min_amostras_por_variante = ?")
        params.append(body.min_amostras_por_variante)
    if body.frequencia_recalculo is not None:
        if body.frequencia_recalculo not in ("horario", "diario", "semanal"):
            raise HTTPException(status_code=400, detail="frequencia_recalculo deve ser: horario, diario, semanal")
        updates.append("frequencia_recalculo = ?")
        params.append(body.frequencia_recalculo)
    if body.otimizacao_ativa is not None:
        updates.append("otimizacao_ativa = ?")
        params.append(int(body.otimizacao_ativa))

    if not updates:
        raise HTTPException(status_code=400, detail="Nenhum campo fornecido para atualização")

    updates.append("atualizado_por = ?")
    params.append(user["usuario_id"])
    updates.append("atualizado_em = ?")
    params.append(agora)

    if existing:
        set_clause = ", ".join(updates)
        params.append(existing[0])  # config_id
        client.execute_insert(
            f"UPDATE {TABLE_CONFIG_OTIMIZACAO} SET {set_clause} WHERE config_id = ?",
            tuple(params),
        )
    else:
        # Criar registro
        config_id = f"cfg_{uuid4().hex[:12]}"
        client.execute_insert(
            f"""
            INSERT INTO {TABLE_CONFIG_OTIMIZACAO}
            (config_id, escopo, metrica_alvo, janela_avaliacao_horas,
             trafego_minimo_pct, min_amostras_por_variante,
             frequencia_recalculo, otimizacao_ativa, ativo,
             atualizado_por, atualizado_em)
            VALUES (?, 'global', ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                config_id,
                body.metrica_alvo or "aberturas",
                body.janela_avaliacao_horas or 72,
                body.trafego_minimo_pct or 10.0,
                body.min_amostras_por_variante or 100,
                body.frequencia_recalculo or "diario",
                int(body.otimizacao_ativa) if body.otimizacao_ativa is not None else 1,
                user["usuario_id"], agora,
            ),
        )

    return {"data": carregar_config_otimizacao("global", client)}
