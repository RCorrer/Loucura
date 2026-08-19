"""API de Campanha (S3-BACK-02): CRUD + Ciclo de Vida.

Endpoints:
  GET    /api/campanhas          - Lista paginada
  GET    /api/campanhas/{id}     - Detalhe + jornadas
  POST   /api/campanhas          - Criar
  PUT    /api/campanhas/{id}     - Editar (versiona)
  POST   /api/campanhas/{id}/aprovar   - RASCUNHO/EM_APROVACAO → APROVADA
  POST   /api/campanhas/{id}/ativar    - APROVADA → ATIVA (valida peças)
  POST   /api/campanhas/{id}/pausar    - ATIVA → PAUSADA
  POST   /api/campanhas/{id}/encerrar  - ATIVA/PAUSADA → ENCERRADA
  PUT    /api/campanhas/{id}/limite    - Configura limite de envios
"""

import uuid
import json
import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from src.db.databricks_client import get_client
from src.core.security import get_user_or_raise, require_perfil
from src.core.config import TABLE_CAMPANHA, CATALOG, SCHEMA_ENG
from src.models.campanha import (
    CampanhaCreate, CampanhaUpdate, LimiteUpdate,
    CampanhaResponse, CampanhaDetalhe,
    StatusCampanha, TRANSICOES_VALIDAS,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _gerar_codigo(nome: str) -> str:
    """Gera código único: CAM-{NOME_SLUG}-{HEX4}"""
    slug = nome.upper().replace(" ", "-")[:20]
    hex4 = uuid.uuid4().hex[:4].upper()
    return f"CAM-{slug}-{hex4}"


def _transitar_estado(
    campanha_id: str, estado_atual: str, estado_novo: StatusCampanha,
    usuario: str, motivo: Optional[str] = None
):
    """Valida e executa transição de estado."""
    atual = StatusCampanha(estado_atual)
    permitidos = TRANSICOES_VALIDAS.get(atual, [])
    if estado_novo not in permitidos:
        raise HTTPException(
            status_code=422,
            detail=f"Transição inválida: '{atual.value}' → '{estado_novo.value}'. "
                   f"Permitidos: {[e.value for e in permitidos]}"
        )

    client = get_client()
    hist_id = f"hist_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"

    # Update status
    client.execute_insert(
        f"UPDATE {TABLE_CAMPANHA} SET status = ?, atualizado_em = current_timestamp() "
        f"WHERE campanha_id = ?",
        (estado_novo.value, campanha_id)
    )

    # Registra histórico
    client.execute_insert(
        f"INSERT INTO {CATALOG}.{SCHEMA_ENG}.campanha_historico_estado "
        f"(hist_id, campanha_id, estado_anterior, estado_novo, motivo, alterado_por, alterado_em) "
        f"VALUES (?, ?, ?, ?, ?, ?, current_timestamp())",
        (hist_id, campanha_id, atual.value, estado_novo.value, motivo, usuario)
    )

    return estado_novo.value


# --- GET /api/campanhas ---
@router.get("")
async def listar_campanhas(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_user_or_raise),
):
    """Lista campanhas com filtros e paginação."""
    client = get_client()
    offset = (page - 1) * size

    where = "WHERE 1=1"
    params = []
    if status:
        where += " AND status = ?"
        params.append(status)

    # Count
    total_row = client.fetch_one(
        f"SELECT COUNT(*) FROM {TABLE_CAMPANHA} {where}", tuple(params)
    )
    total = total_row[0] if total_row else 0

    # Data
    rows = client.fetch_all(
        f"SELECT campanha_id, campanha_codigo, nome, descricao, objetivo, status, "
        f"owner, area_responsavel, vigencia_inicio, vigencia_fim, "
        f"limite_envios, envios_realizados, versao_atual, criado_em, atualizado_em "
        f"FROM {TABLE_CAMPANHA} {where} "
        f"ORDER BY atualizado_em DESC LIMIT ? OFFSET ?",
        tuple(params + [size, offset])
    )

    campanhas = []
    for r in rows:
        campanhas.append({
            "campanha_id": r[0], "campanha_codigo": r[1], "nome": r[2],
            "descricao": r[3], "objetivo": r[4], "status": r[5],
            "owner": r[6], "area_responsavel": r[7],
            "vigencia_inicio": r[8], "vigencia_fim": r[9],
            "limite_envios": r[10], "envios_realizados": r[11],
            "versao_atual": r[12], "criado_em": r[13], "atualizado_em": r[14],
        })

    return {
        "data": campanhas,
        "meta": {"total": total, "page": page, "size": size, "pages": (total + size - 1) // size}
    }


# --- GET /api/campanhas/{id} ---
@router.get("/{campanha_id}")
async def detalhe_campanha(campanha_id: str, user: dict = Depends(get_user_or_raise)):
    """Detalhe da campanha + jornadas vinculadas."""
    client = get_client()
    row = client.fetch_one(
        f"SELECT * FROM {TABLE_CAMPANHA} WHERE campanha_id = ?", (campanha_id,)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")

    # Jornadas vinculadas
    jornadas = client.fetch_all(
        f"SELECT j.jornada_id, j.jornada_codigo, j.nome, j.status "
        f"FROM {CATALOG}.{SCHEMA_ENG}.campanha_jornada cj "
        f"JOIN {CATALOG}.{SCHEMA_ENG}.jornada j ON j.jornada_id = cj.jornada_id "
        f"WHERE cj.campanha_id = ? AND cj.ativo = true ORDER BY cj.ordem",
        (campanha_id,)
    )

    # Monta response (row é lista posicional — mapear por índice ou usar dict)
    # Para simplificar, retorna dict genérico
    return {
        "data": {
            "campanha_id": row[0], "campanha_codigo": row[1], "nome": row[2],
            "descricao": row[3], "objetivo": row[4], "tags": row[5],
            "resumo": row[6], "objetivo_negocio": row[7], "observacoes": row[8],
            "owner": row[9], "area_responsavel": row[10], "email_contato": row[11],
            "criado_por": row[12], "criado_em": row[13], "status": row[14],
            "vigencia_inicio": row[15], "vigencia_fim": row[16],
            "aprovado_por": row[17], "aprovado_em": row[18],
            "limite_envios": row[19], "alerta_pct_limite": row[20],
            "envios_realizados": row[21], "versao_atual": row[22],
            "atualizado_em": row[23],
            "jornadas": [{"jornada_id": j[0], "jornada_codigo": j[1], "nome": j[2], "status": j[3]} for j in jornadas],
        }
    }


# --- POST /api/campanhas ---
@router.post("", status_code=201)
async def criar_campanha(payload: CampanhaCreate, user: dict = Depends(get_user_or_raise)):
    """Cria campanha em status RASCUNHO + versão 1."""
    client = get_client()
    campanha_id = f"cam_{uuid.uuid4().hex[:12]}"
    campanha_codigo = _gerar_codigo(payload.nome)
    tags_json = json.dumps(payload.tags) if payload.tags else None

    # INSERT campanha
    client.execute_insert(
        f"INSERT INTO {TABLE_CAMPANHA} "
        f"(campanha_id, campanha_codigo, nome, descricao, objetivo, tags, "
        f"resumo, objetivo_negocio, observacoes, owner, area_responsavel, "
        f"email_contato, criado_por, criado_em, status, vigencia_inicio, vigencia_fim, "
        f"versao_atual, atualizado_em) "
        f"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, current_timestamp(), "
        f"'rascunho', ?, ?, 1, current_timestamp())",
        (
            campanha_id, campanha_codigo, payload.nome, payload.descricao,
            payload.objetivo, tags_json, payload.resumo, payload.objetivo_negocio,
            payload.observacoes, user["usuario_id"], payload.area_responsavel,
            payload.email_contato, user["usuario_id"],
            payload.vigencia_inicio, payload.vigencia_fim,
        )
    )

    # INSERT versão 1
    snapshot = payload.model_dump(mode="json")
    client.execute_insert(
        f"INSERT INTO {CATALOG}.{SCHEMA_ENG}.campanha_versao "
        f"(campanha_id, versao, snapshot_json, alterado_por, alterado_em, motivo) "
        f"VALUES (?, 1, ?, ?, current_timestamp(), 'Criação')",
        (campanha_id, json.dumps(snapshot), user["usuario_id"])
    )

    logger.info(f"✓ Campanha criada: {campanha_codigo} ({campanha_id})")
    return {"data": {"campanha_id": campanha_id, "campanha_codigo": campanha_codigo}}


# --- PUT /api/campanhas/{id} ---
@router.put("/{campanha_id}")
async def editar_campanha(
    campanha_id: str, payload: CampanhaUpdate, user: dict = Depends(get_user_or_raise)
):
    """Edita campanha e cria nova versão."""
    client = get_client()
    row = client.fetch_one(
        f"SELECT status, versao_atual FROM {TABLE_CAMPANHA} WHERE campanha_id = ?",
        (campanha_id,)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")

    status_atual = row[0]
    if status_atual not in ("rascunho", "em_aprovacao"):
        raise HTTPException(status_code=422, detail=f"Não editável no status '{status_atual}'")

    versao_atual = row[1]
    nova_versao = versao_atual + 1

    # Build SET clause dinâmico (só campos enviados)
    updates = []
    params = []
    dados = payload.model_dump(exclude_none=True, exclude={"motivo"})
    for campo, valor in dados.items():
        if campo == "tags":
            updates.append(f"tags = ?")
            params.append(json.dumps(valor))
        else:
            updates.append(f"{campo} = ?")
            params.append(valor)

    if updates:
        updates.append("versao_atual = ?")
        params.append(nova_versao)
        updates.append("atualizado_em = current_timestamp()")
        params.append(campanha_id)
        client.execute_insert(
            f"UPDATE {TABLE_CAMPANHA} SET {', '.join(updates)} WHERE campanha_id = ?",
            tuple(params)
        )

    # Nova versão
    snapshot = payload.model_dump(mode="json", exclude_none=True)
    client.execute_insert(
        f"INSERT INTO {CATALOG}.{SCHEMA_ENG}.campanha_versao "
        f"(campanha_id, versao, snapshot_json, alterado_por, alterado_em, motivo) "
        f"VALUES (?, ?, ?, ?, current_timestamp(), ?)",
        (campanha_id, nova_versao, json.dumps(snapshot), user["usuario_id"], payload.motivo)
    )

    return {"data": {"campanha_id": campanha_id, "versao": nova_versao}}


# --- POST /api/campanhas/{id}/aprovar ---
@router.post("/{campanha_id}/aprovar")
async def aprovar_campanha(campanha_id: str, user: dict = Depends(require_perfil(["admin"]))):
    """Transita para APROVADA (requer perfil admin)."""
    client = get_client()
    row = client.fetch_one(
        f"SELECT status FROM {TABLE_CAMPANHA} WHERE campanha_id = ?", (campanha_id,)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")

    # Aceita aprovar de RASCUNHO ou EM_APROVACAO
    if row[0] == StatusCampanha.RASCUNHO.value:
        _transitar_estado(campanha_id, row[0], StatusCampanha.EM_APROVACAO, user["usuario_id"])
        row = [StatusCampanha.EM_APROVACAO.value]

    _transitar_estado(campanha_id, row[0], StatusCampanha.APROVADA, user["usuario_id"], "Aprovada")

    # Marca aprovador
    client.execute_insert(
        f"UPDATE {TABLE_CAMPANHA} SET aprovado_por = ?, aprovado_em = current_timestamp() "
        f"WHERE campanha_id = ?",
        (user["usuario_id"], campanha_id)
    )

    return {"data": {"status": "aprovada"}}


# --- POST /api/campanhas/{id}/ativar ---
@router.post("/{campanha_id}/ativar")
async def ativar_campanha(campanha_id: str, user: dict = Depends(require_perfil(["admin"]))):
    """Transita para ATIVA. Valida: todas peças das jornadas devem estar aprovadas."""
    client = get_client()
    row = client.fetch_one(
        f"SELECT status FROM {TABLE_CAMPANHA} WHERE campanha_id = ?", (campanha_id,)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")

    # Valida peças aprovadas (via jornadas vinculadas)
    pecas_nao_aprovadas = client.fetch_all(
        f"SELECT p.peca_id, p.nome, p.status_aprovacao "
        f"FROM {CATALOG}.{SCHEMA_ENG}.campanha_jornada cj "
        f"JOIN {CATALOG}.{SCHEMA_ENG}.jornada j ON j.jornada_id = cj.jornada_id "
        f"JOIN {CATALOG}.{SCHEMA_ENG}.peca p ON p.peca_id IN ("
        f"  SELECT DISTINCT peca_id FROM {CATALOG}.{SCHEMA_ENG}.fila_disparo "
        f"  WHERE jornada_id = j.jornada_id"
        f") "
        f"WHERE cj.campanha_id = ? AND cj.ativo = true "
        f"AND p.status_aprovacao != 'aprovada'",
        (campanha_id,)
    )

    if pecas_nao_aprovadas:
        nomes = [r[1] for r in pecas_nao_aprovadas]
        raise HTTPException(
            status_code=422,
            detail=f"Peças não aprovadas: {nomes}. Todas as peças devem estar aprovadas para ativar."
        )

    _transitar_estado(campanha_id, row[0], StatusCampanha.ATIVA, user["usuario_id"], "Ativada")

    # Evento: campanha_ativada
    _emitir_evento(client, campanha_id, "campanha_ativada", user["usuario_id"])

    return {"data": {"status": "ativa"}}


# --- POST /api/campanhas/{id}/pausar ---
@router.post("/{campanha_id}/pausar")
async def pausar_campanha(campanha_id: str, user: dict = Depends(get_user_or_raise)):
    """Transita para PAUSADA."""
    client = get_client()
    row = client.fetch_one(
        f"SELECT status FROM {TABLE_CAMPANHA} WHERE campanha_id = ?", (campanha_id,)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")

    _transitar_estado(campanha_id, row[0], StatusCampanha.PAUSADA, user["usuario_id"], "Pausada")
    return {"data": {"status": "pausada"}}


# --- POST /api/campanhas/{id}/encerrar ---
@router.post("/{campanha_id}/encerrar")
async def encerrar_campanha(campanha_id: str, user: dict = Depends(get_user_or_raise)):
    """Transita para ENCERRADA."""
    client = get_client()
    row = client.fetch_one(
        f"SELECT status FROM {TABLE_CAMPANHA} WHERE campanha_id = ?", (campanha_id,)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")

    _transitar_estado(campanha_id, row[0], StatusCampanha.ENCERRADA, user["usuario_id"], "Encerrada")
    return {"data": {"status": "encerrada"}}


# --- PUT /api/campanhas/{id}/limite ---
@router.put("/{campanha_id}/limite")
async def configurar_limite(
    campanha_id: str, payload: LimiteUpdate, user: dict = Depends(get_user_or_raise)
):
    """Configura limite de envios e alerta."""
    client = get_client()
    row = client.fetch_one(
        f"SELECT campanha_id FROM {TABLE_CAMPANHA} WHERE campanha_id = ?", (campanha_id,)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")

    client.execute_insert(
        f"UPDATE {TABLE_CAMPANHA} SET limite_envios = ?, alerta_pct_limite = ?, "
        f"atualizado_em = current_timestamp() WHERE campanha_id = ?",
        (payload.limite_envios, payload.alerta_pct_limite, campanha_id)
    )

    return {"data": {"limite_envios": payload.limite_envios, "alerta_pct_limite": payload.alerta_pct_limite}}


# --- Helper: emitir evento ---
def _emitir_evento(client, campanha_id: str, tipo_evento: str, usuario: str):
    """Emite evento no barramento (disparo_eventos)."""
    evento_id = f"evt_{uuid.uuid4().hex[:12]}"
    try:
        client.execute_insert(
            f"INSERT INTO {CATALOG}.eventos.disparo_eventos "
            f"(evento_id, tipo_evento, entidade_tipo, entidade_id, "
            f"payload_json, emitido_por, emitido_em, processado) "
            f"VALUES (?, ?, 'campanha', ?, ?, ?, current_timestamp(), false)",
            (evento_id, tipo_evento, campanha_id,
             json.dumps({"campanha_id": campanha_id}), usuario)
        )
    except Exception as e:
        # Não bloqueia a operação principal se o barramento falhar
        logger.warning(f"Evento não emitido ({tipo_evento}): {e}")
