"""Async SQLAlchemy session machinery + table creation."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import get_settings
from .models import Base


_settings = get_settings()

engine = create_async_engine(
    _settings.database_url,
    echo=False,
    future=True,
)

SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    """Create tables if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    """FastAPI dependency for per-request sessions."""
    async with SessionLocal() as session:
        yield session
