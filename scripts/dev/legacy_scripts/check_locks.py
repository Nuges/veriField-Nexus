import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///dev.db")

async def test():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        res = await conn.execute(text("SELECT pid, mode, granted, relation::regclass FROM pg_locks WHERE relation::regclass::text LIKE '%activities%';"))
        for row in res:
            print(row)

asyncio.run(test())
