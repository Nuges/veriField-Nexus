"""
=============================================================================
VeriField Nexus — User Seeder
=============================================================================
Seeds the single authorized platform Super Admin account.
Only segunoluwole22@gmail.com may hold the SUPER_ADMIN role.
Other users should be provisioned via the governance API.
=============================================================================
"""

import asyncio
import os
from app.db.session import async_session_factory
from app.core.security import get_password_hash
from sqlalchemy import text

AUTHORIZED_SUPER_ADMIN_EMAIL = "segunoluwole22@gmail.com"
AUTHORIZED_SUPER_ADMIN_ID = "00000000-0000-0000-0000-000000000001"

async def seed():
    """Seed only the authorized Super Admin account."""
    async with async_session_factory() as session:
        # Password configured securely through environment variable.
        seed_password = os.environ.get("SUPER_ADMIN_PASSWORD", os.environ.get("SEED_ADMIN_PASSWORD", "VeriField_Dev_2026!"))
        pw_hash = get_password_hash(seed_password)

        await session.execute(
            text("""
            INSERT INTO users (id, email, full_name, role, status, is_active, password_hash, requires_password_change, created_at, updated_at)
            VALUES (
                :id,
                :email,
                'Segun Oluwole',
                'SUPER_ADMIN',
                'active',
                true,
                :pw_hash,
                true,
                now(),
                now()
            )
            ON CONFLICT (email) DO UPDATE SET password_hash = :pw_hash, requires_password_change = true;
            """),
            {"id": AUTHORIZED_SUPER_ADMIN_ID, "email": AUTHORIZED_SUPER_ADMIN_EMAIL, "pw_hash": pw_hash},
        )
        await session.commit()
        print(f"Super Admin ({AUTHORIZED_SUPER_ADMIN_EMAIL}) seeded successfully.")

asyncio.run(seed())
