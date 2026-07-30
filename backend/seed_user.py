import asyncio
from app.db.session import async_session_factory
from app.core.security import get_password_hash
from sqlalchemy import text
import uuid

async def seed():
    async with async_session_factory() as session:
        pw_hash = get_password_hash("Lovelyday1")
        emails = [
            ("segun@example.invalid", "Segun Oluwole"),
            ("phil@example.invalid", "Phil Admin"),
            ("admin@verifield.io", "VeriField Admin")
        ]
        for email, name in emails:
            user_id = str(uuid.uuid4())
            await session.execute(
                text("""
                INSERT INTO users (id, email, full_name, role, status, is_active, password_hash, requires_password_change, created_at, updated_at)
                VALUES (
                    :id,
                    :email,
                    :name,
                    'SUPER_ADMIN',
                    'active',
                    true,
                    :pw_hash,
                    false,
                    now(),
                    now()
                )
                ON CONFLICT (email) DO UPDATE SET password_hash = :pw_hash;
                """),
                {"id": user_id, "email": email, "name": name, "pw_hash": pw_hash},
            )
        await session.commit()
        print("Users seeded successfully!")

asyncio.run(seed())
