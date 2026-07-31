"""
Endpoints admin de governança de catálogo (S1-BACK-11).
Apenas admin do S1 tem acesso.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from src.services.metadata_admin_service import MetadataAdminService
from src.models.dto.metadata_admin_dto import FlagUpdateDTO, StatusUpdateDTO
from src.core.security import require_perfil

router = APIRouter(prefix="/metadata/admin", tags=["metadata_admin"])


@router.get("/campos")
async def listar_campos_admin(
    tema: Optional[str] = Query(None, description="Filtrar por tema"),
    sistema: Optional[str] = Query(None, description="s2 ou s3"),
    status: Optional[str] = Query(None, description="ativo ou inativo"),
    busca: Optional[str] = Query(None, description="Busca textual"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    user: dict = Depends(require_perfil(["admin"])),
):
    """
    Lista todas as características (inclui inativas) com filtros.
    Apenas admin.
    """
    service = MetadataAdminService()
    return service.listar_campos(
        tema=tema, sistema=sistema, status=status, busca=busca,
        page=page, size=size,
    )


@router.get("/campos/{caracteristica_id}")
async def obter_campo_admin(
    caracteristica_id: str,
    user: dict = Depends(require_perfil(["admin"])),
):
    """
    Detalhe completo de uma característica (inclui flags).
    Apenas admin.
    """
    service = MetadataAdminService()
    dados = service.obter_campo(caracteristica_id)
    if not dados:
        raise HTTPException(status_code=404, detail="Característica não encontrada")
    return dados


@router.put("/campos/{caracteristica_id}/flags")
async def atualizar_flags(
    caracteristica_id: str,
    payload: FlagUpdateDTO,
    user: dict = Depends(require_perfil(["admin"])),
):
    """
    Atualiza flags (S2/S3/bloco) e grava histórico.
    Apenas admin.
    """
    service = MetadataAdminService()
    try:
        resultado = service.atualizar_flags(
            caracteristica_id=caracteristica_id,
            flags=payload,
            alterado_por=user["usuario_id"],
        )
        return resultado
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.put("/campos/{caracteristica_id}/status")
async def atualizar_status(
    caracteristica_id: str,
    payload: StatusUpdateDTO,
    user: dict = Depends(require_perfil(["admin"])),
):
    """
    Ativa/desativa globalmente uma característica e grava histórico.
    Apenas admin.
    """
    service = MetadataAdminService()
    try:
        resultado = service.atualizar_status(
            caracteristica_id=caracteristica_id,
            status=payload,
            alterado_por=user["usuario_id"],
        )
        return resultado
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/historico")
async def listar_historico(
    caracteristica_id: Optional[str] = Query(None),
    sistema_alvo: Optional[str] = Query(None),
    acao: Optional[str] = Query(None),
    alterado_por: Optional[str] = Query(None),
    de: Optional[str] = Query(None, description="Data início (ISO)"),
    ate: Optional[str] = Query(None, description="Data fim (ISO)"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    user: dict = Depends(require_perfil(["admin"])),
):
    """
    Lista histórico de governança (trilha geral) com filtros.
    Apenas admin.
    """
    service = MetadataAdminService()
    return service.listar_historico(
        caracteristica_id=caracteristica_id,
        sistema_alvo=sistema_alvo,
        acao=acao,
        alterado_por=alterado_por,
        de=de,
        ate=ate,
        page=page,
        size=size,
    )


@router.get("/campos/{caracteristica_id}/historico")
async def listar_historico_por_campo(
    caracteristica_id: str,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    user: dict = Depends(require_perfil(["admin"])),
):
    """
    Lista histórico específico de uma característica.
    Apenas admin.
    """
    service = MetadataAdminService()
    return service.listar_historico(
        caracteristica_id=caracteristica_id,
        page=page,
        size=size,
    )