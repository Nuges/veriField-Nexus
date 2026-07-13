import asyncio
import asyncpg
from app.core.config import settings

async def main():
    conn = await asyncpg.connect(str(settings.database_url).replace("postgresql+asyncpg", "postgresql"), statement_cache_size=0)
    
    try:
        await conn.execute("ALTER TABLE climate_programmes ADD COLUMN version INTEGER NOT NULL DEFAULT 1;")
    except asyncpg.exceptions.DuplicateColumnError:
        pass
        
    await conn.close()

asyncio.run(main())
