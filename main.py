"""
main.py
────────
Application entry point.
Run with:  python main.py
        or uvicorn main:app --reload
"""

import uvicorn
from app.app import create_app
from app.core.config import get_settings

app = create_app()

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_debug,
        log_level="debug" if settings.app_debug else "info",
    )