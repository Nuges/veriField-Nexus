import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.db.partition_activities import setup_monthly_partitioning

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///dev.db")

async def test():
    engine = create_async_engine(DATABASE_URL)
    print("Testing setup_monthly_partitioning...")
    await setup_monthly_partitioning(engine)
    print("Finished setup_monthly_partitioning.")

asyncio.run(test())
