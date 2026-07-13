import asyncio
import asyncpg
from app.core.config import settings

async def main():
    conn = await asyncpg.connect(str(settings.database_url).replace("postgresql+asyncpg", "postgresql"), statement_cache_size=0)
    
    try:
        await conn.execute("ALTER TABLE users ADD COLUMN meta_data JSONB;")
        print("Added meta_data column")
    except Exception as e:
        print(e)
        
    await conn.close()

asyncio.run(main())
