import asyncio
import sys
import os
from dotenv import load_dotenv

load_dotenv('backend/.env')
sys.path.append(os.path.abspath('backend'))

from app.db.session import async_session_factory
from app.models.user import User
from sqlalchemy import select

async def main():
    print("=== Testing User Query ===")
    try:
        async with async_session_factory() as session:
            res = await session.execute(select(User))
            users = res.scalars().all()
            print("Successfully queried users! Count:", len(users))
    except Exception as e:
        print("Error querying users:", e)

if __name__ == "__main__":
    asyncio.run(main())
