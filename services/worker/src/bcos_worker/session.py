"""Async database session infrastructure for the BCOS worker."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from bcos_worker.config import DatabaseSettings


def _normalize_database_url(url: str) -> str:
    """Normalize PostgreSQL URLs for SQLAlchemy with psycopg 3."""

    if url.startswith("postgresql+psycopg://"):
        return url

    if url.startswith("postgresql://"):
        return url.replace(
            "postgresql://",
            "postgresql+psycopg://",
            1,
        )

    if url.startswith("postgres://"):
        return url.replace(
            "postgres://",
            "postgresql+psycopg://",
            1,
        )

    raise RuntimeError(
        "DATABASE_URL must use a PostgreSQL connection URL."
    )


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Return the shared async engine, creating it on first use."""

    global _engine
    global _session_factory

    if _engine is None:
        settings = DatabaseSettings.from_env()

        _engine = create_async_engine(
            _normalize_database_url(settings.url),
            pool_pre_ping=True,
        )

        _session_factory = async_sessionmaker(
            bind=_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the shared worker session factory."""

    global _session_factory

    if _session_factory is None:
        get_engine()

    if _session_factory is None:
        raise RuntimeError(
            "Database session factory could not be initialized."
        )

    return _session_factory
