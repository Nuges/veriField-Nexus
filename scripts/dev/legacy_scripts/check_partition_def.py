import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://postgres.rxlfxrbyhagyofzfwzoa:TaMpn243vupkPUWL@aws-0-eu-west-1.pooler.supabase.com:5432/postgres"

async def test():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        res = await conn.execute(text("SELECT pg_get_expr(relpartbound, oid) FROM pg_class WHERE relname = 'activities_default'"))
        row = res.scalar_one_or_none()
        print(f"Activities default definition: {row}")

asyncio.run(test())
