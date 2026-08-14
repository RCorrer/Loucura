from fastapi import FastAPI, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
import os
import logging

from src.api import metadata, segmentacao, estimativa, comentario, saude, metadata_admin
from src.core.config import AppConfig
from src.core.security import get_current_user, require_perfil

# Configura logging
logging.basicConfig(level=AppConfig.LOG_LEVEL)
logger = logging.getLogger(__name__)

# Cria a aplicação
app = FastAPI(
    title="SegmentHub - S1",
    description="API de gestão de segmentações",
    version="0.1.0",
)

# ============================================================
# Health check
# ============================================================
@app.get("/health")
async def health():
    return {"status": "ok", "system": "SegmentHub"}

# ============================================================
# Rotas protegidas (exemplo)
# ============================================================
@app.get("/api/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Retorna o usuário atual (útil para debug)."""
    return {"user": user}

# ============================================================
# Debug: visualizar cabeçalhos da requisição
# ============================================================
@app.get("/api/debug-headers")
async def debug_headers(request: Request):
    """Retorna todos os cabeçalhos da requisição (útil para diagnóstico OBO)."""
    return {"headers": dict(request.headers)}

# ============================================================
# Debug: testar conexão com o banco
# ============================================================
@app.get("/api/test-db")
async def test_db_connection():
    from src.db.databricks_client import get_client
    import logging
    logger = logging.getLogger(__name__)

    try:
        client = get_client()  # <-- sem argumentos
        result = client.fetch_one("SELECT 1 AS valor")
        return {
            "status": "success",
            "result": result,
            "message": "Conexão com o banco funcionando!"
        }
    except Exception as e:
        logger.error(f"Erro no test-db: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": "Falha na conexão com o banco"
        }

# ============================================================
# Debug: testar conexão com o banco usando TestDatabricksClient
# ============================================================
@app.get("/api/test-simplified")
async def test_simplified():
    from src.db.test_client import TestDatabricksClient
    try:
        client = TestDatabricksClient()
        rows = client.execute_query("SELECT 1 AS valor")
        return {
            "status": "success",
            "result": rows,
            "message": "Cliente simplificado funcionando!"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": "Falha no cliente simplificado"
        }    

# ============================================================
# Inclusão de routers
# ============================================================
app.include_router(metadata.router, prefix="/api")
app.include_router(segmentacao.router, prefix="/api")
app.include_router(estimativa.router, prefix="/api")
app.include_router(comentario.router, prefix="/api")
app.include_router(comentario.comentario_router, prefix="/api")
app.include_router(comentario.notificacao_router, prefix="/api")
app.include_router(saude.router, prefix="/api")
app.include_router(metadata_admin.router, prefix="/api")

# ============================================================
# Static files + SPA fallback
# ============================================================
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")

if os.path.exists(static_dir):
    # Serve assets buildados (JS/CSS/images) em /assets
    assets_dir = os.path.join(static_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="static-assets")

    # SPA fallback: qualquer rota não-API serve index.html (React Router resolve)
    @app.get("/{full_path:path}")
    async def spa(full_path: str):
        index_path = os.path.join(static_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return Response(status_code=404)
else:
    logger.warning("Pasta 'static' não encontrada. Frontend não será servido.")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        return {"message": "Frontend não construído. Execute npm run build."}

# ============================================================
# Ponto de entrada (para execução local)
# ============================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)