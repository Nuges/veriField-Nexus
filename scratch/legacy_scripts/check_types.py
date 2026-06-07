import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.config import settings
from app.models.activity import Activity
from sqlalchemy import select, func

async def main():
    engine = create_async_engine(settings.database_url.replace("postgres://", "postgresql+asyncpg://"))
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    async with SessionLocal() as db:
        # Get count of activities per activity_type
        res_acts = await db.execute(
            select(Activity.activity_type, func.count(Activity.id))
            .group_by(Activity.activity_type)
        )
        print("=== ACTIVITY TYPES ===")
        for type_name, count in res_acts.all():
            print(f"Activity Type: {type_name} | Count: {count}")

asyncio.run(main())
