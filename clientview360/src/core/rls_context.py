# OBO/RLS - S2-BACK-01
from fastapi import Request, HTTPException
from databricks.sdk import WorkspaceClient

def get_current_user_obo(request: Request) -> dict:
    # O Databricks Apps injeta o usuário OBO no contexto
    # Exemplo: request.headers.get('X-Databricks-User')
    user = request.headers.get('X-Databricks-User')
    if not user:
        # fallback para dev
        return {"usuario": "dev_user", "perfil": "admin"}
    # TODO: validar perfil em governanca.usuarios_perfil
    return {"usuario": user, "perfil": "gerente"}

def require_obo():
    def dependency(user: dict = Depends(get_current_user_obo)):
        if not user:
            raise HTTPException(401, "Não autenticado")
        return user
    return dependency
