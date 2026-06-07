import asyncio
import asyncpg
import os
from dotenv import load_dotenv
load_dotenv('backend/.env')

async def set_rls():
    db_url = os.getenv('DATABASE_URL').replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(db_url)
    print("Connected to Supabase DB")
    
    # Policy to allow public uploads to activity-photos
    sql = """
    CREATE POLICY "Allow public uploads to activity-photos" 
    ON storage.objects FOR INSERT 
    WITH CHECK ( bucket_id = 'activity-photos' );
    """
    try:
        await conn.execute(sql)
        print("Policy created successfully!")
    except Exception as e:
        print("Error creating policy:", e)
        
    await conn.close()

asyncio.run(set_rls())
