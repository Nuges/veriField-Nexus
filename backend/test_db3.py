import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///dev.db")

async def main():
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT state, count(*) FROM pg_stat_activity GROUP BY state;"))
        rows = res.fetchall()
        for r in rows:
            print(r)

asyncio.run(main())
