import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://postgres.rxlfxrbyhagyofzfwzoa:TaMpn243vupkPUWL@aws-0-eu-west-1.pooler.supabase.com:5432/postgres"

async def test():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        res = await conn.execute(text("SELECT relname, pg_get_expr(relpartbound, oid) FROM pg_class WHERE relname LIKE 'activities_y%'"))
        for row in res:
            print(f"Partition: {row[0]}, Bounds: {row[1]}")

asyncio.run(test())
