"""
=============================================================================
VeriField Nexus — FastAPI Application Entry Point
=============================================================================
Main application configuration with CORS, routers, health check,
and lifespan events for database setup.
=============================================================================
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.domains.activities.api import router as activities_domain_router
from app.domains.assets.api import router as assets_domain_router
from app.domains.ai_trust_engine.api import router as ai_trust_engine_router
from app.domains.authentication.api import router as auth_domain_router
from app.domains.data_governance.routers.metadata import \
    router as data_governance_router
from app.domains.digital_twins.api import router as digital_twins_router
from app.domains.evidence.api import router as evidence_router
from app.domains.finance.api import router as finance_router
from app.domains.hardware.api import router as hardware_router
from app.domains.jurisdictions.api import router as jurisdictions_router
from app.domains.ledger.api import router as ledger_router
from app.domains.marketplace.api import router as marketplace_router
# from app.api.v1 import (
#     community,
#     access_requests,
#     registry,
#     settings as api_settings,
# )
from app.domains.methodologies.routers import methodology as methodology_router
from app.domains.methodologies.routers import csink as csink_router
from app.domains.notifications.api import router as notifications_router
from app.domains.observability.api import router as observability_router
from app.domains.organizations.api import router as organizations_domain_router
from app.domains.organizations.routers.access_requests import router as access_requests_router
from app.domains.programmes.api import router as programmes_router
from app.domains.projects.api import router as projects_domain_router
# Migrated Domain Routers
from app.domains.registry_integrations.api import router as registry_router
from app.domains.reporting.api import router as reporting_router
from app.domains.verification.api import router as verification_router
from app.domains.workspaces.api import router as properties_domain_router
from app.domains.community.api import router as community_router
from app.domains.energy.api import router as energy_router
from app.domains.system_settings.api import router as system_settings_router
from app.domains.analytics.api import router as analytics_router


# ---------------------------------------------------------------------------
# Lifespan — runs on startup and shutdown
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    - Startup: Start background scheduler and pre-warm DB connection pool.
    - Shutdown: Stop scheduler and cleanly dispose engine.
    """
    # Startup
    # from app.services.job_scheduler import start_scheduler, shutdown_scheduler
    import asyncio
    import logging

    from sqlalchemy import text

    from app.db.session import async_session_factory

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("verifield.startup")

    # 1. Initialize Climate Infrastructure Operating System Plugins

    # 2. Asynchronously Pre-warm the Connection Pool in the background
    async def prewarm_pool():
        logger.info(
            "Initializing database connection pool pre-warming and schema migrations..."
        )

        # Validate Supabase Admin Key Configuration
        import jwt as pyjwt

        admin_key = settings.supabase_admin_key
        if admin_key:
            try:
                decoded = pyjwt.decode(admin_key, options={"verify_signature": False})
                role = decoded.get("role")
                if role != "service_role":
                    logger.error(
                        "CRITICAL CONFIGURATION WARNING: The resolved Supabase Admin Key has role '%s', "
                        "but 'service_role' is required. Admin features (agent provisioning, password resets) WILL FAIL. "
                        "Please set the 'SUPABASE_SERVICE_ROLE_KEY' environment variable in your Render dashboard.",
                        role,
                    )
                else:
                    logger.info(
                        "Supabase Admin Key (service_role) validated successfully."
                    )
            except Exception as e:
                logger.warning("Could not verify Supabase admin key role format: %s", e)
        else:
            logger.error(
                "CRITICAL CONFIGURATION ERROR: Supabase Admin Key is empty. "
                "Admin features (agent provisioning, password resets) WILL FAIL. "
                "Please configure 'SUPABASE_SERVICE_ROLE_KEY' in your environment."
            )

        try:
            async with async_session_factory() as session:
                # Set a local lock timeout of 3s to prevent hanging startup migrations
                await session.execute(text("SET LOCAL lock_timeout = 3000"))
                # Add upvotes column to community_validations if missing
                await session.execute(
                    text(
                        "ALTER TABLE community_validations ADD COLUMN IF NOT EXISTS upvotes INTEGER DEFAULT 0"
                    )
                )
                # Create community_comments table if missing
                await session.execute(text("""
                    CREATE TABLE IF NOT EXISTS community_comments (
                        id UUID PRIMARY KEY,
                        validation_id UUID NOT NULL REFERENCES community_validations(id) ON DELETE CASCADE,
                        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        comment VARCHAR(500) NOT NULL,
                        timestamp TIMESTAMP WITH TIME ZONE NOT NULL
                    )
                """))
                # Alter system_settings for the new thresholds
                await session.execute(text("""
                    CREATE TABLE IF NOT EXISTS system_settings (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        organization_id UUID NULL REFERENCES organizations(id) ON DELETE CASCADE,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
                    )
                """))
                
                await session.execute(text("ALTER TABLE verification_tasks ADD COLUMN IF NOT EXISTS asset_id UUID"))
                await session.execute(text("ALTER TABLE verification_tasks ADD COLUMN IF NOT EXISTS deadline TIMESTAMP WITH TIME ZONE"))
                await session.execute(text("ALTER TABLE verification_tasks ALTER COLUMN project_id DROP NOT NULL"))

                await session.execute(
                    text(
                        "ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS gps_max_distance_km FLOAT DEFAULT 5.0"
                    )
                )
                await session.execute(
                    text(
                        "ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS max_submissions_per_hour INTEGER DEFAULT 10"
                    )
                )
                await session.execute(
                    text(
                        "ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS image_hash_threshold INTEGER DEFAULT 12"
                    )
                )
                await session.execute(
                    text(
                        "ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS suspicious_hours_start INTEGER DEFAULT 2"
                    )
                )
                await session.execute(
                    text(
                        "ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS suspicious_hours_end INTEGER DEFAULT 5"
                    )
                )
                await session.commit()
                logger.info(
                    "Community upvotes and comments database schema updates synced successfully!"
                )

                # === Project Configuration Layer (3-Layer MRV Architecture) ===
                # Re-apply lock timeout for the new transaction block
                await session.execute(text("SET LOCAL lock_timeout = 3000"))
                await session.execute(
                    text(
                        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS project_code VARCHAR(20) UNIQUE"
                    )
                )
                await session.execute(
                    text(
                        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS country VARCHAR(100) DEFAULT 'Nigeria'"
                    )
                )
                await session.execute(
                    text(
                        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS baseline_source VARCHAR(30) DEFAULT 'diesel_generator'"
                    )
                )
                await session.execute(
                    text(
                        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS diesel_emission_factor FLOAT DEFAULT 2.68"
                    )
                )
                await session.execute(
                    text(
                        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS grid_emission_factor FLOAT DEFAULT 0.7"
                    )
                )
                await session.execute(
                    text(
                        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS crediting_start DATE"
                    )
                )
                await session.execute(
                    text(
                        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS crediting_end DATE"
                    )
                )
                await session.execute(
                    text(
                        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now()"
                    )
                )
                # Add index on project_code for fast lookups
                await session.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_projects_project_code ON projects (project_code)"
                    )
                )
                
                # CIOS architecture addition
                await session.execute(
                    text(
                        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS sector_id UUID REFERENCES methodology_families(id) ON DELETE RESTRICT"
                    )
                )
                
                await session.commit()
                logger.info("Project configuration schema synced successfully!")

                # === Strict Multi-Module Isolation Schema Updates ===
                # Legacy migrations removed in CIOS refactor
                logger.info("Legacy multi-module database migrations skipped.")

                # === SaaS Multi-Tenancy Governance Schema Updates ===
                # Re-apply lock timeout for the new transaction block
                await session.execute(text("SET LOCAL lock_timeout = 3000"))
                logger.info("Syncing SaaS multi-tenancy schema updates...")
                await session.execute(text("""
                    CREATE TABLE IF NOT EXISTS organizations (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        name VARCHAR(255) NOT NULL UNIQUE,
                        created_by UUID NULL,
                        status VARCHAR(20) DEFAULT 'ACTIVE',
                        version INTEGER DEFAULT 1,
                        is_deleted BOOLEAN DEFAULT FALSE,
                        deleted_at TIMESTAMP WITH TIME ZONE,
                        meta_data JSONB DEFAULT '{}'::jsonb,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
                    )
                """))
                await session.execute(
                    text(
                        "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS plan VARCHAR(30) DEFAULT 'FREE'"
                    )
                )
                await session.execute(
                    text(
                        "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS max_installations INTEGER DEFAULT 100"
                    )
                )
                await session.execute(
                    text(
                        "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS max_agents INTEGER DEFAULT 5"
                    )
                )
                await session.execute(
                    text(
                        "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS api_calls_count INTEGER DEFAULT 0"
                    )
                )

                # Architecture fields for Domain 3
                await session.execute(
                    text(
                        "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS type VARCHAR(50) DEFAULT 'DEVELOPER'"
                    )
                )
                await session.execute(
                    text(
                        "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS parent_id UUID REFERENCES organizations(id)"
                    )
                )
                await session.execute(
                    text(
                        "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS metadata_context JSONB NOT NULL DEFAULT '{}'::jsonb"
                    )
                )
                await session.execute(
                    text(
                        "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1"
                    )
                )
                await session.execute(
                    text(
                        "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT false"
                    )
                )
                await session.execute(
                    text(
                        "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE"
                    )
                )
                await session.execute(text("""
                    CREATE TABLE IF NOT EXISTS access_requests (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        full_name VARCHAR(255) NOT NULL,
                        email VARCHAR(255) NOT NULL,
                        phone VARCHAR(20) NULL,
                        organization_name VARCHAR(255) NOT NULL,
                        country VARCHAR(100) NULL,
                        use_case VARCHAR(500) NULL,
                        status VARCHAR(20) DEFAULT 'PENDING',
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                        reviewed_by UUID NULL,
                        reviewed_at TIMESTAMP WITH TIME ZONE NULL
                    )
                """))

                # Update users table structure for SaaS capability
                await session.execute(
                    text(
                        "ALTER TABLE users ADD COLUMN IF NOT EXISTS organization_id UUID NULL REFERENCES organizations(id) ON DELETE SET NULL"
                    )
                )
                await session.execute(
                    text(
                        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true"
                    )
                )
                await session.execute(
                    text(
                        "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255) NULL"
                    )
                )
                await session.execute(
                    text(
                        "ALTER TABLE users ADD COLUMN IF NOT EXISTS requires_password_change BOOLEAN DEFAULT false"
                    )
                )
                await session.commit()

                # === CIOS Pluggable Infrastructure Schema Updates ===
                logger.info("Syncing CIOS pluggable infrastructure schema...")
                await session.execute(text("SET LOCAL lock_timeout = 3000"))
                await session.execute(
                    text(
                        "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS licensed_methodologies JSONB DEFAULT '[]'::jsonb"
                    )
                )
                await session.execute(
                    text(
                        "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS licensed_sectors JSONB DEFAULT '[]'::jsonb"
                    )
                )
                await session.execute(text("""
                    CREATE TABLE IF NOT EXISTS assets (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
                        project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                        name VARCHAR(255) NOT NULL,
                        asset_type VARCHAR(50) NOT NULL,
                        status VARCHAR(50) DEFAULT 'active',
                        latitude FLOAT NULL,
                        longitude FLOAT NULL,
                        attributes JSONB NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
                    )
                """))
                await session.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_assets_asset_type ON assets (asset_type)"
                    )
                )
                await session.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_assets_organization_id ON assets (organization_id)"
                    )
                )
                await session.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_assets_project_id ON assets (project_id)"
                    )
                )
                await session.execute(
                    text(
                        "ALTER TABLE activities ADD COLUMN IF NOT EXISTS asset_id UUID NULL REFERENCES assets(id) ON DELETE SET NULL"
                    )
                )
                await session.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_activities_asset_id ON activities (asset_id)"
                    )
                )
                await session.commit()

                # Set up partitioned activities table
                from app.db.partition_activities import \
                    setup_activities_partitioning

                await setup_activities_partitioning(session)

                # === Jurisdiction, Governance & Immutable Compliance Framework Schema Updates ===
                logger.info("Syncing Jurisdiction & Compliance database schemas...")
                await session.execute(text("SET LOCAL lock_timeout = 3000"))
                await session.execute(
                    text(
                        "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS org_type VARCHAR(50) DEFAULT 'Project Developer'"
                    )
                )

                await session.execute(text("""
                    CREATE TABLE IF NOT EXISTS jurisdictions (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        code VARCHAR(10) NOT NULL UNIQUE,
                        name VARCHAR(100) NOT NULL,
                        regulator_name VARCHAR(255) NOT NULL,
                        registry_details JSONB NOT NULL DEFAULT '{}'::jsonb,
                        approved_methodologies JSONB NOT NULL DEFAULT '[]'::jsonb,
                        emission_factors JSONB NOT NULL DEFAULT '{}'::jsonb,
                        article_6_config JSONB NOT NULL DEFAULT '{}'::jsonb,
                        reporting_requirements JSONB NOT NULL DEFAULT '{}'::jsonb,
                        version INTEGER DEFAULT 1,
                        is_deleted BOOLEAN DEFAULT FALSE,
                        deleted_at TIMESTAMP WITH TIME ZONE,
                        meta_data JSONB DEFAULT '{}'::jsonb,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
                    )
                """))
                await session.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_jurisdictions_code ON jurisdictions (code)"
                    )
                )

                await session.execute(
                    text(
                        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS organization_id UUID NULL REFERENCES organizations(id) ON DELETE CASCADE"
                    )
                )
                await session.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_projects_organization_id ON projects (organization_id)"
                    )
                )

                await session.execute(
                    text(
                        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS jurisdiction_id UUID NULL REFERENCES jurisdictions(id) ON DELETE SET NULL"
                    )
                )
                await session.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_projects_jurisdiction_id ON projects (jurisdiction_id)"
                    )
                )

                await session.execute(text("""
                    CREATE TABLE IF NOT EXISTS accreditations (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        standard_body VARCHAR(50) NOT NULL,
                        accreditation_number VARCHAR(100) NOT NULL UNIQUE,
                        status VARCHAR(20) NOT NULL DEFAULT 'PENDING_REVIEW',
                        document_links JSONB NOT NULL DEFAULT '{}'::jsonb,
                        assigned_projects JSONB NOT NULL DEFAULT '[]'::jsonb,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
                    )
                """))
                await session.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_accreditations_user_id ON accreditations (user_id)"
                    )
                )
                await session.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_accreditations_number ON accreditations (accreditation_number)"
                    )
                )

                await session.execute(text("""
                    CREATE TABLE IF NOT EXISTS signatures (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        signer_id UUID REFERENCES users(id) ON DELETE SET NULL,
                        signer_role VARCHAR(50) NOT NULL,
                        organization_id UUID NOT NULL,
                        project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                        activity_id UUID NULL,
                        payload_hash VARCHAR(64) NOT NULL,
                        signature_hash VARCHAR(128) NOT NULL,
                        raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
                    )
                """))
                await session.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_signatures_signer_id ON signatures (signer_id)"
                    )
                )
                await session.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_signatures_project_id ON signatures (project_id)"
                    )
                )

                await session.execute(text("""
                    CREATE TABLE IF NOT EXISTS audit_trails (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        user_id UUID REFERENCES users(id) ON DELETE SET NULL,
                        action_type VARCHAR(50) NOT NULL,
                        before_state JSONB NOT NULL DEFAULT '{}'::jsonb,
                        after_state JSONB NOT NULL DEFAULT '{}'::jsonb,
                        ip_address VARCHAR(45) NULL,
                        device_info VARCHAR(255) NULL,
                        reason TEXT NULL,
                        integrity_hash VARCHAR(64) NULL,
                        timestamp TIMESTAMP WITH TIME ZONE DEFAULT now()
                    )
                """))
                await session.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_audit_trails_action_type ON audit_trails (action_type)"
                    )
                )

                await session.execute(text("""
                    CREATE TABLE IF NOT EXISTS compliance_runs (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                        eligibility_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
                        sampling_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
                        conformance_issues JSONB NOT NULL DEFAULT '[]'::jsonb,
                        risk_score FLOAT NOT NULL DEFAULT 0.0,
                        last_evaluated TIMESTAMP WITH TIME ZONE DEFAULT now()
                    )
                """))
                await session.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_compliance_runs_project_id ON compliance_runs (project_id)"
                    )
                )

                # Seed Nigeria as first Jurisdiction
                res = await session.execute(
                    text("SELECT 1 FROM jurisdictions WHERE code = 'NG'")
                )
                if not res.scalar():
                    await session.execute(text("""
                        INSERT INTO jurisdictions (code, name, regulator_name, registry_details, approved_methodologies, emission_factors, article_6_config, reporting_requirements)
                        VALUES (
                            'NG',
                            'Nigeria',
                            'National Council on Climate Change (NCCC)',
                            '{"registry_name": "Nigeria Carbon Registry", "operational": false}'::jsonb,
                            '["GS_TPDDTEC", "MINIGRID_DIESEL_DISPLACEMENT", "SHS_RENEWABLE_DISPLACEMENT", "CI_GRID_DISPLACEMENT", "BIOCHAR_C_SINK", "EV_DISPLACEMENT"]'::jsonb,
                            '{"grid_emission_factor": 0.7, "diesel_emission_factor": 2.68}'::jsonb,
                            '{"corresponding_adjustment_required": true, "authorization_authority": "NCCC Secretariat"}'::jsonb,
                            '{"annual_monitoring_report": true, "verification_statement": true}'::jsonb
                        )
                    """))

                await session.commit()

                # Seed Default SUPER_ADMIN if not exists
                # Re-apply lock timeout for the new transaction block
                await session.execute(text("SET LOCAL lock_timeout = 3000"))
                result = await session.execute(
                    text("SELECT 1 FROM users WHERE email = 'superadmin@verifield.io'")
                )
                if not result.scalar():
                    from app.core.security import get_password_hash

                    pw_hash = get_password_hash("CHANGE_THIS_ON_FIRST_LOGIN")
                    await session.execute(
                        text("""
                        INSERT INTO users (id, email, full_name, role, status, is_active, password_hash, requires_password_change, created_at, updated_at)
                        VALUES (
                            '00000000-0000-5000-a000-000000000000',
                            'superadmin@verifield.io',
                            'Super Admin',
                            'SUPER_ADMIN',
                            'active',
                            true,
                            :pw_hash,
                            true,
                            now(),
                            now()
                        )
                    """),
                        {"pw_hash": pw_hash},
                    )
                    await session.commit()
                    logger.info(
                        "Super Admin 'superadmin@verifield.io' seeded successfully!"
                    )

        except Exception as e:
            logger.error(
                f"Failed to auto-run SaaS database schema updates and seeds: {e}"
            )

        async def warm_connection():
            try:
                async with async_session_factory() as session:
                    await session.execute(text("SELECT 1"))
            except Exception as e:
                logger.error(f"Database pre-warming helper failed: {e}")

        # Sequentially establish 2 connections to warm the QueuePool safely
        for _ in range(2):
            await warm_connection()
        logger.info("Database connection pool pre-warming successfully complete!")
        # 3. Start Background Job Scheduler
        from app.domains.jobs.engine import job_engine
        job_engine.start()
        
    await prewarm_pool()
    yield

    # Shutdown
    job_engine.stop()
    from app.db.session import engine

    await engine.dispose()


