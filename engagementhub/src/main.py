"""EngagementHub (S3) — FastAPI Application.
Marketing Cloud: campanhas, jornadas, peças, disparos, tracking, MAB.
"""

import os
import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

from src.core.config import APP_NAME, APP_VERSION

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown."""
    logger.info(f"\u25b6 {APP_NAME} v{APP_VERSION} iniciando...")
    yield
    logger.info(f"\u25a0 {APP_NAME} encerrando.")


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,
)


# --- Health Check ---
@app.get("/health")
def health():
    return {"status": "ok", "system": APP_NAME, "version": APP_VERSION}


# --- API Routers ---
from src.api.campanha import router as campanha_router
from src.api.peca import router as peca_router
# from src.api.jornada import router as jornada_router
# from src.api.disparo import router as disparo_router
# from src.api.avulso import router as avulso_router
# from src.api.operacao import router as operacao_router
# from src.api.admin import router as admin_router
#
app.include_router(campanha_router, prefix="/api/campanhas", tags=["Campanhas"])
app.include_router(peca_router, prefix="/api/pecas", tags=["Peças"])
# app.include_router(jornada_router, prefix="/api/jornadas", tags=["Jornadas"])
# app.include_router(disparo_router, prefix="/api/disparo", tags=["Disparo"])
# app.include_router(avulso_router, prefix="/api/avulso", tags=["Avulso"])
# app.include_router(operacao_router, prefix="/api/operacao", tags=["Operação"])
# app.include_router(admin_router, prefix="/api/admin", tags=["Admin"])

# --- Tracking Routers (endpoints públicos) ---
# from src.track.open import router as track_open_router
# from src.track.click import router as track_click_router
# from src.track.webhooks import router as webhook_router
#
# app.include_router(track_open_router, prefix="/track", tags=["Tracking"])
# app.include_router(track_click_router, prefix="/track", tags=["Tracking"])
# app.include_router(webhook_router, prefix="/webhook", tags=["Webhooks"])


# --- SPA Fallback (React build em /static) ---
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")

if os.path.exists(static_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(static_dir, "assets")), name="assets")


@app.get("/{full_path:path}")
def spa(full_path: str):
    """SPA fallback: serve index.html para rotas do React Router."""
    # Não intercepta /api, /track, /webhook, /health, /docs
    if full_path.startswith(("api/", "track/", "webhook/", "health", "docs", "openapi")):
        return {"detail": "Not found"}
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": f"{APP_NAME} API - Frontend not built yet. Acesse /docs."}
