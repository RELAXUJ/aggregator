"""Async database session management.

Provides async SQLAlchemy engine and session factory for PostgreSQL
using asyncpg driver.
"""

from collections.abc import AsyncGenerator
from typing import Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings


def _get_async_database_url() -> str:
    """Convert database URL to async variant using asyncpg driver."""
    settings = get_settings()
    url = str(settings.database_url)
    # Replace postgresql:// or postgresql+psycopg:// with postgresql+asyncpg://
    if url.startswith("postgresql+psycopg://"):
        return url.replace("postgresql+psycopg://", "postgresql+asyncpg://")
    elif url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://")
    return url


# Lazy initialization - engine and session factory created on first use
_engine: Optional[AsyncEngine] = None
_async_session_local: Optional[async_sessionmaker[AsyncSession]] = None


def get_engine() -> AsyncEngine:
    """Get or create the async database engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            _get_async_database_url(),
            echo=settings.debug,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )
    return _engine


def get_async_session_local() -> async_sessionmaker[AsyncSession]:
    """Get or create the async session factory."""
    global _async_session_local
    if _async_session_local is None:
        _async_session_local = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _async_session_local


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions.

    Yields an async session and ensures it's closed after use.
    Use with FastAPI's Depends():

        @router.get("/items")
        async def get_items(session: AsyncSession = Depends(get_db_session)):
            ...

    Yields:
        AsyncSession: An async SQLAlchemy session.
    """
    session_factory = get_async_session_local()
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
