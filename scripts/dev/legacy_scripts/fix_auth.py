import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///dev.db")

async def test():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        res = await conn.execute(text("SELECT id, password_hash, role FROM users WHERE email = 'dami@gmail.com'"))
        user = res.fetchone()
        if user:
            print(f"Found user: {user.id}")
            # Insert into auth.users
            await conn.execute(text(f"""
                INSERT INTO auth.users (
                    instance_id, id, aud, role, email, encrypted_password,
                    email_confirmed_at, created_at, updated_at, raw_user_meta_data
                ) VALUES (
                    '00000000-0000-0000-0000-000000000000', '{user.id}'::uuid, 'authenticated', 'authenticated', 'dami@gmail.com', '{user.password_hash}',
                    now(), now(), now(), '{{"role": "super-admin"}}'::jsonb
                )
                ON CONFLICT (id) DO NOTHING
            """))

            # also insert into auth.identities
            await conn.execute(text(f"""
                INSERT INTO auth.identities (
                    provider_id, id, user_id, identity_data, provider, last_sign_in_at, created_at, updated_at
                ) VALUES (
                    '{user.id}', gen_random_uuid(), '{user.id}'::uuid, jsonb_build_object('sub', '{user.id}', 'email', 'dami@gmail.com'), 'email', now(), now(), now()
                )
                ON CONFLICT DO NOTHING
            """))
            print("Inserted into auth.users and auth.identities")
        else:
            print("User not found in public.users")

asyncio.run(test())
