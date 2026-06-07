import asyncio
import sys
import os
from dotenv import load_dotenv

load_dotenv('backend/.env')
sys.path.append(os.path.abspath('backend'))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.models.user import User
from sqlalchemy import select

async def main():
    print("=== Testing User Query without Prepared Statements ===")
    db_url = os.getenv('DATABASE_URL')
    db_url = db_url.replace("aws-0-eu-west-1.pooler.supabase.com", "34.241.16.247")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        
    if "?" not in db_url:
        db_url += "?prepared_statement_cache_size=0"
    else:
        db_url += "&prepared_statement_cache_size=0"
        
    engine = create_async_engine(db_url)
    async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    import time
    start = time.time()
    try:
        async with async_session_factory() as session:
            res = await session.execute(select(User))
            users = res.scalars().all()
            print(f"Successfully queried users! Count: {len(users)}")
            print(f"Time taken: {time.time() - start:.2f} seconds")
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    asyncio.run(main())
