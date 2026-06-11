import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.config import settings
from app.models.activity import Activity
from app.models.user import User
from sqlalchemy import select

async def main():
    engine = create_async_engine(settings.database_url.replace("postgres://", "postgresql+asyncpg://"))
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    async with SessionLocal() as db:
        # Get latest activity
        res = await db.execute(select(Activity).order_by(Activity.captured_at.desc()).limit(1))
        a = res.scalar_one_or_none()
        if a:
            print("Latest DB Activity:")
            print("ID:", a.id)
            print("Type:", a.activity_type)
            print("Status:", a.status)
            print("Captured At:", a.captured_at)
            print("Created At:", a.created_at)
            print("User ID:", a.user_id)
        
        # Test what admin gets (No user_id filter)
        res = await db.execute(select(Activity).order_by(Activity.captured_at.desc()).limit(5))
        acts = res.scalars().all()
        print(f"\nLast 5 activities for Admin GET /activities: {[str(x.id) for x in acts]}")

asyncio.run(main())
