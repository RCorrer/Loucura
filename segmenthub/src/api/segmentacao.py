"""
Endpoints de segmentação para validação e geração de SQL.
"""

from fastapi import APIRouter, Depends, HTTPException
from src.models.regras import RegrasJson
from src.core.validator import RegraValidator
from src.core.query_engine import QueryEngine
from src.core.security import require_perfil

router = APIRouter(prefix="/segmentacao", tags=["segmentacao"])


@router.post("/validar-regras")
async def validar_regras(
    regras: RegrasJson,
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    """
    Valida regras JSON sem executar a query.
    Retorna lista de erros se inválido.
    """
    validator = RegraValidator()
    erros = validator.validar_regras(regras)
    if erros:
        return {"valido": False, "erros": erros}
    return {"valido": True, "mensagem": "Regras válidas"}


@router.post("/gerar-sql")
async def gerar_sql(
    regras: RegrasJson,
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    """
    Gera SQL parametrizado a partir das regras.
    Valida antes de gerar (alinhado com o planejamento).
    """
    # 1. Valida as regras
    validator = RegraValidator()
    erros = validator.validar_regras(regras)
    if erros:
        raise HTTPException(status_code=422, detail={"erros": erros})

    # 2. Gera o SQL
    try:
        engine = QueryEngine()
        sql, params = engine.generate_query(regras)
        return {
            "sql": sql,
            "params": params,
            "mensagem": "SQL gerado com sucesso"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))