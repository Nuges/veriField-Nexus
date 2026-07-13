import asyncio
import asyncpg
from app.core.config import settings

async def main():
    conn = await asyncpg.connect(str(settings.database_url).replace("postgresql+asyncpg", "postgresql"), statement_cache_size=0)
    
    await conn.execute("DROP TABLE IF EXISTS climate_programmes CASCADE;")
    
    await conn.execute("""
        CREATE TABLE climate_programmes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL,
            org_id UUID NOT NULL,
            jurisdiction_id UUID REFERENCES jurisdictions(id),
            funding_sources JSONB NOT NULL DEFAULT '[]'::jsonb,
            budget FLOAT NOT NULL DEFAULT 0.0,
            status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
            version INTEGER NOT NULL DEFAULT 1,
            is_deleted BOOLEAN DEFAULT false,
            deleted_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        );
    """)

    await conn.close()

asyncio.run(main())
