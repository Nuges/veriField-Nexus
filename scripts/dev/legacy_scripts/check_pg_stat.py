import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import json

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///dev.db")

async def test():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        res = await conn.execute(text("SELECT state, query FROM pg_stat_activity WHERE query ILIKE '%activities%' AND state != 'idle'"))
        for row in res:
            print(f"State: {row[0]}, Query: {row[1][:100]}")

asyncio.run(test())
