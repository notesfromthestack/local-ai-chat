import logging
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import APIRouter, FastAPI
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response

from api.app.config import settings

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

from api.app.routes import router
from api.app.embeddings import embedding_service
from api.app.qdrant_client import vector_store
from api.app.metrics import metrics

BASE_DIR = Path(__file__).resolve().parent
INDEX_PATH = BASE_DIR.parent / "templates" / "index.html"

system_router = APIRouter(tags=["system"])


@system_router.get("/health")
async def health_check():
    """Report liveness of the API and reachability of dependencies."""
    dependencies = {"ollama": "unreachable", "qdrant": "unreachable"}
    async with httpx.AsyncClient(timeout=2.0) as client:
        try:
            r = await client.get(f"{settings.ollama_base_url}/api/tags")
            if r.status_code == 200:
                dependencies["ollama"] = "ok"
        except Exception:
            pass
        try:
            r = await client.get(f"{settings.qdrant_url}/readyz")
            if r.status_code == 200:
                dependencies["qdrant"] = "ok"
        except Exception:
            pass

    overall = "healthy" if all(v == "ok" for v in dependencies.values()) else "degraded"
    return JSONResponse(
        content={
            "status": overall,
            "service": "docchat-api",
            "version": "0.1.0",
            "dependencies": dependencies,
        }
    )


@system_router.get("/metrics")
async def get_metrics():
    """Prometheus-compatible metrics endpoint."""
    return Response(
        content=metrics.get_prometheus_format(),
        media_type="text/plain",
    )


@system_router.get("/", response_class=HTMLResponse)
async def index():
    return FileResponse(INDEX_PATH)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting DocChat API")
    logger.info(f"Ollama URL: {settings.ollama_base_url}")
    logger.info(f"Qdrant URL: {settings.qdrant_url}")
    logger.info(f"Embedding Model: {settings.embedding_model}")

    embedding_service.load()
    vector_store.connect(vector_size=embedding_service.dim)

    yield

    logger.info("Shutting down DocChat API")


app = FastAPI(
    title="DocChat API",
    description="Local RAG chat over your markdown documents.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router)
app.include_router(system_router)
