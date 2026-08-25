"""API de Peças (S3-BACK-03): CRUD + Aprovação + Preview + Variáveis + Assets."""

import uuid
import json
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from src.db.databricks_client import get_client
from src.core.security import get_user_or_raise, require_perfil
from src.core.config import CATALOG, SCHEMA_ENG, TABLE_PECA
from src.core.render_engine import extrair_variaveis, render_preview
from src.models.peca import (
    PecaCreate, PecaUpdate, AprovarPayload, ReprovarPayload, PreviewPayload,
    StatusAprovacao, TRANSICOES_APROVACAO,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _gerar_codigo(canal: str) -> str:
    hex6 = uuid.uuid4().hex[:6].upper()
    return f"PEC-{canal.upper()}-{hex6}"


# --- GET /api/pecas/variaveis (ANTES de /{peca_id} para evitar conflito) ---
@router.get("/variaveis")
async def listar_variaveis(user: dict = Depends(get_user_or_raise)):
    """Catálogo de variáveis disponíveis para personalização (contrato S1)."""
    client = get_client()
    rows = client.fetch_all(
        f"SELECT campo_id, campo_label, tipo_dado, descricao "
        f"FROM {CATALOG}.{SCHEMA_ENG}.variaveis_disponiveis"
    )
    variaveis = [{
        "campo_id": r[0], "campo_label": r[1], "tipo_dado": r[2], "descricao": r[3]
    } for r in rows]
    return {"data": variaveis}


# --- GET /api/pecas ---
@router.get("")
async def listar_pecas(
    canal: Optional[str] = None,
    status_aprovacao: Optional[str] = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_user_or_raise),
):
    client = get_client()
    offset = (page - 1) * size
    where = "WHERE 1=1"
    params = []
    if canal:
        where += " AND canal = ?"
        params.append(canal)
    if status_aprovacao:
        where += " AND status_aprovacao = ?"
        params.append(status_aprovacao)

    total_row = client.fetch_one(f"SELECT COUNT(*) FROM {TABLE_PECA} {where}", tuple(params))
    total = total_row[0] if total_row else 0

    rows = client.fetch_all(
        f"SELECT peca_id, peca_codigo, nome, descricao, canal, status_aprovacao, "
        f"owner, area_responsavel, versao_atual, criado_em, atualizado_em "
        f"FROM {TABLE_PECA} {where} ORDER BY atualizado_em DESC LIMIT ? OFFSET ?",
        tuple(params + [size, offset])
    )

    pecas = [{
        "peca_id": r[0], "peca_codigo": r[1], "nome": r[2], "descricao": r[3],
        "canal": r[4], "status_aprovacao": r[5], "owner": r[6],
        "area_responsavel": r[7], "versao_atual": r[8],
        "criado_em": r[9], "atualizado_em": r[10],
    } for r in rows]

    return {"data": pecas, "meta": {"total": total, "page": page, "size": size,
            "pages": (total + size - 1) // size if total > 0 else 0}}


# --- GET /api/pecas/{id} ---
@router.get("/{peca_id}")
async def detalhe_peca(peca_id: str, user: dict = Depends(get_user_or_raise)):
    client = get_client()
    COLS = ("peca_id, peca_codigo, nome, descricao, canal, tags, conteudo_json, "
            "html_renderizado, assunto, template_meta_id, variaveis_usadas, "
            "status_aprovacao, aprovado_por, aprovado_em, motivo_reprovacao, "
            "criado_por, criado_em, owner, area_responsavel, versao_atual, atualizado_em")
    row = client.fetch_one(f"SELECT {COLS} FROM {TABLE_PECA} WHERE peca_id = ?", (peca_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Peça não encontrada")

    # Versões
    versoes = client.fetch_all(
        f"SELECT versao, alterado_por, alterado_em, motivo "
        f"FROM {CATALOG}.{SCHEMA_ENG}.peca_versao WHERE peca_id = ? ORDER BY versao DESC",
        (peca_id,)
    )
    # Aprovações
    aprovacoes = client.fetch_all(
        f"SELECT etapa, status, aprovado_por, aprovado_em, comentario "
        f"FROM {CATALOG}.{SCHEMA_ENG}.peca_aprovacao WHERE peca_id = ? ORDER BY aprovado_em DESC",
        (peca_id,)
    )

    tags_raw = row[5]
    tags = json.loads(tags_raw) if isinstance(tags_raw, str) and tags_raw else tags_raw
    vars_raw = row[10]
    variaveis = json.loads(vars_raw) if isinstance(vars_raw, str) and vars_raw else vars_raw

    return {"data": {
        "peca_id": row[0], "peca_codigo": row[1], "nome": row[2], "descricao": row[3],
        "canal": row[4], "tags": tags, "conteudo_json": row[6],
        "html_renderizado": row[7], "assunto": row[8], "template_meta_id": row[9],
        "variaveis_usadas": variaveis, "status_aprovacao": row[11],
        "aprovado_por": row[12], "aprovado_em": row[13], "motivo_reprovacao": row[14],
        "criado_por": row[15], "criado_em": row[16], "owner": row[17],
        "area_responsavel": row[18], "versao_atual": row[19], "atualizado_em": row[20],
        "versoes": [{"versao": v[0], "alterado_por": v[1], "alterado_em": v[2], "motivo": v[3]} for v in versoes],
        "aprovacoes": [{"etapa": a[0], "status": a[1], "aprovado_por": a[2], "aprovado_em": a[3], "comentario": a[4]} for a in aprovacoes],
    }}


# --- POST /api/pecas ---
@router.post("", status_code=201)
async def criar_peca(payload: PecaCreate, user: dict = Depends(get_user_or_raise)):
    client = get_client()
    peca_id = f"pec_{uuid.uuid4().hex[:12]}"
    peca_codigo = _gerar_codigo(payload.canal.value)
    tags_json = json.dumps(payload.tags) if payload.tags else None
    variaveis = extrair_variaveis(payload.conteudo_json)
    variaveis_json = json.dumps(variaveis)

    # Valida template WhatsApp se canal=whatsapp
    if payload.canal.value == "whatsapp" and payload.template_meta_id:
        tmpl = client.fetch_one(
            f"SELECT status_meta FROM {CATALOG}.{SCHEMA_ENG}.whatsapp_templates "
            f"WHERE template_meta_id = ?", (payload.template_meta_id,)
        )
        if not tmpl:
            raise HTTPException(status_code=422, detail=f"Template WhatsApp '{payload.template_meta_id}' não encontrado")

    client.execute_insert(
        f"INSERT INTO {TABLE_PECA} "
        f"(peca_id, peca_codigo, nome, descricao, canal, tags, conteudo_json, "
        f"html_renderizado, assunto, template_meta_id, variaveis_usadas, "
        f"status_aprovacao, criado_por, criado_em, owner, area_responsavel, "
        f"versao_atual, atualizado_em) "
        f"VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, 'rascunho', ?, "
        f"current_timestamp(), ?, ?, 1, current_timestamp())",
        (peca_id, peca_codigo, payload.nome, payload.descricao,
         payload.canal.value, tags_json, payload.conteudo_json,
         payload.assunto, payload.template_meta_id, variaveis_json,
         user["usuario_id"], user["usuario_id"], payload.area_responsavel)
    )

    # Versão 1
    client.execute_insert(
        f"INSERT INTO {CATALOG}.{SCHEMA_ENG}.peca_versao "
        f"(peca_id, versao, conteudo_json, html_renderizado, alterado_por, alterado_em, motivo) "
        f"VALUES (?, 1, ?, NULL, ?, current_timestamp(), 'Criação')",
        (peca_id, payload.conteudo_json, user["usuario_id"])
    )

    return {"data": {"peca_id": peca_id, "peca_codigo": peca_codigo, "variaveis_usadas": variaveis}}


# --- PUT /api/pecas/{id} ---
@router.put("/{peca_id}")
async def editar_peca(peca_id: str, payload: PecaUpdate, user: dict = Depends(get_user_or_raise)):
    client = get_client()
    row = client.fetch_one(
        f"SELECT status_aprovacao, versao_atual FROM {TABLE_PECA} WHERE peca_id = ?", (peca_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Peça não encontrada")
    if row[0] not in ("rascunho", "reprovada"):
        raise HTTPException(status_code=422, detail=f"Não editável no status '{row[0]}'")

    nova_versao = row[1] + 1
    dados = payload.model_dump(exclude_none=True, exclude={"motivo"})
    if not dados:
        raise HTTPException(status_code=422, detail="Nenhum campo para atualizar")
    updates, params = [], []

    for campo, valor in dados.items():
        if campo == "tags":
            updates.append("tags = ?")
            params.append(json.dumps(valor))
        else:
            updates.append(f"{campo} = ?")
            params.append(valor)

    # Re-extrair variáveis se conteudo mudou
    if "conteudo_json" in dados:
        variaveis = extrair_variaveis(dados["conteudo_json"])
        updates.append("variaveis_usadas = ?")
        params.append(json.dumps(variaveis))

    if updates:
        updates.append("versao_atual = ?")
        params.append(nova_versao)
        updates.append("atualizado_em = current_timestamp()")
        params.append(peca_id)
        client.execute_insert(
            f"UPDATE {TABLE_PECA} SET {', '.join(updates)} WHERE peca_id = ?", tuple(params))

    # Nova versão
    conteudo_snap = dados.get("conteudo_json", None)
    client.execute_insert(
        f"INSERT INTO {CATALOG}.{SCHEMA_ENG}.peca_versao "
        f"(peca_id, versao, conteudo_json, html_renderizado, alterado_por, alterado_em, motivo) "
        f"VALUES (?, ?, ?, NULL, ?, current_timestamp(), ?)",
        (peca_id, nova_versao, conteudo_snap, user["usuario_id"], payload.motivo)
    )

    return {"data": {"peca_id": peca_id, "versao": nova_versao}}


# --- POST /api/pecas/{id}/submeter ---
@router.post("/{peca_id}/submeter")
async def submeter_peca(peca_id: str, user: dict = Depends(get_user_or_raise)):
    client = get_client()
    row = client.fetch_one(f"SELECT status_aprovacao FROM {TABLE_PECA} WHERE peca_id = ?", (peca_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Peça não encontrada")
    if row[0] != "rascunho":
        raise HTTPException(status_code=422, detail=f"Só pode submeter de 'rascunho', atual='{row[0]}'")

    client.execute_insert(
        f"UPDATE {TABLE_PECA} SET status_aprovacao = 'em_aprovacao', atualizado_em = current_timestamp() "
        f"WHERE peca_id = ?", (peca_id,))

    return {"data": {"status_aprovacao": "em_aprovacao"}}


# --- POST /api/pecas/{id}/aprovar ---
@router.post("/{peca_id}/aprovar")
async def aprovar_peca(
    peca_id: str, payload: AprovarPayload, user: dict = Depends(require_perfil(["admin"]))
):
    client = get_client()
    row = client.fetch_one(f"SELECT status_aprovacao, versao_atual FROM {TABLE_PECA} WHERE peca_id = ?", (peca_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Peça não encontrada")
    if row[0] != "em_aprovacao":
        raise HTTPException(status_code=422, detail=f"Só pode aprovar em 'em_aprovacao', atual='{row[0]}'")

    aprov_id = f"apr_{uuid.uuid4().hex[:8]}"
    client.execute_insert(
        f"INSERT INTO {CATALOG}.{SCHEMA_ENG}.peca_aprovacao "
        f"(aprovacao_id, peca_id, versao, etapa, perfil_aprovador, status, aprovado_por, aprovado_em, comentario) "
        f"VALUES (?, ?, ?, ?, 'admin', 'aprovado', ?, current_timestamp(), ?)",
        (aprov_id, peca_id, row[1], payload.etapa, user["usuario_id"], payload.comentario)
    )
    client.execute_insert(
        f"UPDATE {TABLE_PECA} SET status_aprovacao = 'aprovada', aprovado_por = ?, "
        f"aprovado_em = current_timestamp(), atualizado_em = current_timestamp() WHERE peca_id = ?",
        (user["usuario_id"], peca_id)
    )

    return {"data": {"status_aprovacao": "aprovada", "etapa": payload.etapa}}


# --- POST /api/pecas/{id}/reprovar ---
@router.post("/{peca_id}/reprovar")
async def reprovar_peca(
    peca_id: str, payload: ReprovarPayload, user: dict = Depends(require_perfil(["admin"]))
):
    client = get_client()
    row = client.fetch_one(f"SELECT status_aprovacao, versao_atual FROM {TABLE_PECA} WHERE peca_id = ?", (peca_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Peça não encontrada")
    if row[0] != "em_aprovacao":
        raise HTTPException(status_code=422, detail=f"Só pode reprovar em 'em_aprovacao', atual='{row[0]}'")

    aprov_id = f"apr_{uuid.uuid4().hex[:8]}"
    client.execute_insert(
        f"INSERT INTO {CATALOG}.{SCHEMA_ENG}.peca_aprovacao "
        f"(aprovacao_id, peca_id, versao, etapa, perfil_aprovador, status, aprovado_por, aprovado_em, comentario) "
        f"VALUES (?, ?, ?, ?, 'admin', 'reprovado', ?, current_timestamp(), ?)",
        (aprov_id, peca_id, row[1], payload.etapa, user["usuario_id"], payload.motivo)
    )
    client.execute_insert(
        f"UPDATE {TABLE_PECA} SET status_aprovacao = 'reprovada', motivo_reprovacao = ?, "
        f"atualizado_em = current_timestamp() WHERE peca_id = ?",
        (payload.motivo, peca_id)
    )

    return {"data": {"status_aprovacao": "reprovada", "motivo": payload.motivo}}


# --- POST /api/pecas/{id}/preview ---
@router.post("/{peca_id}/preview")
async def preview_peca(peca_id: str, payload: PreviewPayload, user: dict = Depends(get_user_or_raise)):
    client = get_client()
    row = client.fetch_one(
        f"SELECT conteudo_json, canal, assunto FROM {TABLE_PECA} WHERE peca_id = ?", (peca_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Peça não encontrada")

    resultado = render_preview(
        conteudo_json=row[0], canal=row[1],
        variaveis_override=payload.variaveis, assunto=row[2]
    )
    return {"data": resultado}




# --- POST /api/pecas/assets ---
@router.post("/assets", status_code=201)
async def upload_asset(user: dict = Depends(get_user_or_raise)):
    """Placeholder: upload de imagem para Volume UC.
    Implementação real requer multipart/form-data + SDK Volumes.
    """
    # TODO: Implementar upload real via Databricks SDK Volumes API
    # O arquivo binario vai para /Volumes/plataforma/engagement/assets/{uuid}.{ext}
    # E o registro vai para a tabela 'asset'
    raise HTTPException(
        status_code=501,
        detail="Upload de assets será implementado com Databricks SDK Volumes API (BACK-03 phase 2)"
    )
