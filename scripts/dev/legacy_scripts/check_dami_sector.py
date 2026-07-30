import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://postgres.rxlfxrbyhagyofzfwzoa:TaMpn243vupkPUWL@aws-0-eu-west-1.pooler.supabase.com:5432/postgres"

async def test():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        res = await conn.execute(text("SELECT id, email, organization_id FROM users WHERE email = 'dami@gmail.com'"))
        user = res.fetchone()
        if user:
            print(f"User: {user.email}, org: {user.organization_id}")
            if user.organization_id:
                res2 = await conn.execute(text("SELECT id, name, sector, sub_sector, type FROM organizations WHERE id = :org_id"), {"org_id": user.organization_id})
                org = res2.fetchone()
                print(f"Org: {org}")
        else:
            print("User not found")

asyncio.run(test())
