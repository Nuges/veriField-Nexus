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
    
    print("\n--- Active Queries ---")
    queries = await conn.fetch("""
        SELECT pid, state, query, age(clock_timestamp(), query_start) as age 
        FROM pg_stat_activity 
        WHERE state != 'idle' AND pid != pg_backend_pid();
    """)
    for q in queries:
        print(dict(q))
        
    print("\n--- Locks ---")
    locks = await conn.fetch("""
        SELECT 
            coalesce(t.schemaname, '') || '.' || coalesce(t.relname, '') as relation,
            l.mode,
            l.locktype,
            l.granted,
            a.pid,
            a.query
        FROM pg_locks l
        JOIN pg_stat_activity a ON a.pid = l.pid
        LEFT JOIN pg_stat_user_tables t ON t.relid = l.relation
        WHERE a.pid != pg_backend_pid();
    """)
    for l in locks:
        print(dict(l))
        
    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
