import asyncio
from sqlalchemy import text
from app.db.session import async_session_factory

async def clear_users():
    async with async_session_factory() as session:
        await session.execute(text("TRUNCATE TABLE users CASCADE;"))
        await session.commit()
        print("Users table cleared")

if __name__ == "__main__":
    asyncio.run(clear_users())
