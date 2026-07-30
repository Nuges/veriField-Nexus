import asyncio
from sqlalchemy import text
from app.db.session import async_session_factory

async def main():
    async with async_session_factory() as db:
        res = await db.execute(text("SELECT email, licensed_sectors, licensed_methodologies FROM users WHERE role='ORG_ADMIN'"))
        for row in res.fetchall():
            print(row)

if __name__ == "__main__":
    asyncio.run(main())
