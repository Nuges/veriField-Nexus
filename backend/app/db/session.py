"""

=============================================================================

VeriField Nexus — Database Session Management

=============================================================================

Async SQLAlchemy engine and session factory for connecting to Supabase

PostgreSQL. Provides the `get_db` dependency for FastAPI routes.

=============================================================================

"""



import os

import uuid
from typing import AsyncGenerator
from fastapi import HTTPException



from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,

                                    create_async_engine)



from app.core.config import settings



# Ensure the connection string uses the asyncpg driver and transaction pooler

db_url = settings.database_url

if db_url and db_url.startswith("postgres://"):

    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)

elif db_url and db_url.startswith("postgresql://"):

    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)



# --- Async Engine ---

# Creates a connection pool to Supabase PostgreSQL

# Tuned for PgBouncer transaction pooling or direct sessions

import sys



from sqlalchemy import pool



is_testing = "pytest" in sys.modules or os.environ.get("TESTING") == "1"



engine_kwargs = {

    "echo": settings.debug,

    "poolclass": pool.NullPool if is_testing else None,

    "pool_pre_ping": True if not is_testing else False,

    "connect_args": {

        "ssl": "require",

        "server_settings": {"jit": "off", "application_name": "verifield"},

        "command_timeout": 60.0,

        "statement_cache_size": 0,

        "prepared_statement_cache_size": 0,

        "prepared_statement_name_func": lambda: f"__asyncpg_{uuid.uuid4()}__",

    },

}



if not is_testing:

    engine_kwargs["pool_size"] = 15

    engine_kwargs["max_overflow"] = 30

    engine_kwargs["pool_timeout"] = 60

    engine_kwargs["pool_recycle"] = 1800

else:

    engine_kwargs["connect_args"].pop("ssl", None)



engine = create_async_engine(db_url, **engine_kwargs)



# --- Session Factory ---

# Creates new database sessions for each request

async_session_factory = async_sessionmaker(

    engine,

    class_=AsyncSession,

    expire_on_commit=False,  # Don't expire objects after commit

)





# Fallback SQLite Engine for offline/sandboxed execution (Lazy Initialized)

fallback_engine = None

fallback_session_factory = None



def _get_fallback_session_factory():

    global fallback_engine, fallback_session_factory

    if fallback_session_factory is None:

        fallback_db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../verifield_dev.db"))

        fallback_db_url = f"sqlite+aiosqlite:///{fallback_db_path}"

        fallback_engine = create_async_engine(fallback_db_url, echo=False)

        fallback_session_factory = async_sessionmaker(

            fallback_engine,

            class_=AsyncSession,

            expire_on_commit=False,

        )

    return fallback_session_factory



_fallback_initialized = False



from sqlalchemy.dialects.postgresql import JSONB, UUID

from sqlalchemy.ext.compiler import compiles



@compiles(JSONB, "sqlite")

def compile_jsonb_sqlite(type_, compiler, **kw):

    return "JSON"



@compiles(UUID, "sqlite")

def compile_uuid_sqlite(type_, compiler, **kw):

    return "TEXT"



async def _init_fallback_db():
    global _fallback_initialized
    if _fallback_initialized:
        return

    _get_fallback_session_factory()

    from app.db.base import Base
    from app.core.security import get_password_hash
    from sqlalchemy import text



    # Clean PostgreSQL server_default syntax for SQLite compatibility

    for table in Base.metadata.tables.values():

        for col in table.columns:

            if col.server_default is not None:

                sd_str = str(col.server_default.arg) if hasattr(col.server_default, 'arg') else ""

                if any(kw in sd_str.lower() for kw in ["gen_random_uuid", "jsonb", "now()", "true", "false"]):

                    col.server_default = None



    async with fallback_engine.begin() as conn:

        await conn.run_sync(Base.metadata.create_all)

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



    async with fallback_session_factory() as session:

        await session.execute(text("""

            INSERT OR IGNORE INTO system_settings (id, gps_max_distance_km, max_submissions_per_hour, image_hash_threshold, suspicious_hours_start, suspicious_hours_end)

            VALUES ('00000000-0000-0000-0000-000000000001', 5.0, 10, 12, 2, 5)

        """))

        pw_hash = get_password_hash("Lovelyday1")

        # Seed ONLY admin@verifield.io (Platform Admin)

        await session.execute(text("""

            INSERT OR REPLACE INTO users (id, email, full_name, role, status, is_active, password_hash, requires_password_change, version, is_deleted, created_at, updated_at)

            VALUES (

                '00000000-0000-0000-0000-000000000003',

                'admin@verifield.io',

                'VeriField Admin',

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

            await session.commit()

        except Exception as seed_err:

            print(f"Fallback DB methodology seed notice: {seed_err}")



        # Seed Metadata-Driven Role Catalogue

        roles_to_seed = [

            ("SUPER_ADMIN", "Platform Super Admin", "Global platform governance and administrative authority", "PLATFORM", 1),

            ("ORG_ADMIN", "Organization Administrator", "Tenant administration and user management within assigned organization", "ORGANIZATION", 1),

            ("PROJECT_MANAGER", "Project Manager", "Operational project configuration and team management", "PROJECT", 1),

            ("AUDITOR", "VVB Independent Auditor", "Read-only inspection and independent audit sign-off", "PROJECT", 1),

            ("COMPLIANCE_OFFICER", "Compliance Officer", "Regulatory compliance review and verification approvals", "PROJECT", 1),

            ("FIELD_SUPERVISOR", "Field Supervisor", "Field team supervision and activity review", "PROJECT", 1),

            ("FIELD_AGENT", "Field Data Capture Agent", "Field evidence collection and activity submission", "PROJECT", 1),

            ("QA_OFFICER", "QA Officer", "Quality assurance and photo anomaly review", "PROJECT", 1),

        ]

        for r_code, r_name, r_desc, r_scope, r_sys in roles_to_seed:

            await session.execute(text("""

                INSERT OR IGNORE INTO roles (id, code, name, description, scope, is_system)

                VALUES (:id, :code, :name, :desc, :scope, :is_sys)

            """), {

                "id": str(uuid.uuid4()),

                "code": r_code,

                "name": r_name,

                "desc": r_desc,

                "scope": r_scope,

                "is_sys": r_sys

            })



        await session.commit()

    _fallback_initialized = True





async def get_db() -> AsyncGenerator[AsyncSession, None]:

    """

    FastAPI dependency that provides a database session.

    Automatically falls back to local SQLite if remote PostgreSQL is unreachable.

    """

    try:

        async with async_session_factory() as session:

            # Test connection with a lightweight ping query

            await session.execute(text("SELECT 1"))

            try:
                yield session
            except HTTPException:
                await session.rollback()
                raise
            except Exception as err:
                await session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database session error: {type(err).__name__}: {str(err)}"
                )
            finally:
                await session.close()
            return
    except Exception as err:
        # Fallback to local SQLite when remote DB has network/DNS issues
        await _init_fallback_db()
        factory = _get_fallback_session_factory()
        async with factory() as session:
            try:
                yield session
            except HTTPException:
                await session.rollback()
                raise
            except Exception as inner_err:
                await session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Fallback database error: {type(inner_err).__name__}: {str(inner_err)}"
                )
            finally:
                await session.close()
