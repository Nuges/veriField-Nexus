import asyncio
import asyncpg
from app.core.config import settings

async def main():
    conn = await asyncpg.connect(str(settings.database_url).replace("postgresql+asyncpg", "postgresql"), statement_cache_size=0)
    
    await conn.execute("DROP TABLE IF EXISTS evidence_records CASCADE;")
    
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS evidence_records (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            activity_id UUID NOT NULL,
            file_uri VARCHAR(500) NOT NULL,
            file_hash VARCHAR(64) NOT NULL,
            status VARCHAR(20) DEFAULT 'PENDING',
            evidence_type VARCHAR(50) NOT NULL,
            metadata_json JSONB DEFAULT '{}'::jsonb,
            uploaded_by UUID REFERENCES users(id) ON DELETE SET NULL,
            verified_by UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        );
    """)

    await conn.close()

asyncio.run(main())
