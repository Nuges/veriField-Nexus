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
    
    print("\n--- Carbon Calculations ---")
    calcs = await conn.fetch("""
        SELECT c.id, c.activity_id, c.methodology_used, c.tco2e_generated, c.status,
               u.email as user_email, u.organization
        FROM carbon_calculations c
        JOIN activities a ON c.activity_id = a.id
        JOIN users u ON a.user_id = u.id;
    """)
    print(f"Calculations found: {len(calcs)}")
    for c in calcs:
        print(dict(c))
        
    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
