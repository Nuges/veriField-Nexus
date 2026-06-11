import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv('backend/.env')

async def main():
    db_url = os.getenv('DATABASE_URL')
    if db_url.startswith('postgresql+asyncpg://'):
        db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
        
    print("Connecting to Supabase...")
    conn = await asyncpg.connect(db_url)
    print("=== Connected ===")
    
    print("\n--- Active Queries ---")
    queries = await conn.fetch("""
        SELECT pid, age(clock_timestamp(), query_start) as duration, state, query 
        FROM pg_stat_activity 
        WHERE state != 'idle' AND pid != pg_backend_pid();
    """)
    for q in queries:
        print(dict(q))
        
    print("\n--- Locks on Tables ---")
    locks = await conn.fetch("""
        SELECT 
            coalesce(t.relname, 'None') AS table_name,
            l.mode,
            l.granted,
            l.pid,
            a.query
        FROM pg_locks l
        LEFT JOIN pg_class t ON l.relation = t.oid
        JOIN pg_stat_activity a ON l.pid = a.pid
        WHERE l.pid != pg_backend_pid() AND t.relname IS NOT NULL;
    """)
    for l in locks:
        print(dict(l))
        
    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
