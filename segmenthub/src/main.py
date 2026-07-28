from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app = FastAPI(title="SegmentHub - S1", version="0.1.0")

# Health check
@app.get("/health")
def health():
    return {"status": "ok", "system": "SegmentHub"}

# API routers serão montados aqui
# from src.api import metadata, segmentacao, estimativa, ...
# app.include_router(metadata.router, prefix="/api")

# Static files (React build)
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
else:
    @app.get("/")
    def root():
        return {"message": "SegmentHub API - Frontend not built yet"}

# Rota catch-all para SPA (se buildado)
@app.get("/{full_path:path}")
def spa(full_path: str):
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Not found"}
