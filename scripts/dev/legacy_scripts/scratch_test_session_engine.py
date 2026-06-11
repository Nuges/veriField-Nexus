import asyncio
import sys
import os
from dotenv import load_dotenv

load_dotenv('backend/.env')
sys.path.append(os.path.abspath('backend'))

from app.db.session import engine
from sqlalchemy import text

async def main():
    print("=== Testing DB engine connection ===")
    try:
        async with engine.connect() as conn:
            res = await conn.execute(text("SELECT 1"))
            print("Successfully queried database:", res.scalar())
    except Exception as e:
        print("Failed to query database:", e)

if __name__ == "__main__":
    asyncio.run(main())
