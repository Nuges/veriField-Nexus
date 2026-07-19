import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://postgres.rxlfxrbyhagyofzfwzoa:TaMpn243vupkPUWL@34.241.16.247:5432/postgres"

async def main():
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT email FROM users LIMIT 5;"))
        rows = res.fetchall()
        for r in rows:
            print(f"User: {r[0]}")

asyncio.run(main())
