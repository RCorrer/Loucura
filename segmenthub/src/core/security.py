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
    """
    Obtém o usuário atual da requisição.
    - Em produção (Databricks Apps): lê o cabeçalho 'X-Databricks-User' (OBO).
    - Em desenvolvimento: usa a variável de ambiente DEV_USER.
    Retorna um dicionário com 'usuario_id' e 'perfil' ou None se não encontrado.
    """
    # 1. Tenta obter do cabeçalho (produção)
    user_id = request.headers.get("X-Databricks-User")
    
    # 2. Fallback para desenvolvimento
    if not user_id:
        user_id = os.getenv("DEV_USER")
        if not user_id:
            # Fallback padrão (útil para testes iniciais)
            logger.warning("DEV_USER não definido, usando 'admin' como fallback")
            user_id = "admin"
    
    # 3. Busca o perfil do usuário na tabela de governança
    try:
        client = get_client()
        row = client.fetch_one(
            """
            SELECT perfil
            FROM plataforma.governanca.usuarios_perfil
            WHERE usuario_id = :user_id
              AND sistema = 'segmenthub'
              AND ativo = true
            """,
            {"user_id": user_id}
        )
        if row:
            return {"usuario_id": user_id, "perfil": row["perfil"]}
        else:
            logger.warning(f"Usuário {user_id} não encontrado ou inativo no sistema segmenthub")
            return None
    except Exception as e:
        logger.error(f"Erro ao buscar perfil do usuário {user_id}: {e}")
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