import asyncio
import asyncpg
import os
import time
from dotenv import load_dotenv

load_dotenv('backend/.env')

async def main():
    db_url = os.getenv('DATABASE_URL')
    if db_url.startswith('postgresql+asyncpg://'):
        db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
        
    print("=== Testing Raw asyncpg Connection ===")
    try:
        start = time.time()
        conn = await asyncpg.connect(db_url)
        print(f"Connected in {time.time() - start:.2f} seconds")
        
        start_q = time.time()
        res = await conn.fetch("SELECT id FROM users;")
        print(f"Queried {len(res)} users in {time.time() - start_q:.2f} seconds")
        
        await conn.close()
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    asyncio.run(main())
