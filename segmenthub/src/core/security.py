async def get_current_user(request: Request) -> Optional[dict]:
    user_email = request.headers.get("X-Forwarded-Email")
    if not user_email:
        user_email = os.getenv("DEV_USER")
    if not user_email:
        return None

    try:
        client = get_client()
        row = client.fetch_one(
            "SELECT perfil FROM plataforma.governanca.usuarios_perfil "
            "WHERE usuario_id = :user_id AND sistema = 'segmenthub' AND ativo = true",
            {"user_id": user_email}
        )
        if row:
            return {"usuario_id": user_email, "perfil": row[0]}  # row é uma lista
        return None
    except Exception as e:
        logger.error(f"Erro: {e}")
        return {"usuario_id": user_email, "perfil": "admin"} if os.getenv("ENV") != "production" else None