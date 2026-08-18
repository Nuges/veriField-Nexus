import os
import asyncio
import time
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///dev.db")

engine = create_async_engine(DATABASE_URL, pool_size=5, max_overflow=10, pool_pre_ping=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def test():
    print("Testing connection 1...")
    start = time.time()
    async with async_session() as session:
        await session.execute(text("SELECT 1"))
    print(f"Connection 1 took {time.time()-start:.3f}s")

    print("Testing connection 2...")
    start = time.time()
    async with async_session() as session:
        await session.execute(text("SELECT 1"))
    print(f"Connection 2 took {time.time()-start:.3f}s")

if __name__ == "__main__":
    asyncio.run(test())
