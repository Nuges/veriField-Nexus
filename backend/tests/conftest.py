import os
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///test_default.db")
os.environ.setdefault("TESTING", "1")
os.environ.setdefault("JWT_SECRET", "test-secret-key-32-chars-minimum-for-testing")

from uuid import UUID
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.domains.authentication.models import User
from app.main import app

@pytest_asyncio.fixture(scope="session", autouse=True)
async def init_test_database():
    from app.db.base import Base
    from app.db.session import engine, async_session_factory
    from app.core.security import get_password_hash
    from sqlalchemy import text

    # Clean PostgreSQL server_default syntax for SQLite compatibility
    for table in Base.metadata.tables.values():
        for col in table.columns:
            if col.server_default is not None:
                sd_str = str(col.server_default.arg) if hasattr(col.server_default, 'arg') else ""
                if any(kw in sd_str.lower() for kw in ["gen_random_uuid", "jsonb", "now()", "true", "false", "::"]):
                    col.server_default = None

    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, checkfirst=True))

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS access_requests (
                id TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT,
                organization_name TEXT NOT NULL,
                country TEXT,
                use_case TEXT,
                sector_id TEXT,
                methodology_id TEXT,
                project_name TEXT,
                status TEXT NOT NULL DEFAULT 'PENDING',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_by TEXT,
                reviewed_at TIMESTAMP
            )
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS system_settings (
                id TEXT PRIMARY KEY,
                organization_id TEXT,
                gps_max_distance_km FLOAT DEFAULT 5.0,
                max_submissions_per_hour INTEGER DEFAULT 10,
                image_hash_threshold INTEGER DEFAULT 12,
                suspicious_hours_start INTEGER DEFAULT 2,
                suspicious_hours_end INTEGER DEFAULT 5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS document_chunks (
                id TEXT PRIMARY KEY,
                document_id TEXT,
                organization_id TEXT,
                project_id TEXT,
                sector_id TEXT,
                methodology_id TEXT,
                title TEXT,
                document_type TEXT,
                page_number INTEGER,
                section TEXT,
                chunk_index INTEGER,
                content TEXT,
                chunk_hash TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

    async with async_session_factory() as session:
        await session.execute(text("""
            INSERT OR IGNORE INTO system_settings (id, gps_max_distance_km, max_submissions_per_hour, image_hash_threshold, suspicious_hours_start, suspicious_hours_end)
            VALUES ('00000000-0000-0000-0000-000000000001', 5.0, 10, 12, 2, 5)
        """))

        await session.execute(text("""
            DELETE FROM users WHERE email != 'segunoluwole22@gmail.com' AND role = 'SUPER_ADMIN'
        """))

        pw_hash = get_password_hash("Lovelyday1")
        await session.execute(text("""
            INSERT OR REPLACE INTO users (id, email, full_name, role, status, is_active, password_hash, requires_password_change, version, is_deleted, created_at, updated_at)

            VALUES (
                '00000000-0000-0000-0000-000000000001',
                'segunoluwole22@gmail.com',
                'Segun Oluwole',
                'SUPER_ADMIN',
                'active',
                1,
                :pw_hash,
                0,
                1,
                0,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
        """), {"pw_hash": pw_hash})

        try:
            from app.domains.methodologies.metadata.seed_phase_1 import seed_data
            await seed_data(session)
        except Exception:
            pass

        await session.commit()


@pytest_asyncio.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client



@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    async with async_session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def admin_token_headers():
    from app.core.security import get_current_user

    async def override_get_current_user():
        return User(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            email="segunoluwole22@gmail.com",
            full_name="Segun Oluwole",
            role="SUPER_ADMIN",
            status="active",
            is_active=True,
        )

    app.dependency_overrides[get_current_user] = override_get_current_user

    yield {"Authorization": "Bearer TEST_TOKEN"}

    app.dependency_overrides.pop(get_current_user, None)




@pytest_asyncio.fixture(autouse=True)
async def cleanup_redis():
    from app.core.redis import close_redis

    yield
    await close_redis()
