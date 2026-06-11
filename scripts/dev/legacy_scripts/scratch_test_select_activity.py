import asyncio
import sys
import os
from dotenv import load_dotenv

load_dotenv('backend/.env')
sys.path.append(os.path.abspath('backend'))

from app.db.session import async_session_factory
from app.models.activity import Activity
from sqlalchemy import select

async def main():
    print("=== Testing Activity Query ===")
    import time
    start = time.time()
    try:
        async with async_session_factory() as session:
            res = await session.execute(
                select(Activity).where(Activity.activity_type == "HYBRID_ENERGY")
            )
            activities = res.scalars().all()
            print(f"Successfully queried HYBRID_ENERGY activities! Count: {len(activities)}")
            print(f"Time taken: {time.time() - start:.2f} seconds")
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    asyncio.run(main())
