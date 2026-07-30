import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://postgres.rxlfxrbyhagyofzfwzoa:TaMpn243vupkPUWL@aws-0-eu-west-1.pooler.supabase.com:5432/postgres"

async def test():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        res = await conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'users'"))
        for row in res:
            print(row[0])

        res2 = await conn.execute(text("SELECT email, status FROM users WHERE email = 'dami@gmail.com'"))
        user = res2.fetchone()
        print(f"User: {user}")

asyncio.run(test())
