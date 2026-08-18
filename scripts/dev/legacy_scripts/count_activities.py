import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///dev.db")

async def test():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        res = await conn.execute(text("SELECT count(*) FROM activities"))
        row = res.scalar_one()
        print(f"Activities count: {row}")

        # also check tables
        res2 = await conn.execute(text("SELECT tablename FROM pg_tables WHERE tablename LIKE 'activities%'"))
        for r in res2:
            print(f"Table: {r[0]}")

asyncio.run(test())
