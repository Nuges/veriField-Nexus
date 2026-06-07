import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.config import settings
from app.models.user import User
from sqlalchemy import select

async def main():
    engine = create_async_engine(settings.database_url.replace("postgres://", "postgresql+asyncpg://"))
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    async with SessionLocal() as db:
        res = await db.execute(select(User).where(User.email == "pete@gmail.com"))
        user = res.scalar_one_or_none()
        if user:
            print(f"Found user {user.email} with role {user.role}. Upgrading to admin...")
            user.role = "admin"
            await db.commit()
            print("Upgraded successfully!")
        else:
            print("User pete@gmail.com not found!")

asyncio.run(main())
