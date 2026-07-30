"""
Endpoints para comentários e notificações (S1-BACK-08).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List

from src.services.comentario_service import ComentarioService
from src.core.security import require_perfil

# ============================================================
# Router de segmentações (comentários aninhados)
# ============================================================
router = APIRouter(prefix="/segmentacoes", tags=["comentarios"])


@router.get("/{seg_id}/comentarios", response_model=List[dict])
async def listar_comentarios(
    seg_id: str,
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    """
    Lista comentários de uma segmentação em thread aninhada.
    """
    service = ComentarioService()
    return service.listar_comentarios(seg_id)


@router.post("/{seg_id}/comentarios", response_model=dict)
async def criar_comentario(
    seg_id: str,
    payload: dict,  # {texto, tipo?, versao_referencia?, respondendo_a?, mencoes?}
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    """
    Cria um novo comentário em uma segmentação.
    Menções (@usuario) geram notificações.
    """
    service = ComentarioService()
    try:
        resultado = service.criar_comentario(
            seg_id=seg_id,
            texto=payload["texto"],
            autor=user["usuario_id"],
            tipo=payload.get("tipo", "geral"),
            versao_referencia=payload.get("versao_referencia"),
            respondendo_a=payload.get("respondendo_a"),
            mencoes=payload.get("mencoes"),
        )
        return resultado
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))


# ============================================================
# Router de comentários (edição)
# ============================================================
comentario_router = APIRouter(prefix="/comentarios", tags=["comentarios"])


@comentario_router.put("/{comentario_id}", response_model=dict)
async def editar_comentario(
    comentario_id: str,
    payload: dict,  # {texto?, resolvido?}
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    """
    Edita o texto ou marca como resolvido um comentário.
    """
    service = ComentarioService()
    try:
        service.editar_comentario(
            comentario_id,
            texto=payload.get("texto"),
            resolvido=payload.get("resolvido")
        )
        return {"mensagem": "Comentário atualizado com sucesso"}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================
# Router de notificações
# ============================================================
notificacao_router = APIRouter(prefix="/notificacoes", tags=["notificacoes"])


@notificacao_router.get("", response_model=List[dict])
async def listar_notificacoes(
    lida: Optional[bool] = Query(None, description="Filtrar por lida (true/false)"),
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    """
    Lista notificações do usuário autenticado.
    """
    service = ComentarioService()
    return service.listar_notificacoes(user["usuario_id"], lida)


@notificacao_router.put("/{notif_id}/lida", response_model=dict)
async def marcar_notificacao_lida(
    notif_id: str,
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    """
    Marca uma notificação como lida.
    """
    service = ComentarioService()
    if service.marcar_lida(notif_id):
        return {"mensagem": "Notificação marcada como lida"}
    raise HTTPException(status_code=404, detail="Notificação não encontrada")