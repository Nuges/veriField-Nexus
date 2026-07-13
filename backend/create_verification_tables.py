import asyncio
import asyncpg
from app.core.config import settings

async def main():
    conn = await asyncpg.connect(str(settings.database_url).replace("postgresql+asyncpg", "postgresql"), statement_cache_size=0)
    
    await conn.execute("DROP TABLE IF EXISTS verification_tasks CASCADE;")
    await conn.execute("DROP TABLE IF EXISTS audit_reports CASCADE;")

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS verification_tasks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id UUID NOT NULL,
            verifier_id UUID,
            status VARCHAR(50) DEFAULT 'ASSIGNED',
            findings JSONB DEFAULT '{}'::jsonb,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        );
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_reports (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id UUID NOT NULL,
            vvb_org_id UUID NOT NULL,
            report_uri VARCHAR(500) NOT NULL,
            report_hash VARCHAR(64) NOT NULL,
            is_positive_opinion BOOLEAN NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        );
    """)

    await conn.close()

asyncio.run(main())
