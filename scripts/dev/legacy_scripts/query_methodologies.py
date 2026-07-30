import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import json

DATABASE_URL = "postgresql+asyncpg://postgres.rxlfxrbyhagyofzfwzoa:TaMpn243vupkPUWL@aws-0-eu-west-1.pooler.supabase.com:5432/postgres"

async def test():
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    async with engine.begin() as conn:
        res = await conn.execute(text("SELECT code, ui_config FROM methodologies"))
        for row in res:
            print(f"Code: {row[0]}")
            print(f"UI Config: {json.dumps(row[1]) if row[1] else 'NULL'}")
            print("---")

asyncio.run(test())
