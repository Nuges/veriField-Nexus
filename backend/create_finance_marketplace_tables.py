import asyncio
import asyncpg
from app.core.config import settings

async def main():
    conn = await asyncpg.connect(str(settings.database_url).replace("postgresql+asyncpg", "postgresql"), statement_cache_size=0)
    
    await conn.execute("DROP TABLE IF EXISTS financial_transactions CASCADE;")
    await conn.execute("DROP TABLE IF EXISTS marketplace_listings CASCADE;")

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS financial_transactions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            from_org_id UUID NOT NULL,
            to_org_id UUID NOT NULL,
            amount DOUBLE PRECISION NOT NULL,
            currency VARCHAR(10) DEFAULT 'USD',
            project_id UUID,
            status VARCHAR(50) DEFAULT 'PENDING',
            metadata_json JSONB DEFAULT '{}'::jsonb,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        );
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS marketplace_listings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            org_id UUID NOT NULL,
            project_id UUID NOT NULL,
            quantity DOUBLE PRECISION NOT NULL,
            price_per_unit DOUBLE PRECISION NOT NULL,
            currency VARCHAR(10) DEFAULT 'USD',
            status VARCHAR(50) DEFAULT 'ACTIVE',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        );
    """)

    await conn.close()

asyncio.run(main())
