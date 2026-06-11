import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+asyncpg://postgres.rxlfxrbyhagyofzfwzoa:TaMpn243vupkPUWL@aws-0-eu-west-1.pooler.supabase.com:5432/postgres"

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
