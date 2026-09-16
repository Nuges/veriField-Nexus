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

        if "sqlite" in str(engine.url):
            for col_def in [
                ("soil_samples", "model_represents_30cm", "BOOLEAN DEFAULT 0"),
                ("soil_samples", "extrapolation_method", "TEXT"),
                ("tree_observations", "belowground_model_id", "TEXT"),
                ("tree_observations", "derived_belowground_biomass_kg", "FLOAT"),
                ("biochar_batches", "organization_id", "TEXT"),
                ("biochar_batches", "production_run_id", "TEXT"),
                ("biochar_batches", "dry_mass_tonnes", "FLOAT"),
                ("biochar_batches", "carbon_claim_project_id", "TEXT"),
                ("biochar_batches", "carbon_claim_registry", "TEXT"),
                ("biochar_batches", "carbon_claim_methodology", "TEXT"),
                ("biochar_batches", "mass_balance_allocated_tonnes", "FLOAT DEFAULT 0.0"),
                ("biochar_batches", "mass_balance_status", "TEXT DEFAULT 'IN_BALANCE'"),
                ("biochar_batches", "batch_digest_hash", "TEXT"),
                ("biochar_feedstock_lots", "dry_basis_derivation_method", "TEXT DEFAULT 'OVEN_DRY_BASIS_ASTM_D4442'"),
                # Puro Biochar 2025 V2 columns
                ("puro_end_use_categories", "application_type", "TEXT"),
                ("puro_end_use_categories", "min_environmental_quality", "TEXT"),
                ("puro_end_use_categories", "reversal_rules", "JSON DEFAULT '{}'"),
                ("puro_end_use_categories", "cascading_conditions", "JSON DEFAULT '{}'"),
                ("puro_end_use_categories", "reversal_discount_factor_required", "BOOLEAN DEFAULT 0"),
                ("puro_calculation_executions", "calculation_mode", "TEXT DEFAULT 'AUTHORITATIVE'"),
                ("puro_calculation_executions", "persistence_fraction_pf", "FLOAT DEFAULT 0.0"),
                ("puro_calculation_executions", "persistence_m_param", "FLOAT"),
                ("puro_calculation_executions", "persistence_a_param", "FLOAT"),
                ("puro_calculation_executions", "durability_class", "TEXT DEFAULT 'CORC200+'"),
                ("puro_calculation_executions", "e_ops_biomass_tco2e", "FLOAT DEFAULT 0.0"),
                ("puro_calculation_executions", "e_ops_production_tco2e", "FLOAT DEFAULT 0.0"),
                ("puro_calculation_executions", "e_ops_use_tco2e", "FLOAT DEFAULT 0.0"),
                ("puro_calculation_executions", "e_ops_total_tco2e", "FLOAT DEFAULT 0.0"),
                ("puro_calculation_executions", "e_emb_infra_tco2e", "FLOAT DEFAULT 0.0"),
                ("puro_calculation_executions", "e_emb_dluc_tco2e", "FLOAT DEFAULT 0.0"),
                ("puro_calculation_executions", "e_emb_annualized_tco2e", "FLOAT DEFAULT 0.0"),
                ("puro_calculation_executions", "leakage_eco_tco2e", "FLOAT DEFAULT 0.0"),
                ("puro_calculation_executions", "leakage_ma_tco2e", "FLOAT DEFAULT 0.0"),
                ("puro_calculation_executions", "leakage_iluc_tco2e", "FLOAT DEFAULT 0.0"),
                ("puro_calculation_executions", "reported_uncertainty_text", "TEXT"),
                ("puro_calculation_executions", "superseded_at", "TIMESTAMP"),
                ("puro_calculation_executions", "superseded_reason", "TEXT"),
                ("puro_calculation_executions", "replacement_engine_version", "TEXT"),
            ]:
                try:
                    await conn.execute(text(f"ALTER TABLE {col_def[0]} ADD COLUMN {col_def[1]} {col_def[2]}"))
                except Exception:
                    pass
        else:
            for col_sql in [
                "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS licensed_sectors JSONB DEFAULT '[]'::jsonb",
                "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS licensed_methodologies JSONB DEFAULT '[]'::jsonb",
                "ALTER TABLE projects ADD COLUMN IF NOT EXISTS sector_id UUID",
                "ALTER TABLE projects ALTER COLUMN methodology_id DROP NOT NULL",
                "ALTER TABLE methodology_families ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE",
                "ALTER TABLE methodology_families ADD COLUMN IF NOT EXISTS project_types JSONB DEFAULT '[]'::jsonb",
                "ALTER TABLE methodologies ADD COLUMN IF NOT EXISTS recommendation_rules JSONB DEFAULT '{}'::jsonb",
                "ALTER TABLE methodologies ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE",
                "ALTER TABLE methodology_monitoring_templates ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE",
                "ALTER TABLE emission_factor_registry ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE",
            ]:
                try:
                    await conn.execute(text(col_sql))
                except Exception:
                    pass


    async with async_session_factory() as session:
        if "sqlite" in str(engine.url):
            await session.execute(text("""
                INSERT OR IGNORE INTO system_settings (id, gps_max_distance_km, max_submissions_per_hour, image_hash_threshold, suspicious_hours_start, suspicious_hours_end)
                VALUES ('00000000-0000-0000-0000-000000000001', 5.0, 10, 12, 2, 5)
            """))
        else:
            await session.execute(text("""
                INSERT INTO system_settings (id, gps_max_distance_km, max_submissions_per_hour, image_hash_threshold, suspicious_hours_start, suspicious_hours_end)
                VALUES ('00000000-0000-0000-0000-000000000001', 5.0, 10, 12, 2, 5)
                ON CONFLICT (id) DO NOTHING
            """))

        from app.core.config import settings
        admin_email = settings.authorized_bootstrap_admin_email

        await session.execute(text("""
            DELETE FROM users WHERE email != :admin_email AND role = 'SUPER_ADMIN'
        """), {"admin_email": admin_email})

        pw_hash = get_password_hash("Lovelyday1")
        if "sqlite" in str(engine.url):
            await session.execute(text("""
                INSERT OR REPLACE INTO users (id, email, full_name, role, status, is_active, password_hash, requires_password_change, version, is_deleted, created_at, updated_at)
                VALUES (
                    '00000000-0000-0000-0000-000000000001',
                    :admin_email,
                    'Platform Super Admin',
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
            """), {"admin_email": admin_email, "pw_hash": pw_hash})
        else:
            await session.execute(text("""
                INSERT INTO users (id, email, full_name, role, status, is_active, password_hash, requires_password_change, version, is_deleted, created_at, updated_at)
                VALUES (
                    '00000000-0000-0000-0000-000000000001',
                    :admin_email,
                    'Platform Super Admin',
                    'SUPER_ADMIN',
                    'active',
                    true,
                    :pw_hash,
                    false,
                    1,
                    false,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                )
                ON CONFLICT (id) DO UPDATE SET
                    email = EXCLUDED.email,
                    role = EXCLUDED.role,
                    password_hash = EXCLUDED.password_hash,
                    is_active = true
            """), {"admin_email": admin_email, "pw_hash": pw_hash})

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
    from app.core.config import settings

    async def override_get_current_user():
        return User(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            email=settings.authorized_bootstrap_admin_email,
            full_name="Platform Super Admin",
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
