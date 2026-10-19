from __future__ import annotations
import logging, os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .api import router
from . import models  # noqa: F401 - register all ORM tables before schema initialization
from .db import Base, SessionLocal, engine
from .seed import ensure_catalog

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("careerinsight")

def schema_autocreate_enabled() -> bool:
    return os.getenv("CAREERINSIGHT_AUTO_CREATE", "").strip().casefold() in {"1", "true", "yes", "on"}

@asynccontextmanager
async def lifespan(_: FastAPI):
    # Local SQLite is the default development database. Create any missing tables
    # before seeding the catalogue so a fresh ZIP checkout starts without a manual
    # migration step. Managed databases continue to use Alembic unless explicitly opted in.
    if schema_autocreate_enabled() or engine.dialect.name == "sqlite":
        Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        ensure_catalog(db)
    yield

app = FastAPI(title="CareerInsight AI", description="Explainable career path and skill decision support", version="1.0.0", lifespan=lifespan)
app.add_middleware(GZipMiddleware, minimum_size=1000)

@app.middleware("http")
async def response_headers(request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault("Cache-Control", "no-store")
    return response

app.include_router(router)

@app.get("/healthz", include_in_schema=False)
def healthz():
    return {"ok": True}

# In production the compiled SPA is served by the same FastAPI origin as its REST API.
static_dir = Path(__file__).resolve().parents[1] / "frontend" / "dist"
if static_dir.exists():
    assets_dir = static_dir / "assets"
    if assets_dir.exists(): app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    @app.get("/{path:path}", include_in_schema=False)
    def serve_spa(path: str):
        candidate = (static_dir / path).resolve()
        if candidate.is_file() and static_dir.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(static_dir / "index.html")
