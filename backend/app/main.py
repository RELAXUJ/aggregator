"""FastAPI application factory and main entry point."""

import asyncio
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.rwa_aggregator.infrastructure.tasks.price_tasks import _fetch_all_prices_async
from app.rwa_aggregator.presentation.api import alerts, health, prices, tokens
from app.rwa_aggregator.presentation.web import dashboard

settings = get_settings()
logger = get_logger(__name__)


async def price_fetcher_loop() -> None:
    """Background task to fetch prices every 10 seconds."""
    while True:
        try:
            logger.debug("Fetching prices from all venues...")
            result = await _fetch_all_prices_async()
            logger.info(
                f"Price fetch complete: {result['snapshots_created']} snapshots "
                f"for {result['tokens_processed']} tokens"
            )
        except Exception as e:
            logger.error(f"Price fetch error: {e}")
        await asyncio.sleep(10)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup/shutdown events."""
    # Startup
    setup_logging(level="DEBUG" if settings.debug else "INFO")
    logger.info("RWA Liquidity Aggregator starting up...")
    logger.info(f"Environment: {settings.app_env}")

    # Run database migrations on startup (Railway deployment)
    if settings.is_production:
        try:
            logger.info("Running database migrations...")
            import os
            import subprocess
            import sys
            
            # Find alembic.ini - it's in the backend directory
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            alembic_ini_path = os.path.join(backend_dir, "alembic.ini")
            
            if os.path.exists(alembic_ini_path):
                # Change to backend directory and run alembic command
                original_cwd = os.getcwd()
                try:
                    os.chdir(backend_dir)
                    result = subprocess.run(
                        [sys.executable, "-m", "alembic", "upgrade", "head"],
                        capture_output=True,
                        text=True,
                        timeout=60,
                    )
                    if result.returncode == 0:
                        logger.info("✅ Database migrations completed")
                        if result.stdout:
                            logger.debug(f"Migration output: {result.stdout}")
                    else:
                        logger.error(f"⚠️ Migration failed: {result.stderr}")
                finally:
                    os.chdir(original_cwd)
            else:
                logger.warning(f"⚠️ alembic.ini not found at {alembic_ini_path}, skipping migrations")
        except Exception as e:
            logger.error(f"⚠️ Migration error (continuing anyway): {e}")
            import traceback
            logger.error(traceback.format_exc())

    # Start background price fetcher
    logger.info("Starting price fetcher background task (every 10s)...")
    price_task = asyncio.create_task(price_fetcher_loop())

    yield

    # Shutdown
    logger.info("RWA Liquidity Aggregator shutting down...")
    price_task.cancel()
    try:
        await price_task
    except asyncio.CancelledError:
        logger.info("Price fetcher task cancelled")


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
