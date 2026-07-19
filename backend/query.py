import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
from app.core.config import settings

async def run():
    engine = create_async_engine(settings.database_url.replace("postgresql://", "postgresql+asyncpg://"))
    async with AsyncSession(engine) as session:
        props = await session.execute(text("SELECT id, name, status FROM properties"))
        print("Properties:")
        for p in props.mappings().all():
            print(dict(p))
            
        acts = await session.execute(text("SELECT id, property_id, status, trust_score FROM activities"))
        print("\nActivities:")
        for a in acts.mappings().all():
            print(dict(a))

if __name__ == "__main__":
    asyncio.run(run())
