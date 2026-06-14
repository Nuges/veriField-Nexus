import asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+asyncpg://postgres.rxlfxrbyhagyofzfwzoa:TaMpn243vupkPUWL@aws-0-eu-west-1.pooler.supabase.com:6543/postgres"

async def inspect():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Count readings
        res = await session.execute(text("SELECT COUNT(*) FROM sensor_readings"))
        count = res.scalar()
        print(f"Total rows in sensor_readings: {count}")
        
        if count > 0:
            res_details = await session.execute(text("SELECT DISTINCT device_id, asset_id FROM sensor_readings"))
            rows = res_details.all()
            for r in rows:
                print(f"Device: {r[0]}, Asset ID: {r[1]}")
                
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(inspect())
