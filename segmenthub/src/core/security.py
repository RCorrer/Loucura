# Placeholder S1-BACK-01
from fastapi import HTTPException, Depends, Request
from typing import Optional

def get_current_user(request: Request) -> Optional[dict]:
    # TODO: implementar RBAC com governanca.usuarios_perfil
    # Por enquanto, mock admin
    return {"perfil": "admin", "usuario": "mock"}

def require_perfil(perfis_perm: list):
    def dependency(user: dict = Depends(get_current_user)):
        if not user or user.get("perfil") not in perfis_perm:
            raise HTTPException(403, "Acesso negado")
        return user
    return dependency
