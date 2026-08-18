import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, func
from app.domains.authentication.models import User
from app.domains.activities.models import Activity

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///dev.db")
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def main():
    async with async_session() as session:
        stmt = select(User).where(User.role.in_(["field_agent", "FIELD_AGENT"]))
        res = await session.execute(stmt)
        users = res.scalars().all()
        print("Users with role field_agent or FIELD_AGENT:", [(u.email, u.role) for u in users])

        # Let's see what roles actually exist in the DB
        stmt = select(User.role, func.count(User.id)).group_by(User.role)
        res = await session.execute(stmt)
        roles = res.all()
        print("All roles in DB:", roles)

asyncio.run(main())
