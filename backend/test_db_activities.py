import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://postgres.rxlfxrbyhagyofzfwzoa:TaMpn243vupkPUWL@34.241.16.247:6543/postgres?prepared_statement_cache_size=0"

async def main():
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT activity_data FROM activities LIMIT 2;"))
        print(res.fetchall())

asyncio.run(main())
