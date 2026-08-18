import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import traceback

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///dev.db")

async def test():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        try:
            # Let's count how many rows we can insert before it fails!
            # Oh wait, it inserts all or nothing. Let's just run it and see the exact exception.
            await conn.execute(text("""
                INSERT INTO activities (id, organization_id, user_id, property_id, asset_id, activity_type, activity_data, description, image_url, image_hash, latitude, longitude, gps_accuracy, environment_type, radius_used_m, duplicate_flag, override_reason, captured_at, submitted_at, trust_score, trust_flags, status, client_id, created_at, validation_status, validation_hash, is_locked, evidence_payload)
                SELECT id, COALESCE(organization_id, '00000000-0000-0000-0000-000000000000'::uuid), user_id, property_id, asset_id, activity_type, activity_data, description, image_url, image_hash, latitude, longitude, gps_accuracy, environment_type, radius_used_m, duplicate_flag, override_reason, captured_at, submitted_at, trust_score, trust_flags, status, client_id, COALESCE(created_at, now()), validation_status, validation_hash, is_locked, evidence_payload
                FROM activities_old
            """))
            print("Migration successful!")
        except Exception as e:
            print("Migration failed:")
            print(traceback.format_exc())

asyncio.run(test())
