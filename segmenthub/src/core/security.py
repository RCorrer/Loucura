import os
import logging
from fastapi import HTTPException, Depends, Request
from typing import Optional, List

from src.db.databricks_client import get_client

logger = logging.getLogger(__name__)


async def get_current_user(request: Request) -> Optional[dict]:
    """
    Obtém o usuário atual a partir do cabeçalho OBO (Databricks Apps).
    Retorna o perfil (validado no banco) e o token do usuário.
    """
    # 1. Extrai email e token do cabeçalho OBO
    user_email = request.headers.get("X-Forwarded-Email")
    user_token = request.headers.get("X-Forwarded-Access-Token")

    # Fallback para desenvolvimento local
    if not user_email:
        user_email = os.getenv("DEV_USER")
        if user_email:
            # Em desenvolvimento, usamos o token fixo do ambiente (DATABRICKS_TOKEN)
            user_token = os.getenv("DATABRICKS_TOKEN")

    if not user_email:
        logger.warning("Nenhum usuário identificado")
        return None

    # 2. Valida o perfil no banco usando o token do usuário (ou fallback)
    try:
        # Cria cliente com o token do usuário (OBO)
        client = get_client(user_token=user_token)
        row = client.fetch_one(
            "SELECT perfil FROM plataforma.governanca.usuarios_perfil "
            "WHERE usuario_id = :user_id AND sistema = 'segmenthub' AND ativo = true",
            (user_email,)  # placeholders posicionais
        )
        if row:
            logger.info(f"Usuário {user_email} autenticado com perfil {row['perfil']}")
            # Retorna o token junto com o perfil (para usar em outras chamadas, se necessário)
            return {"usuario_id": user_email, "perfil": row["perfil"], "token": user_token}
        else:
            logger.warning(f"Usuário {user_email} não encontrado ou inativo")
            return None
    except Exception as e:
        logger.error(f"Erro ao buscar perfil: {e}")
        # Fallback apenas para desenvolvimento (quando ENV != production)
        if os.getenv("ENV") == "production":
            return None
        logger.warning(f"Fallback: assumindo perfil 'admin' para {user_email} (modo desenvolvimento)")
        return {"usuario_id": user_email, "perfil": "admin", "token": user_token}


def require_perfil(perfis_permitidos: List[str] = None):
    if perfis_permitidos is None:
        perfis_permitidos = ["admin", "analista"]

    async def dependency(user: dict = Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=401, detail="Não autenticado")
        if user["perfil"] not in perfis_permitidos:
            raise HTTPException(
                status_code=403,
                detail=f"Acesso negado. Perfil '{user['perfil']}' não permitido. Permitidos: {perfis_permitidos}"
            )
        return user

    return dependency


async def get_user_or_raise(request: Request) -> dict:
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Não autenticado")
    return user