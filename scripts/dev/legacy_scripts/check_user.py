import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://postgres.rxlfxrbyhagyofzfwzoa:TaMpn243vupkPUWL@aws-0-eu-west-1.pooler.supabase.com:5432/postgres"

async def test():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        res = await conn.execute(text("SELECT id, email, hashed_password, status, is_superuser, mfa_enabled FROM users WHERE email = 'dami@gmail.com'"))
        user = res.fetchone()
        print(f"User: {user}")

        # also check requests
        res = await conn.execute(text("SELECT id, email, use_case, status FROM access_requests WHERE email = 'dami@gmail.com'"))
        req = res.fetchone()
        print(f"Request: {req}")

asyncio.run(test())
