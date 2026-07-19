"""
=============================================================================
VeriField Nexus — Database Session Management
=============================================================================
Async SQLAlchemy engine and session factory for connecting to Supabase
PostgreSQL. Provides the `get_db` dependency for FastAPI routes.
=============================================================================
"""

import os
import uuid
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)

from app.core.config import settings

# Ensure the connection string uses the asyncpg driver and transaction pooler
db_url = settings.database_url
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif db_url and db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# --- Async Engine ---
# Creates a connection pool to Supabase PostgreSQL
# Tuned for PgBouncer transaction pooling or direct sessions
import sys

from sqlalchemy import pool

is_testing = "pytest" in sys.modules or os.environ.get("TESTING") == "1"

engine_kwargs = {
    "echo": settings.debug,
    "poolclass": pool.NullPool if is_testing else None,
    "pool_pre_ping": True if not is_testing else False,
    "pool_recycle": 1800 if not is_testing else -1,
    "connect_args": {
        "ssl": "require",
        "server_settings": {"jit": "off", "application_name": "verifield"},
        "command_timeout": 60.0,
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
        "prepared_statement_name_func": lambda: f"__asyncpg_{uuid.uuid4()}__",
    },
}

if not is_testing:
    engine_kwargs["pool_size"] = 5
    engine_kwargs["max_overflow"] = 15
    engine_kwargs["pool_timeout"] = 60
else:
    engine_kwargs["connect_args"].pop("ssl", None)

engine = create_async_engine(db_url, **engine_kwargs)

# --- Session Factory ---
# Creates new database sessions for each request
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Don't expire objects after commit
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session.

    Automatically handles session lifecycle:
    - Creates a new session for each request
    - Commits on success (if manually committed in route)
    - Rolls back on exception
    - Always closes the session

    Usage:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
