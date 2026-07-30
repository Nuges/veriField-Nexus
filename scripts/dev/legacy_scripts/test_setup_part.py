import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.db.partition_activities import setup_monthly_partitioning

DATABASE_URL = "postgresql+asyncpg://postgres.rxlfxrbyhagyofzfwzoa:TaMpn243vupkPUWL@aws-0-eu-west-1.pooler.supabase.com:5432/postgres"

async def test():
    engine = create_async_engine(DATABASE_URL)
    print("Testing setup_monthly_partitioning...")
    await setup_monthly_partitioning(engine)
    print("Finished setup_monthly_partitioning.")

asyncio.run(test())
