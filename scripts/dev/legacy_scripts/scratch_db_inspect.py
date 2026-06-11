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
    
    print("\n--- Users ---")
    users = await conn.fetch("SELECT id, email, role, sector, country, project_type, organization FROM users;")
    for u in users:
        print(dict(u))
        
    print("\n--- Properties ---")
    properties = await conn.fetch("SELECT id, name, property_type, owner_id FROM properties LIMIT 10;")
    for p in properties:
        print(dict(p))
        
    print("\n--- Activities ---")
    activities = await conn.fetch("SELECT id, user_id, activity_type, status, captured_at FROM activities LIMIT 10;")
    for a in activities:
        print(dict(a))
        
    print("\n--- Carbon Calculations ---")
    calculations = await conn.fetch("SELECT id, status, tco2e_generated FROM carbon_calculations LIMIT 10;")
    for c in calculations:
        print(dict(c))
        
    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
