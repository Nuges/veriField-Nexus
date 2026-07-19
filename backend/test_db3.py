import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://postgres.rxlfxrbyhagyofzfwzoa:TaMpn243vupkPUWL@aws-0-eu-west-1.pooler.supabase.com:6543/postgres?prepared_statement_cache_size=0"

async def main():
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT state, count(*) FROM pg_stat_activity GROUP BY state;"))
        rows = res.fetchall()
        for r in rows:
            print(r)

asyncio.run(main())
