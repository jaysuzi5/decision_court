from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .config import get_settings
from .models import Base

_settings = get_settings()
engine = create_async_engine(_settings.database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# Lightweight idempotent migrations for columns added after first deploy
# (create_all only creates missing tables, never alters existing ones).
_MIGRATIONS = [
    "ALTER TABLE shares ADD COLUMN IF NOT EXISTS gallery BOOLEAN NOT NULL DEFAULT FALSE",
    "CREATE INDEX IF NOT EXISTS ix_shares_gallery ON shares (gallery)",
]


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for stmt in _MIGRATIONS:
            await conn.execute(text(stmt))


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
