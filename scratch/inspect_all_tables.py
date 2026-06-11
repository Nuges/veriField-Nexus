import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+asyncpg://postgres.rxlfxrbyhagyofzfwzoa:TaMpn243vupkPUWL@aws-0-eu-west-1.pooler.supabase.com:5432/postgres"

async def inspect():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        tables = [
            "users",
            "properties",
            "activities",
            "sensor_readings",
            "community_validations",
            "audits",
            "anomaly_flags",
            "carbon_ledger",
            "carbon_calculations"
        ]
        
        for table in tables:
            try:
                res = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = res.scalar()
                print(f"Table '{table}' row count: {count}")
            except Exception as e:
                print(f"Table '{table}' error: {e}")
                
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(inspect())
