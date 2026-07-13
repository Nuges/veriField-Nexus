import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.db.base import Base
from app.core.config import settings
import app.models

async def main():
    engine = create_async_engine(
        str(settings.database_url),
        connect_args={"statement_cache_size": 0}
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()

asyncio.run(main())
