"""
app/app.py
──────────
FastAPI application factory.
Creates and configures the app instance with all middleware,
routes, and startup/shutdown lifecycle hooks.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.api.routes.videos import router as videos_router
from app.api.routes.qa import router as qa_router
from app.api.routes.health import router as health_router
from app.rag.store import VideoStore
from app.services.llm import LLMService
from app.services.video import VideoService

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.
    Runs startup logic before yield, teardown after.
    """
    settings = get_settings()
    setup_logging(debug=settings.app_debug)

    logger.info(f"Starting {settings.app_title} v{settings.app_version}")
    logger.info(f"Debug mode: {settings.app_debug}")

    # ── Initialise shared singletons ──────────────────────────────
    store = VideoStore()
    llm_service = LLMService()
    video_service = VideoService(store=store)

    # Attach to app state for dependency injection
    app.state.store = store
    app.state.llm_service = llm_service
    app.state.video_service = video_service

    logger.info("All services initialised. Ready to serve requests.")
    yield

    # ── Teardown ──────────────────────────────────────────────────
    logger.info(f"Shutting down. {store.count()} video(s) were indexed this session.")


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_title,
        version=settings.app_version,
        description=(
            "Production-ready RAG pipeline for YouTube videos. "
            "Index any video transcript and ask questions powered by Groq LLM."
        ),
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── API Routers ───────────────────────────────────────────────
    app.include_router(health_router,  prefix="/api")
    app.include_router(videos_router,  prefix="/api")
    app.include_router(qa_router,      prefix="/api")

    # ── Static files + SPA catch-all ─────────────────────────────
    app.mount("/static", StaticFiles(directory="static"), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_ui():
        return FileResponse("static/index.html")

    return app