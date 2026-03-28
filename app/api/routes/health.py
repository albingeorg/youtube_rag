"""
app/api/routes/health.py
─────────────────────────
Simple health-check endpoint — useful for Docker / k8s liveness probes.
"""

from fastapi import APIRouter, Depends

from app.api.dependencies import get_vector_store
from app.api.schemas import HealthResponse
from app.core.config import get_settings
from app.rag.store import VideoStore

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service health check",
)
async def health(store: VideoStore = Depends(get_vector_store)):
    settings = get_settings()
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        videos_indexed=store.count(),
    )