import asyncio
import asyncpg
from app.core.config import settings

async def main():
    conn = await asyncpg.connect(str(settings.database_url).replace("postgresql+asyncpg", "postgresql"), statement_cache_size=0)
    
    try:
        await conn.execute("ALTER TABLE users ADD COLUMN is_deleted BOOLEAN NOT NULL DEFAULT FALSE;")
        await conn.execute("ALTER TABLE users ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE;")
        print("Added is_deleted and deleted_at columns")
    except Exception as e:
        print(e)
        
    await conn.close()

asyncio.run(main())