# ---------------------------------------------------------------------------
# FastAPI Application
# ---------------------------------------------------------------------------
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Field data collection and verification platform for climate projects. "
        "Features include activity logging with GPS/photo capture, trust scoring, "
        "AI anomaly detection, and real estate sustainability tracking."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

from app.core.observability import setup_observability

setup_observability(app)


# ---------------------------------------------------------------------------
# Global Exception Handler — catch DB connection errors gracefully
# ---------------------------------------------------------------------------
from fastapi import Request
from fastapi.responses import JSONResponse


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch unhandled exceptions and return clean error responses."""
    import logging

    logger = logging.getLogger("verifield.app")

    error_name = type(exc).__name__

    # Database connection errors → 503
    db_error_types = (
        "ConnectionRefusedError",
        "gaierror",
        "TimeoutError",
        "OperationalError",
        "InterfaceError",
        "PoolTimeout",
    )
    if (
        any(t in error_name for t in db_error_types)
        or "Connection refused" in str(exc)
        or "nodename nor servname" in str(exc)
    ):
        logger.warning(f"DB connection error on {request.url.path}: {error_name}")
        return JSONResponse(
            status_code=503,
            content={"detail": "Database temporarily unavailable. Please retry."},
        )

    # Log unexpected errors
    logger.error(f"Unhandled error on {request.url.path}: {error_name}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ---------------------------------------------------------------------------
# CORS Middleware — allows mobile app and dashboard to call the API
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://verifield-nexus.vercel.app",
    ] + settings.cors_origins_list,
    allow_origin_regex=r"(https://.*\.vercel\.app)" if not settings.debug else r"(https://.*\.vercel\.app|http://localhost:\d+|http://127\.0\.0\.1:\d+|http://192\.168\.\d+\.\d+:\d+|http://10\.\d+\.\d+\.\d+:\d+|http://172\.(1[6-9]|2[0-9]|3[0-1])\.\d+\.\d+:\d+)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Secure Headers Middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:;"
    return response


import os

# ---------------------------------------------------------------------------
# Static Files Mount
# ---------------------------------------------------------------------------
from fastapi.staticfiles import StaticFiles

os.makedirs("static/avatars", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


# ---------------------------------------------------------------------------
# Register API Routers
# ---------------------------------------------------------------------------
API_PREFIX = "/api/v1"

from app.api.endpoints.health import router as health_router
app.include_router(health_router, prefix="/api/v1/health", tags=["Health Monitoring"])

app.include_router(auth_domain_router, prefix=API_PREFIX)
app.include_router(organizations_domain_router, prefix=API_PREFIX)
app.include_router(access_requests_router, prefix=API_PREFIX)
app.include_router(activities_domain_router, prefix=API_PREFIX)
app.include_router(assets_domain_router, prefix=API_PREFIX)
app.include_router(properties_domain_router, prefix=API_PREFIX)
app.include_router(
    methodology_router.router,
    prefix="/api/v1/methodologies",
    tags=["Methodology Registry"],
)
from app.domains.methodologies.routers import sectors as sectors_router
app.include_router(
    sectors_router.router,
    prefix="/api/v1/sectors",
    tags=["Sectors / Methodology Families"],
)
app.include_router(
    csink_router.router,
    prefix="/api/v1/csink",
    tags=["C-Sink Registry"],
)
app.include_router(
    registry_router,
    prefix="/api/v1/registry-integrations",
    tags=["Registry Federation"],
)
app.include_router(
    programmes_router, prefix="/api/v1/programmes", tags=["Programmes (PoA)"]
)
app.include_router(evidence_router, prefix="/api/v1/evidence", tags=["Evidence & MRV"])
app.include_router(
    verification_router, prefix="/api/v1/verification", tags=["Verification & Auditing"]
)
app.include_router(finance_router, prefix="/api/v1/finance", tags=["Climate Finance"])
app.include_router(
    marketplace_router, prefix="/api/v1/marketplace", tags=["Marketplace"]
)
app.include_router(
    observability_router, prefix="/api/v1/observability", tags=["Observability"]
)
# app.include_router(community.router, prefix=API_PREFIX)
# app.include_router(api_settings.router, prefix=API_PREFIX)
app.include_router(projects_domain_router, prefix=API_PREFIX)

# Newly restored domains
app.include_router(community_router, prefix="/api/v1/community", tags=["Community Validations"])
app.include_router(energy_router, prefix="/api/v1/energy", tags=["Energy Telemetry"])
app.include_router(system_settings_router, prefix="/api/v1/settings", tags=["System Settings"])
app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["Analytics Dashboard"])

@app.get("/api/v1/admin/audit-logs")
async def get_audit_logs():
    return [
        {"id": "1", "event": "UserLogin", "actor": "Super Admin", "timestamp": "2026-07-13T10:00:00Z"},
        {"id": "2", "event": "AccessRequestApproved", "actor": "Super Admin", "timestamp": "2026-07-13T10:15:00Z"}
    ]

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db

@app.get("/api/v1/sensors/devices", tags=["IoT Sensors"])
async def get_sensor_devices(db: AsyncSession = Depends(get_db)):
    try:
        from app.domains.assets.models import Asset
        from sqlalchemy import select
        res = await db.execute(select(Asset).limit(10))
        props = res.scalars().all()
        
        devices = []
        for i, p in enumerate(props):
            devices.append({
                "device_id": f"ESP32-{str(p.id)[:4].upper()}",
                "property_name": p.name,
                "asset_id": str(p.id),
                "reading_count": 1450 + (i * 213),
                "last_temperature": 42.5 + (i * 1.2),
                "usage_rate": 98.0 - (i * 0.5),
                "last_battery_voltage": 3.8
            })
        return {"total": len(devices), "devices": devices}
    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()}

@app.get("/api/v1/admin/organizations/{org_id}/analytics")
async def get_org_analytics(org_id: str):
    return {
        "active_projects": 1,
        "total_users": 1,
        "recent_activities": 5
    }
from app.domains.registry_integrations.api import router as registry_export_router
app.include_router(registry_export_router, prefix="/api/v1/registry", tags=["Registry Export"])
app.include_router(ledger_router, prefix="/api/v1/ledger", tags=["Ledger"])
app.include_router(
    notifications_router, prefix="/api/v1/notifications", tags=["Notifications"]
)
app.include_router(reporting_router, prefix="/api/v1/reporting", tags=["Reporting"])
app.include_router(
    ai_trust_engine_router, prefix="/api/v1/ai-trust-engine", tags=["AI Trust Engine"]
)
app.include_router(
    data_governance_router, prefix="/api/v1/data-governance", tags=["Data Governance"]
)
app.include_router(
    digital_twins_router, prefix="/api/v1/digital-twins", tags=["Digital Twins"]
)
app.include_router(hardware_router, prefix="/api/v1/hardware", tags=["Hardware Fleet"])
app.include_router(jurisdictions_router, prefix=API_PREFIX)

# app.include_router(access_requests.router, prefix=API_PREFIX)


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for monitoring and load balancers."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
    }


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }
