"""
SecureIoT-X Database Engine — SQLite (legacy CLI tool only).

NOTE: This module is kept ONLY to support the CLI migration tool
      (database/migrations.py). It is NOT used by the FastAPI application.
      The FastAPI application uses MongoDB exclusively.

Do NOT import this module from FastAPI routes or business logic.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


# ── Base model for legacy SQLAlchemy models ────────────────────
class Base(DeclarativeBase):
    """Declarative base — kept for CLI migration tool only."""
    pass


# ── Safe URL helpers ───────────────────────────────────────────

def _get_async_url(url: str) -> str:
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def _get_sync_url(url: str) -> str:
    url = url.replace("sqlite+aiosqlite:///", "sqlite:///")
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    return url


# ── Engine setup — uses fallback SQLite path if no DATABASE_URL ─

_FALLBACK_DB = "sqlite:///./secureiot.db"

try:
    from backend.core.config import settings as _settings
    # settings no longer exposes database_url — use fallback
    _db_url = getattr(_settings, "database_url", _FALLBACK_DB)
except Exception:
    _db_url = _FALLBACK_DB

_async_url = _get_async_url(_db_url)
_sync_url = _get_sync_url(_db_url)

async_engine = create_async_engine(_async_url, echo=False, future=True)
sync_engine = create_engine(_sync_url, echo=False, future=True)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False,
)
SyncSessionLocal = sessionmaker(bind=sync_engine, expire_on_commit=False)


# ── FastAPI dependency (legacy — not used; MongoDB is used instead) ─────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Legacy async DB session. Not used in FastAPI routes — MongoDB is used."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_db() -> Session:
    """Sync session for CLI migration tool."""
    return SyncSessionLocal()


# ── Table creation (CLI only) ───────────────────────────────────

async def init_db() -> None:
    """Create all legacy tables (async). CLI use only."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def init_db_sync() -> None:
    """Create all legacy tables (sync). CLI use only."""
    Base.metadata.create_all(bind=sync_engine)


async def drop_db() -> None:
    """Drop all legacy tables (async). CLI use only."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
