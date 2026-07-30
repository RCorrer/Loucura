"""
Endpoint de estimativa de público.
"""

from fastapi import APIRouter, Depends, HTTPException
from src.models.regras import RegrasJson
from src.services.estimativa_service import EstimativaService
from src.core.security import require_perfil

router = APIRouter(prefix="/estimativa", tags=["estimativa"])


@router.post("/preview")
async def preview_estimativa(
    regras: RegrasJson,
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    """
    Calcula a estimativa de público para as regras fornecidas.
    Retorna apenas números (nunca lista de CPFs).
    """
    service = EstimativaService()
    try:
        resultado = service.calcular_estimativa(regras)
        return resultado
    except ValueError as e:
        raise HTTPException(status_code=422, detail={"erros": str(e).split(": ")[1] if ": " in str(e) else str(e)})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao calcular estimativa: {str(e)}")