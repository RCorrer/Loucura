"""Segurança do EngagementHub (S3). OBO + RBAC (sistema='engagement')."""

import os
import logging
from fastapi import HTTPException, Depends, Request
from typing import Optional, List

from src.db.databricks_client import get_client

logger = logging.getLogger(__name__)

SISTEMA = "engagement"


async def get_current_user(request: Request) -> Optional[dict]:
    """Obtém usuário via OBO (X-Forwarded-Email) e valida perfil."""
    user_email = request.headers.get("X-Forwarded-Email")
    if not user_email:
        user_email = os.getenv("DEV_USER")
        if user_email:
            logger.info(f"\ud83d\udd27 Modo dev: DEV_USER={user_email}")

    if not user_email:
        return None

    try:
        client = get_client()
        row = client.fetch_one(
            "SELECT perfil FROM plataforma.governanca.usuarios_perfil "
            "WHERE usuario_id = ? AND sistema = ? AND ativo = true",
            (user_email, SISTEMA)
        )
        if row:
            return {"usuario_id": user_email, "perfil": row[0]}
        else:
            logger.warning(f"\u26a0\ufe0f Usuário {user_email} não tem perfil no sistema '{SISTEMA}'")
            return None
    except Exception as e:
        logger.error(f"\u274c Erro RBAC: {e}")
        if os.getenv("ENV") == "production":
            return None
        return {"usuario_id": user_email, "perfil": "admin"}


def require_perfil(perfis_permitidos: Optional[List[str]] = None):
    """Factory: Depends(require_perfil(["admin"]))"""
    if perfis_permitidos is None:
        perfis_permitidos = ["admin", "analista"]

    async def dependency(user: dict = Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=401, detail="Não autenticado")
        if user["perfil"] not in perfis_permitidos:
            raise HTTPException(
                status_code=403,
                detail=f"Perfil '{user['perfil']}' não permitido. Requer: {perfis_permitidos}"
            )
        return user

    return dependency


async def get_user_or_raise(request: Request) -> dict:
    """Obtém usuário ou levanta 401."""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Não autenticado")
    return user
