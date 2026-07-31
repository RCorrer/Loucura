"""
Endpoints de saúde e overlap (S1-BACK-09).
"""

from fastapi import APIRouter, Depends, HTTPException
from src.services.saude_service import SaudeService
from src.core.security import require_perfil

router = APIRouter(prefix="/saude", tags=["saude"])


@router.get("")
async def dashboard(
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    """
    Retorna dashboard consolidado de saúde de todas as segmentações.
    """
    service = SaudeService()
    return service.dashboard()


@router.get("/{seg_id}")
async def detalhe_saude(
    seg_id: str,
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    """
    Retorna saúde detalhada de uma segmentação específica.
    """
    service = SaudeService()
    dados = service.detalhe_saude(seg_id)
    if not dados:
        raise HTTPException(status_code=404, detail="Dados de saúde não encontrados para esta segmentação")
    return dados


@router.get("/{seg_id}/overlap")
async def listar_overlaps(
    seg_id: str,
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    """
    Retorna sobreposições de um segmento com outros.
    """
    service = SaudeService()
    dados = service.listar_overlaps(seg_id)
    return {
        "seg_id": seg_id,
        "overlaps": dados
    }