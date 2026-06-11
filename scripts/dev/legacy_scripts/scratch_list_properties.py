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
        
    print("\n--- Properties with Owner Details ---")
    props = await conn.fetch("SELECT p.id, p.name, p.property_type, p.owner_id, u.email, u.organization FROM properties p JOIN users u ON p.owner_id = u.id LIMIT 30;")
    for p in props:
        print(dict(p))
        
    print("\n--- Carbon Methodology counts ---")
    meth_counts = await conn.fetch("SELECT methodology_used, count(*) FROM carbon_calculations GROUP BY methodology_used;")
    for mc in meth_counts:
        print(dict(mc))
        
    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
