import asyncio
from app.db.session import async_session_factory
from sqlalchemy import text

async def main():
    try:
        async with async_session_factory() as session:
            res = await session.execute(text("SELECT 1"))
            print("DB connected! Result:", res.scalar())
    except Exception as e:
        print("DB connection failed:", e)

if __name__ == "__main__":
    asyncio.run(main())
