import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://postgres.rxlfxrbyhagyofzfwzoa:TaMpn243vupkPUWL@aws-0-eu-west-1.pooler.supabase.com:6543/postgres"

async def test():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        # Get my own pid so I don't kill myself
        res = await conn.execute(text("SELECT pg_backend_pid()"))
        my_pid = res.scalar()
        print(f"My PID is {my_pid}")

        # Kill all other backends
        res = await conn.execute(text(f"""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE pid <> {my_pid}
            AND datname = 'postgres'
        """))
        print("Terminated other connections")

asyncio.run(test())
