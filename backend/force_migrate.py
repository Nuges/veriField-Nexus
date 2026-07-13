import asyncio
import asyncpg
from app.core.config import settings

async def run():
    db_url = settings.database_url
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgres://", 1)
    elif db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgres://", 1)
    print(f"Connecting to {db_url}...")
    conn = await asyncpg.connect(db_url)
    try:
        print("Adding columns to organizations table...")
        await conn.execute("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS parent_id UUID REFERENCES organizations(id);")
        await conn.execute("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS metadata_context JSONB NOT NULL DEFAULT '{}'::jsonb;")
        await conn.execute("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1;")
        await conn.execute("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT false;")
        await conn.execute("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE;")
        print("Success.")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(run())
