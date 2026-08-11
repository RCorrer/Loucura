"""
Metadata Service - Endpoints públicos para catálogo de características e públicos.

ATENÇÃO: Estes endpoints NÃO expõem as flags usavel_em_visao360, usavel_em_peca, bloco_visao360.
A administração dessas flags é feita via /api/metadata/admin/* (S1-BACK-11).
O consumo dessas flags pelo S2/S3 é via GRANT SELECT direto na tabela (CONTRATOS 3.1).
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List

from src.services.metadata_service import MetadataService
from src.core.security import require_perfil
from src.models.dto.caracteristica_dto import (
    CaracteristicaDTO,
    CaracteristicaDetalheDTO,
    PublicoDTO,
    CaracteristicaEmUsoDTO,
)
from src.models.responses import RespostaLista, RespostaUnica
from src.exceptions.custom_exceptions import TemaNotFoundError, CampoNotFoundError

router = APIRouter(prefix="/metadata", tags=["metadata"])


@router.get("/temas", response_model=RespostaLista)
async def listar_temas(
    user: dict = Depends(require_perfil(["admin", "analista"])),
    service: MetadataService = Depends(),
):
    """
    Retorna a lista de temas disponíveis no catálogo.
    """
    data = service.listar_temas()
    return {
        "data": data,
        "meta": {
            "page": 1,
            "size": len(data),
            "total": len(data),
            "total_pages": 1,
        },
    }


@router.get("/temas-completos", response_model=RespostaLista)
async def listar_temas_completos(
    user: dict = Depends(require_perfil(["admin", "analista"])),
    service: MetadataService = Depends(),
):
    """
    Retorna todos os temas com seus campos em uma única chamada.
    Resolve o problema de N+1 queries no frontend.
    """
    data = service.listar_temas_com_campos()
    return {
        "data": data,
        "meta": {
            "page": 1,
            "size": len(data),
            "total": len(data),
            "total_pages": 1,
        },
    }


@router.get("/temas/{tema}/caracteristicas", response_model=RespostaLista[CaracteristicaDTO])
async def listar_caracteristicas_por_tema(
    tema: str,
    user: dict = Depends(require_perfil(["admin", "analista"])),
    service: MetadataService = Depends(),
):
    """
    Retorna a lista de características de um tema específico.
    """
    try:
        data = service.listar_campos_por_tema(tema)
        return {
            "data": data,
            "meta": {
                "page": 1,
                "size": len(data),
                "total": len(data),
                "total_pages": 1,
            },
        }
    except TemaNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/caracteristicas/{caracteristica_id}", response_model=RespostaUnica[CaracteristicaDetalheDTO])
async def obter_caracteristica(
    caracteristica_id: str,
    user: dict = Depends(require_perfil(["admin", "analista"])),
    service: MetadataService = Depends(),
):
    """
    Retorna detalhes de uma característica específica.
    """
    try:
        data = service.obter_campo(caracteristica_id)
        return {"data": data}
    except CampoNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/publicos", response_model=RespostaLista[PublicoDTO])
async def listar_publicos(
    user: dict = Depends(require_perfil(["admin", "analista"])),
    service: MetadataService = Depends(),
):
    """
    Retorna a lista de públicos-base disponíveis.
    """
    data = service.listar_publicos()
    return {
        "data": data,
        "meta": {
            "page": 1,
            "size": len(data),
            "total": len(data),
            "total_pages": 1,
        },
    }


@router.get("/caracteristicas-em-uso", response_model=RespostaLista[CaracteristicaEmUsoDTO])
async def listar_caracteristicas_em_uso(
    user: dict = Depends(require_perfil(["admin", "analista"])),
    service: MetadataService = Depends(),
):
    """
    Retorna características que estão em uso em segmentações ativas.
    """
    data = service.listar_campos_em_uso()
    return {
        "data": data,
        "meta": {
            "page": 1,
            "size": len(data),
            "total": len(data),
            "total_pages": 1,
        },
    }