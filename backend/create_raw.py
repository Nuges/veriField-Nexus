import asyncio
import asyncpg
from app.core.config import settings

async def main():
    conn = await asyncpg.connect(str(settings.database_url).replace("postgresql+asyncpg", "postgresql"), statement_cache_size=0)
    
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS registry_configs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(100) NOT NULL UNIQUE,
            adapter_type VARCHAR(50) NOT NULL,
            base_url VARCHAR(255),
            is_active BOOLEAN DEFAULT TRUE,
            credentials JSONB DEFAULT '{}'::jsonb,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        );
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS registry_sync_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            registry_id UUID REFERENCES registry_configs(id) ON DELETE CASCADE,
            project_id UUID,
            action VARCHAR(50) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            idempotency_key VARCHAR(100) NOT NULL UNIQUE,
            request_payload JSONB,
            response_payload JSONB,
            error_message VARCHAR,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        );
    """)

    await conn.close()

asyncio.run(main())
