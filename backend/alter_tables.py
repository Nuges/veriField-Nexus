import asyncio
from sqlalchemy import text
from app.db.session import async_session_factory

async def main():
    async with async_session_factory() as session:
        queries = [
            "ALTER TABLE jurisdictions ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1",
            "ALTER TABLE jurisdictions ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE",
            "ALTER TABLE jurisdictions ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE",
            "ALTER TABLE jurisdictions ADD COLUMN IF NOT EXISTS meta_data JSONB DEFAULT '{}'::jsonb",

            "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1",
            "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE",
            "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE",
            "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS meta_data JSONB DEFAULT '{}'::jsonb",
        ]
        for query in queries:
            try:
                await session.execute(text(query))
            except Exception as e:
                print(f"Failed to execute {query}: {e}")
        await session.commit()
    print("Migration complete.")

if __name__ == "__main__":
    asyncio.run(main())
