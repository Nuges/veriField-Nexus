import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import json

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///dev.db")

async def test():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        res = await conn.execute(text("SELECT relkind FROM pg_class WHERE relname = 'activities'"))
        row = res.scalar_one_or_none()
        print(f"Activities relkind: {row}")

asyncio.run(test())
