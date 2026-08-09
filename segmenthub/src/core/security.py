"""
Módulo de segurança para SegmentHub (S1).
Gerencia autenticação e autorização (RBAC) via tabela governanca.usuarios_perfil.
"""

import os
import logging
from fastapi import HTTPException, Depends, Request
from typing import Optional, List

from src.db.databricks_client import get_client

logger = logging.getLogger(__name__)


async def get_current_user(request: Request) -> Optional[dict]:
    # Obtém o email do usuário do cabeçalho OBO (Databricks Apps)
    user_email = request.headers.get("X-Forwarded-Email")
    
    # Fallback para desenvolvimento local (variável de ambiente)
    if not user_email:
        user_email = os.getenv("DEV_USER")
    
    if not user_email:
        logger.warning("Nenhum usuário identificado na requisição")
        return None
    
    # Busca o perfil do usuário no banco usando o Service Principal (OAuth)
    try:
        client = get_client()
        row = client.fetch_one(
            "SELECT perfil FROM plataforma.governanca.usuarios_perfil WHERE usuario_id = :user_id AND sistema = 'segmenthub' AND ativo = true",
            {"user_id": user_email}
        )
        if row:
            return {"usuario_id": user_email, "perfil": row["perfil"]}
        else:
            logger.warning(f"Usuário {user_email} não encontrado ou inativo")
            return None
    except Exception as e:
        logger.error(f"Erro ao buscar perfil do usuário {user_email}: {e}")
        return None


def require_perfil(perfis_permitidos: List[str] = None):
    """
    Factory que retorna uma dependência para exigir perfis específicos.
    Uso: Depends(require_perfil(["admin"]))
    """
    if perfis_permitidos is None:
        perfis_permitidos = ["admin", "analista"]

    async def dependency(user: dict = Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=401, detail="Não autenticado")
        if user["perfil"] not in perfis_permitidos:
            raise HTTPException(
                status_code=403,
                detail=f"Acesso negado. Perfil '{user['perfil']}' não tem permissão. Permitidos: {perfis_permitidos}"
            )
        return user

    return dependency


async def get_user_or_raise(request: Request) -> dict:
    """Obtém o usuário ou levanta 401 se não autenticado."""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Não autenticado")
    return user