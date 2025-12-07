"""FastAPI application factory and main entry point."""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.rwa_aggregator.presentation.api import alerts, health, prices, tokens
from app.rwa_aggregator.presentation.web import dashboard

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup/shutdown events."""
    # Startup
    setup_logging(level="DEBUG" if settings.debug else "INFO")
    logger.info("RWA Liquidity Aggregator starting up...")
    logger.info(f"Environment: {settings.app_env}")

    yield

    # Shutdown
    logger.info("RWA Liquidity Aggregator shutting down...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="RWA Liquidity Aggregator",
        description="Real-time price aggregation for RWA tokens across multiple venues",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs" if settings.is_development else None,
        redoc_url="/api/redoc" if settings.is_development else None,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.is_development else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routes
    app.include_router(health.router, prefix="/api", tags=["Health"])
    app.include_router(prices.router, prefix="/api", tags=["Prices"])
    app.include_router(alerts.router, prefix="/api", tags=["Alerts"])
    app.include_router(tokens.router, prefix="/api", tags=["Tokens"])

    # Web routes (HTMX dashboard) - no prefix for root /
    app.include_router(dashboard.router, tags=["Web"])

    # Static files (if directory exists)
    static_dir = os.path.join(
        os.path.dirname(__file__),
        "rwa_aggregator",
        "presentation",
        "static",
    )
    if os.path.isdir(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    return app


# Application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development,
    )
