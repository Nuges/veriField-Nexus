"""
=============================================================================
VeriField Nexus — Database Session Management
=============================================================================
Async SQLAlchemy engine and session factory for connecting to Supabase
PostgreSQL. Provides the `get_db` dependency for FastAPI routes.
=============================================================================
"""

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from typing import AsyncGenerator

from app.core.config import settings

# Ensure the connection string uses the asyncpg driver
db_url = settings.database_url
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif db_url and db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# --- Async Engine ---
# Creates a connection pool to Supabase PostgreSQL
# Tuned for Supabase Session pooler (5432)
engine = create_async_engine(
    db_url,
    echo=settings.debug,        # Log SQL queries in debug mode
    pool_size=4,                 # Reduced to stay well below Supabase limits
    max_overflow=2,              # Soft limit to handle bursts without hitting 15
    pool_pre_ping=True,          # Verify connections before use
    pool_recycle=300,            # Recycle connections every 5 minutes
    pool_timeout=15,             # Wait up to 15s for a connection
    connect_args={
        "server_settings": {"jit": "off"},  # Disable JIT for faster simple queries
        "command_timeout": 15.0,             # Kill queries that hang at the socket level
    },
)

# --- Session Factory ---
# Creates new database sessions for each request
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,      # Don't expire objects after commit
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
