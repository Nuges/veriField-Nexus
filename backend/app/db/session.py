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

# --- Async Engine ---
# Creates a connection pool to Supabase PostgreSQL
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,        # Log SQL queries in debug mode
    pool_size=20,                # Connection pool size
    max_overflow=10,             # Extra connections allowed beyond pool_size
    pool_pre_ping=True,          # Verify connections before use
    pool_recycle=300,            # Recycle connections every 5 minutes
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
