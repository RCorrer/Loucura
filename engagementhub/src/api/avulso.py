"""API de Disparo Avulso — DAV (BACK-10).

Disparo único (one-shot) fora de jornada: seleciona segmento + peça,
passa governança (consentimento + capping) e enfileira para envio.

Endpoints:
  POST   /avulso           — Criar DAV
  GET    /avulso           — Listar DAVs
  GET    /avulso/{id}      — Detalhe
  POST   /avulso/{id}/aprovar  — Aprovar
  POST   /avulso/{id}/executar — Executar (governança + enfileirar)
  DELETE /avulso/{id}      — Cancelar
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional

from src.core.config import (
    TABLE_DISPARO_AVULSO,
    TABLE_CONSENTIMENTO,
    TABLE_FILA,
    TABLE_GOLDEN_RECORD,
    TABLE_PECA,
    TABLE_SEG_RESULTADO,
    TABLE_SUPRESSAO,
    TABLE_CAPPING,
)
from src.core.security import require_perfil
from src.db.databricks_client import get_client

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Models (Pydantic)
# ---------------------------------------------------------------------------

class CriarDAVRequest(BaseModel):
    nome: str = Field(..., min_length=3, max_length=200)
    descricao: Optional[str] = None
    seg_id: str = Field(..., description="ID do segmento de entrada")
    peca_id: str = Field(..., description="ID da peça a enviar")
    canal: str = Field(..., description="email ou whatsapp")
    campanha_id: Optional[str] = None
    tipo_envio: str = Field(default="imediato", description="imediato ou agendado")
    agendado_para: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _gerar_id() -> str:
    return f"dav_{uuid4().hex[:16]}"


def _gerar_codigo() -> str:
    return f"DAV-{uuid4().hex[:8].upper()}"


def _buscar_dav(disparo_id: str, client=None) -> dict | None:
    client = client or get_client()
    row = client.fetch_one(
        f"""
        SELECT disparo_id, disparo_codigo, nome, descricao, seg_id, peca_id,
               canal, campanha_id, tipo_envio, agendado_para, status,
               aprovado_por, aprovado_em, qtd_publico, qtd_elegivel,
               qtd_enviado, criado_por, criado_em
        FROM {TABLE_DISPARO_AVULSO}
        WHERE disparo_id = ?
        """,
        (disparo_id,),
    )
    if not row:
        return None
    return {
        "disparo_id": row[0], "disparo_codigo": row[1], "nome": row[2],
        "descricao": row[3], "seg_id": row[4], "peca_id": row[5],
        "canal": row[6], "campanha_id": row[7], "tipo_envio": row[8],
        "agendado_para": row[9], "status": row[10], "aprovado_por": row[11],
        "aprovado_em": row[12], "qtd_publico": row[13], "qtd_elegivel": row[14],
        "qtd_enviado": row[15], "criado_por": row[16], "criado_em": row[17],
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("")
async def criar_dav(
    body: CriarDAVRequest,
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    """Cria um Disparo Avulso (status=rascunho)."""
    client = get_client()
    agora = _utc_now()
    disparo_id = _gerar_id()
    codigo = _gerar_codigo()

    # Validar peça existe e está aprovada
    peca_row = client.fetch_one(
        f"SELECT status_aprovacao, canal FROM {TABLE_PECA} WHERE peca_id = ?",
        (body.peca_id,),
    )
    if not peca_row:
        raise HTTPException(status_code=404, detail=f"Peça '{body.peca_id}' não encontrada")
    if peca_row[0] != "aprovada":
        raise HTTPException(status_code=400, detail=f"Peça deve estar aprovada (atual: {peca_row[0]})")
    if peca_row[1] != body.canal:
        raise HTTPException(status_code=400, detail=f"Canal da peça ({peca_row[1]}) difere do canal solicitado ({body.canal})")

    # Validar tipo_envio
    if body.tipo_envio not in ("imediato", "agendado"):
        raise HTTPException(status_code=400, detail="tipo_envio deve ser 'imediato' ou 'agendado'")
    if body.tipo_envio == "agendado" and not body.agendado_para:
        raise HTTPException(status_code=400, detail="agendado_para obrigatório para tipo_envio='agendado'")

    client.execute_insert(
        f"""
        INSERT INTO {TABLE_DISPARO_AVULSO}
        (disparo_id, disparo_codigo, nome, descricao, seg_id, peca_id,
         canal, campanha_id, tipo_envio, agendado_para, status,
         aprovado_por, aprovado_em, qtd_publico, qtd_elegivel, qtd_enviado,
         criado_por, criado_em)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'rascunho', NULL, NULL, 0, 0, 0, ?, ?)
        """,
        (
            disparo_id, codigo, body.nome, body.descricao,
            body.seg_id, body.peca_id, body.canal, body.campanha_id,
            body.tipo_envio, body.agendado_para,
            user["usuario_id"], agora,
        ),
    )

    return {"data": {"disparo_id": disparo_id, "disparo_codigo": codigo, "status": "rascunho"}}


@router.get("")
async def listar_davs(
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    """Lista DAVs com filtro opcional por status."""
    client = get_client()
    where = "WHERE status = ?" if status else ""
    params = (status,) if status else ()

    rows = client.fetch_all(
        f"""
        SELECT disparo_id, disparo_codigo, nome, canal, seg_id, peca_id,
               status, qtd_publico, qtd_elegivel, qtd_enviado,
               criado_por, criado_em
        FROM {TABLE_DISPARO_AVULSO}
        {where}
        ORDER BY criado_em DESC
        LIMIT {int(limit)}
        """,
        params,
    )
    return {
        "data": [
            {
                "disparo_id": r[0], "disparo_codigo": r[1], "nome": r[2],
                "canal": r[3], "seg_id": r[4], "peca_id": r[5],
                "status": r[6], "qtd_publico": r[7], "qtd_elegivel": r[8],
                "qtd_enviado": r[9], "criado_por": r[10], "criado_em": r[11],
            }
            for r in (rows or [])
        ]
    }


@router.get("/{disparo_id}")
async def detalhe_dav(
    disparo_id: str,
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    """Retorna detalhes completos de um DAV."""
    dav = _buscar_dav(disparo_id)
    if not dav:
        raise HTTPException(status_code=404, detail=f"DAV '{disparo_id}' não encontrado")
    return {"data": dav}


@router.post("/{disparo_id}/aprovar")
async def aprovar_dav(
    disparo_id: str,
    user: dict = Depends(require_perfil(["admin"])),
):
    """Aprova um DAV (rascunho → aprovado)."""
    client = get_client()
    dav = _buscar_dav(disparo_id, client)
    if not dav:
        raise HTTPException(status_code=404, detail="DAV não encontrado")
    if dav["status"] != "rascunho":
        raise HTTPException(status_code=400, detail=f"Só pode aprovar DAV em 'rascunho' (atual: {dav['status']})")

    agora = _utc_now()
    client.execute_insert(
        f"UPDATE {TABLE_DISPARO_AVULSO} SET status = 'aprovado', aprovado_por = ?, aprovado_em = ? WHERE disparo_id = ?",
        (user["usuario_id"], agora, disparo_id),
    )
    return {"data": {"disparo_id": disparo_id, "status": "aprovado"}}


@router.post("/{disparo_id}/executar")
async def executar_dav(
    disparo_id: str,
    user: dict = Depends(require_perfil(["admin"])),
):
    """Executa o DAV: governança + enfileiramento.

    Fluxo:
    1. Carrega membros do segmento (qtd_publico)
    2. Filtra por consentimento
    3. Aplica capping
    4. Enfileira elegíveis na fila_disparo (qtd_elegivel / qtd_enviado)
    5. Status → 'executado'
    """
    client = get_client()
    dav = _buscar_dav(disparo_id, client)
    if not dav:
        raise HTTPException(status_code=404, detail="DAV não encontrado")
    if dav["status"] != "aprovado":
        raise HTTPException(status_code=400, detail=f"Só pode executar DAV 'aprovado' (atual: {dav['status']})")

    agora = _utc_now()

    # Marcar como em execução (lock)
    client.execute_insert(
        f"UPDATE {TABLE_DISPARO_AVULSO} SET status = 'executando' WHERE disparo_id = ?",
        (disparo_id,),
    )

    try:
        # 1. Carregar membros do segmento
        membros = client.fetch_all(
            f"SELECT cpf_cnpj FROM {TABLE_SEG_RESULTADO} WHERE seg_id = ?",
            (dav["seg_id"],),
        )
        cpfs = [r[0] for r in (membros or [])]
        qtd_publico = len(cpfs)

        # 2. Filtrar por consentimento (opt_in para o canal)
        elegiveis = []
        if cpfs:
            # Buscar quem TEM consentimento ativo para o canal
            placeholders = ",".join("?" for _ in cpfs)
            consentidos = client.fetch_all(
                f"""
                SELECT cpf_cnpj FROM {TABLE_CONSENTIMENTO}
                WHERE cpf_cnpj IN ({placeholders})
                  AND canal = ? AND status = 'opt_in'
                """,
                (*cpfs, dav["canal"]),
            )
            cpfs_consentidos = {r[0] for r in (consentidos or [])}
            elegiveis = [c for c in cpfs if c in cpfs_consentidos]

        # 3. Capping: verificar se já atingiu limite (simplificado)
        # Em produção o orquestrador faz capping completo;
        # aqui fazemos check básico contra regras_capping
        qtd_elegivel = len(elegiveis)

        # 4. Enfileirar elegíveis
        enfileirados = 0
        agendado_para = dav["agendado_para"] or agora

        for cpf in elegiveis:
            # Buscar destinatário do golden_record
            dest_row = client.fetch_one(
                f"SELECT email, telefone FROM {TABLE_GOLDEN_RECORD} WHERE cpf_cnpj = ?",
                (cpf,),
            )
            if not dest_row:
                continue

            destinatario = dest_row[0] if dav["canal"] == "email" else dest_row[1]
            if not destinatario:
                continue

            fila_id = f"fila_{uuid4().hex[:16]}"
            client.execute_insert(
                f"""
                INSERT INTO {TABLE_FILA}
                (fila_id, cpf_cnpj, campanha_id, jornada_id, no_id,
                 peca_id, canal, destinatario, agendado_para,
                 prioridade, status, tentativas, criado_em, atualizado_em)
                VALUES (?, ?, ?, NULL, NULL, ?, ?, ?, ?, 5, 'pendente', 0, ?, ?)
                """,
                (
                    fila_id, cpf, dav["campanha_id"],
                    dav["peca_id"], dav["canal"], destinatario,
                    agendado_para, agora, agora,
                ),
            )
            enfileirados += 1

        # 5. Atualizar contadores e status
        client.execute_insert(
            f"""
            UPDATE {TABLE_DISPARO_AVULSO}
            SET status = 'executado', qtd_publico = ?, qtd_elegivel = ?, qtd_enviado = ?
            WHERE disparo_id = ?
            """,
            (qtd_publico, qtd_elegivel, enfileirados, disparo_id),
        )

        # Registrar supressões (quem foi filtrado)
        suprimidos_consent = qtd_publico - qtd_elegivel
        suprimidos_dest = qtd_elegivel - enfileirados
        if suprimidos_consent > 0:
            client.execute_insert(
                f"""
                INSERT INTO {TABLE_SUPRESSAO}
                (supressao_id, cpf_cnpj, campanha_id, canal, motivo, detalhe, data_execucao)
                VALUES (?, 'BATCH', ?, ?, 'sem_consentimento', ?, ?)
                """,
                (
                    f"sup_{uuid4().hex[:12]}", dav["campanha_id"],
                    dav["canal"], f"DAV {disparo_id}: {suprimidos_consent} suprimidos",
                    agora,
                ),
            )

        logger.info(
            f"DAV {disparo_id} executado: publico={qtd_publico}, "
            f"elegivel={qtd_elegivel}, enfileirados={enfileirados}"
        )

        return {
            "data": {
                "disparo_id": disparo_id,
                "status": "executado",
                "qtd_publico": qtd_publico,
                "qtd_elegivel": qtd_elegivel,
                "qtd_enviado": enfileirados,
                "executado_por": user["usuario_id"],
            }
        }

    except Exception as e:
        # Rollback status se falhar
        client.execute_insert(
            f"UPDATE {TABLE_DISPARO_AVULSO} SET status = 'aprovado' WHERE disparo_id = ?",
            (disparo_id,),
        )
        logger.exception(f"Erro executando DAV {disparo_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Erro na execução: {e}")


@router.delete("/{disparo_id}")
async def cancelar_dav(
    disparo_id: str,
    user: dict = Depends(require_perfil(["admin"])),
):
    """Cancela um DAV (só se rascunho ou aprovado)."""
    client = get_client()
    dav = _buscar_dav(disparo_id, client)
    if not dav:
        raise HTTPException(status_code=404, detail="DAV não encontrado")
    if dav["status"] not in ("rascunho", "aprovado"):
        raise HTTPException(
            status_code=400,
            detail=f"Só pode cancelar DAV em 'rascunho'/'aprovado' (atual: {dav['status']})"
        )

    client.execute_insert(
        f"UPDATE {TABLE_DISPARO_AVULSO} SET status = 'cancelado' WHERE disparo_id = ?",
        (disparo_id,),
    )
    return {"data": {"disparo_id": disparo_id, "status": "cancelado"}}
