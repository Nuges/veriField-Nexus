import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///dev.db")

async def test():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        res = await conn.execute(text("SELECT data_type FROM information_schema.columns WHERE table_name = 'activities' AND column_name = 'created_at'"))
        for row in res:
            print(f"Data type: {row[0]}")

asyncio.run(test())
