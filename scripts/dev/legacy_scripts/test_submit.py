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
        # Get first user
        result = await db.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        if not user:
            print("No users found.")
            return

        print(f"Submitting for user {user.email}")
        from app.schemas.activity import ActivityCreate
        from datetime import datetime
        payload = ActivityCreate(
            activity_type="CLEAN_COOKING",
            activity_data={"household_size": 4, "primary_fuel": "wood"},
            captured_at=datetime.utcnow(),
            latitude=6.5244,
            longitude=3.3792
        )
        
        # Manually invoke the endpoint logic or just print to see if we can connect
        print("Schema validated fine!")

asyncio.run(main())
