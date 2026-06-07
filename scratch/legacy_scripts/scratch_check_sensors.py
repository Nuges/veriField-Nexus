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
    
    count = await conn.fetchval("SELECT count(*) FROM sensor_readings;")
    print(f"Total Sensor Readings: {count}")
    
    if count > 0:
        rows = await conn.fetch("SELECT id, asset_id, device_id, temperature, usage_flag, timestamp FROM sensor_readings LIMIT 5;")
        print("\n--- Sample Sensor Readings ---")
        for r in rows:
            print(dict(r))
            
        device_summary = await conn.fetch("""
            SELECT device_id, count(*) as count, 
                   sum(case when usage_flag = true then 1 else 0 end) as usage_true_count
            FROM sensor_readings 
            GROUP BY device_id;
        """)
        print("\n--- Device Summary ---")
        for dev in device_summary:
            print(dict(dev))
    else:
        print("No sensor readings found.")
        
    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
