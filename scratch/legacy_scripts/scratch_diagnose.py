import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.config import settings
from app.models.user import User
from app.models.activity import Activity
from sqlalchemy import select, func

async def main():
    engine = create_async_engine(settings.database_url.replace("postgres://", "postgresql+asyncpg://"))
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    async with SessionLocal() as db:
        # Get all users and their details
        res = await db.execute(select(User))
        users = res.scalars().all()
        print("=== DATABASE USERS ===")
        for u in users:
            print(f"ID: {u.id} | Email: {u.email} | Role: {u.role} | Org: {u.organization} | Name: {u.full_name}")
            
        # Get count of activities per user ID
        res_acts = await db.execute(
            select(Activity.user_id, func.count(Activity.id))
            .group_by(Activity.user_id)
        )
        print("\n=== ACTIVITIES PER USER_ID ===")
        for uid, count in res_acts.all():
            print(f"User ID: {uid} | Count: {count}")

asyncio.run(main())
