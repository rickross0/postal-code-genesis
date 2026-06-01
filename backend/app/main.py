"""FastAPI application entry point."""

import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.core.database import init_db
from app.api.routes import router

logger = logging.getLogger(__name__)

# Frontend static files directory (populated in Docker build)
STATIC_DIR = Path(__file__).parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Static dir exists: {STATIC_DIR.exists()}")
    logger.info(f"index.html exists: {(STATIC_DIR / 'index.html').exists() if STATIC_DIR.exists() else 'N/A'}")
    logger.info(f"DB_HOST: {settings.db_host or '(empty)'}")
    logger.info(f"DB_URL starts with: {settings.get_async_url()[:30]}...")
    await init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API routes (registered first, take priority) ──
app.include_router(router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.app_version}


@app.get("/api")
async def api_root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
    }


# ── Serve React frontend (production only) ──
if STATIC_DIR.exists() and (STATIC_DIR / "index.html").exists():

    @app.get("/favicon.ico")
    async def favicon():
        fav = STATIC_DIR / "favicon.ico"
        if fav.exists():
            return FileResponse(str(fav))
        return FileResponse(str(STATIC_DIR / "index.html"), status_code=404,
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

    # Serve JS/CSS assets from /static (React build output)
    static_assets = STATIC_DIR / "static"
    if static_assets.exists():
        app.mount("/static", StaticFiles(directory=str(static_assets)), name="static_assets")

    # Catch-all for SPA: serve index.html for any non-API path
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = STATIC_DIR / full_path
        if full_path and file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        # Never cache index.html so the browser always fetches the latest JS/CSS hashes
        return FileResponse(
            str(STATIC_DIR / "index.html"),
            headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"},
        )


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
