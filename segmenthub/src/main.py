from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import logging
from typing import List

from src.api import metadata, segmentacao, estimativa, comentario, saude, metadata_admin, chat
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
app.include_router(chat.router, prefix="/api")

# ============================================================
# Static files (frontend build)
# ============================================================
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
else:
    logger.warning("Pasta 'static' não encontrada. Frontend não será servido.")
    @app.get("/")
    async def root():
        return {"message": "SegmentHub API - Frontend não construído"}

# Fallback para SPA (se o frontend estiver buildado)
@app.get("/{full_path:path}")
async def spa(full_path: str):
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Not found"}

# ============================================================
# Ponto de entrada (para execução local)
# ============================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)