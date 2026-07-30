import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://postgres.rxlfxrbyhagyofzfwzoa:TaMpn243vupkPUWL@aws-0-eu-west-1.pooler.supabase.com:5432/postgres"

async def test():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        res = await conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'organizations'"))
        columns = [row[0] for row in res]
        print(f"Organizations columns: {columns}")

        res = await conn.execute(text("SELECT id, email, organization_id FROM users WHERE email = 'dami@gmail.com'"))
        user = res.fetchone()
        print(f"User: {user}")
        if user and user.organization_id:
            res2 = await conn.execute(text(f"SELECT * FROM organizations WHERE id = '{user.organization_id}'"))
            org = res2.fetchone()
            print(f"Org: {org}")

asyncio.run(test())
