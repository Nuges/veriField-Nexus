import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv('backend/.env')

async def main():
    db_url = os.getenv('DATABASE_URL')
    if db_url.startswith('postgresql+asyncpg://'):
        db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
    
    conn = await asyncpg.connect(db_url)
    print("=== Connected to DB ===")
    
    print("\n--- Property Type counts ---")
    types = await conn.fetch("SELECT property_type, count(*) FROM properties GROUP BY property_type;")
    for t in types:
        print(dict(t))
        
    print("\n--- Sample Properties ---")
    props = await conn.fetch("SELECT id, name, property_type FROM properties LIMIT 20;")
    for p in props:
        print(dict(p))
        
    print("\n--- Activity Type counts ---")
    act_types = await conn.fetch("SELECT activity_type, count(*) FROM activities GROUP BY activity_type;")
    for at in act_types:
        print(dict(at))
        
    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
