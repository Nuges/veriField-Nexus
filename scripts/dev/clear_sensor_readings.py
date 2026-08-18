import os
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///dev.db")

async def clear_sensors():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Delete readings
        print("Clearing all rows from sensor_readings...")
        res = await session.execute(text("DELETE FROM sensor_readings"))
        await session.commit()
        print(f"Cleared {res.rowcount} rows from sensor_readings.")
                
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(clear_sensors())
