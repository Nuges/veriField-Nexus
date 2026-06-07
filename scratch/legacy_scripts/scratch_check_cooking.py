import asyncio
import asyncpg
import os
import json
from dotenv import load_dotenv

load_dotenv('backend/.env')

async def main():
    db_url = os.getenv('DATABASE_URL')
    if db_url.startswith('postgresql+asyncpg://'):
        db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
    
    conn = await asyncpg.connect(db_url)
    print("=== Connected to DB ===")
    
    print("\n--- Cooking Activities ---")
    rows = await conn.fetch("SELECT id, activity_data, status, captured_at FROM activities WHERE activity_type='cooking' LIMIT 10;")
    for r in rows:
        print(r['id'], r['activity_data'])
        
    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
