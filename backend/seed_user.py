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
from datetime import datetime, timezone
from uuid import UUID
from app.db.session import async_session_factory
from app.core.security import get_password_hash
from app.domains.authentication.models import User
from sqlalchemy import select

AUTHORIZED_SUPER_ADMIN_EMAIL = "segunoluwole22@gmail.com"
AUTHORIZED_SUPER_ADMIN_ID = "00000000-0000-0000-0000-000000000001"

async def seed():
    """Seed only the authorized Super Admin account."""
    async with async_session_factory() as session:
        seed_password = os.environ.get("SUPER_ADMIN_PASSWORD", os.environ.get("SEED_ADMIN_PASSWORD", "VeriField_Dev_2026!"))
        pw_hash = get_password_hash(seed_password)

        res = await session.execute(select(User).where(User.email == AUTHORIZED_SUPER_ADMIN_EMAIL))
        user = res.scalar_one_or_none()

        if user:
            user.password_hash = pw_hash
            user.role = "SUPER_ADMIN"
            user.status = "active"
            user.is_active = True
            user.requires_password_change = False
            user.updated_at = datetime.now(timezone.utc)
        else:
            user = User(
                id=UUID(AUTHORIZED_SUPER_ADMIN_ID),
                email=AUTHORIZED_SUPER_ADMIN_EMAIL,
                full_name="Segun Oluwole",
                role="SUPER_ADMIN",
                status="active",
                is_active=True,
                password_hash=pw_hash,
                requires_password_change=False,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(user)

        await session.commit()
        print(f"Super Admin ({AUTHORIZED_SUPER_ADMIN_EMAIL}) seeded successfully with role SUPER_ADMIN.")

if __name__ == "__main__":
    asyncio.run(seed())

