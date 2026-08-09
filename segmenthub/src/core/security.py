"""
Módulo de segurança para SegmentHub (S1).
Gerencia autenticação (OBO via Databricks Apps) e autorização (RBAC).
"""

import os
import logging
from fastapi import HTTPException, Depends, Request
from typing import Optional, List

from src.db.databricks_client import get_client

logger = logging.getLogger(__name__)


async def get_current_user(request: Request) -> Optional[dict]:
    """
    Obtém o usuário atual a partir do cabeçalho OBO (Databricks Apps).
    - Em produção: lê X-Forwarded-Email e opcionalmente X-Forwarded-Access-Token.
    - Em desenvolvimento: usa DEV_USER.
    - Valida o perfil no banco via Service Principal (OAuth).
    - Fallback para admin apenas em desenvolvimento (ENV != production).
    """
    # 1. Identifica o usuário
    user_email = request.headers.get("X-Forwarded-Email")
    user_token = request.headers.get("X-Forwarded-Access-Token")  # opcional

    if not user_email:
        user_email = os.getenv("DEV_USER")
        if user_email:
            logger.info(f"🔧 Modo desenvolvimento: usando DEV_USER={user_email}")

    if not user_email:
        logger.warning("Nenhum usuário identificado na requisição")
        return None

    # 2. Valida o perfil no banco (usando Service Principal)
    try:
        client = get_client()
        # O cliente agora retorna listas (não dicionários)
        row = client.fetch_one(
            "SELECT perfil FROM plataforma.governanca.usuarios_perfil "
            "WHERE usuario_id = ? AND sistema = 'segmenthub' AND ativo = true",
            (user_email,)
        )

        if row:
            perfil = row[0]  # <-- acesso por índice (lista)
            logger.info(f"✅ Usuário {user_email} autenticado com perfil '{perfil}'")
            return {"usuario_id": user_email, "perfil": perfil}
        else:
            logger.warning(f"⚠️ Usuário {user_email} não encontrado ou inativo")
            return None

    except Exception as e:
        logger.error(f"❌ Erro ao buscar perfil do usuário {user_email}: {e}")

        # Fallback apenas para desenvolvimento (não em produção)
        if os.getenv("ENV") == "production":
            logger.warning("🚫 Fallback desativado em produção. Acesso negado.")
            return None

        logger.warning(f"🔧 Fallback: assumindo perfil 'admin' para {user_email} (modo desenvolvimento)")
        return {"usuario_id": user_email, "perfil": "admin"}


def require_perfil(perfis_permitidos: Optional[List[str]] = None):
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
                detail=f"Acesso negado. Perfil '{user['perfil']}' não permitido. Permitidos: {perfis_permitidos}"
            )
        return user

    return dependency


async def get_user_or_raise(request: Request) -> dict:
    """
    Obtém o usuário ou levanta 401 se não autenticado.
    Útil para endpoints que não precisam de autorização específica, apenas de autenticação.
    """
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Não autenticado")
    return user