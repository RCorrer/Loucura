"""
Endpoint de estimativa de público.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from src.models.regras import RegrasJson
from src.services.estimativa_service import EstimativaService
from src.core.security import require_perfil
import logging
import json

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/estimativa", tags=["estimativa"])


@router.post("/preview")
async def preview_estimativa(
    request: Request,
    regras: RegrasJson,
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    """
    Calcula a estimativa de público para as regras fornecidas.
    Retorna apenas números (nunca lista de CPFs).
    """
    # Log detalhado do payload recebido
    try:
        body = await request.body()
        logger.info(f"🔍 PREVIEW PAYLOAD RAW: {body.decode('utf-8')}")
    except:
        pass
    
    logger.info(f"🔍 PREVIEW PARSED: publico_base={regras.publico_base}, inclusao={regras.inclusao}, exclusao={regras.exclusao}")
    
    service = EstimativaService()
    try:
        resultado = service.calcular_estimativa(regras)
        return resultado
    except ValueError as e:
        logger.error(f"❌ PREVIEW ValueError: {str(e)}")
        raise HTTPException(status_code=422, detail={"erros": str(e).split(": ")[1] if ": " in str(e) else str(e)})
    except Exception as e:
        logger.error(f"❌ PREVIEW Exception: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao calcular estimativa: {str(e)}")