import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://postgres.rxlfxrbyhagyofzfwzoa:TaMpn243vupkPUWL@34.241.16.247:6543/postgres?prepared_statement_cache_size=0"

async def main():
    engine = create_async_engine(DATABASE_URL, connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0})
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT id, name, meta_data FROM assets LIMIT 2;"))
        rows = res.fetchall()
        for r in rows:
            print(f"ID: {r[0]}, Name: {r[1]}, MetaData: {r[2]}")

asyncio.run(main())
