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
    
    print("=== Database Row Counts ===")
    tables = ['users', 'properties', 'activities', 'carbon_calculations', 'sensor_readings', 'trust_logs', 'anomaly_flags']
    for t in tables:
        try:
            cnt = await conn.fetchval(f"SELECT count(*) FROM {t};")
            print(f"Table '{t}': {cnt} rows")
        except Exception as e:
            print(f"Table '{t}': Error {e}")
            
    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
