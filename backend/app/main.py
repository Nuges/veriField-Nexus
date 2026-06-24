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
from app.api.v1 import auth, activities, properties, analytics, export, cross_verification, carbon, audits, sensors, community, access_requests
from app.api.v1 import registry, settings as api_settings
from app.api.v1 import energy as energy_api
from app.api.v1 import projects as projects_api
from app.api.v1 import csink


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
    from app.services.job_scheduler import start_scheduler, shutdown_scheduler
    import logging
    import asyncio
    from app.db.session import async_session_factory
    from sqlalchemy import text
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("verifield.startup")
    
    # 1. Start Background Job Scheduler
    start_scheduler()

    # 2. Asynchronously Pre-warm the Connection Pool in the background
    async def prewarm_pool():
        logger.info("Initializing database connection pool pre-warming and schema migrations...")
        
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
                        role
                    )
                else:
                    logger.info("Supabase Admin Key (service_role) validated successfully.")
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
                await session.execute(text("ALTER TABLE community_validations ADD COLUMN IF NOT EXISTS upvotes INTEGER DEFAULT 0"))
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
                await session.execute(text("ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS gps_max_distance_km FLOAT DEFAULT 5.0"))
                await session.execute(text("ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS max_submissions_per_hour INTEGER DEFAULT 10"))
                await session.execute(text("ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS image_hash_threshold INTEGER DEFAULT 12"))
                await session.execute(text("ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS suspicious_hours_start INTEGER DEFAULT 2"))
                await session.execute(text("ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS suspicious_hours_end INTEGER DEFAULT 5"))
                await session.commit()
                logger.info("Community upvotes and comments database schema updates synced successfully!")

                # === Project Configuration Layer (3-Layer MRV Architecture) ===
                # Re-apply lock timeout for the new transaction block
                await session.execute(text("SET LOCAL lock_timeout = 3000"))
                await session.execute(text("ALTER TABLE projects ADD COLUMN IF NOT EXISTS project_code VARCHAR(20) UNIQUE"))
                await session.execute(text("ALTER TABLE projects ADD COLUMN IF NOT EXISTS sector VARCHAR(30) DEFAULT 'energy'"))
                await session.execute(text("ALTER TABLE projects ADD COLUMN IF NOT EXISTS country VARCHAR(100) DEFAULT 'Nigeria'"))
                await session.execute(text("ALTER TABLE projects ADD COLUMN IF NOT EXISTS baseline_source VARCHAR(30) DEFAULT 'diesel_generator'"))
                await session.execute(text("ALTER TABLE projects ADD COLUMN IF NOT EXISTS diesel_emission_factor FLOAT DEFAULT 2.68"))
                await session.execute(text("ALTER TABLE projects ADD COLUMN IF NOT EXISTS grid_emission_factor FLOAT DEFAULT 0.7"))
                await session.execute(text("ALTER TABLE projects ADD COLUMN IF NOT EXISTS crediting_start DATE"))
                await session.execute(text("ALTER TABLE projects ADD COLUMN IF NOT EXISTS crediting_end DATE"))
                await session.execute(text("ALTER TABLE projects ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now()"))
                # Add index on project_code for fast lookups
                await session.execute(text("CREATE INDEX IF NOT EXISTS ix_projects_project_code ON projects (project_code)"))
                await session.execute(text("CREATE INDEX IF NOT EXISTS ix_projects_sector ON projects (sector)"))
                await session.commit()
                logger.info("Project configuration schema (3-Layer MRV) synced successfully!")

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
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
                    )
                """))
                await session.execute(text("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS plan VARCHAR(30) DEFAULT 'FREE'"))
                await session.execute(text("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS max_installations INTEGER DEFAULT 100"))
                await session.execute(text("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS max_agents INTEGER DEFAULT 5"))
                await session.execute(text("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS api_calls_count INTEGER DEFAULT 0"))
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
                await session.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS organization_id UUID NULL REFERENCES organizations(id) ON DELETE SET NULL"))
                await session.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true"))
                await session.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255) NULL"))
                await session.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS requires_password_change BOOLEAN DEFAULT false"))
                await session.commit()

                # Seed Default SUPER_ADMIN if not exists
                # Re-apply lock timeout for the new transaction block
                await session.execute(text("SET LOCAL lock_timeout = 3000"))
                result = await session.execute(text("SELECT 1 FROM users WHERE email = 'superadmin@verifield.io'"))
                if not result.scalar():
                    from app.core.security import get_password_hash
                    pw_hash = get_password_hash("CHANGE_THIS_ON_FIRST_LOGIN")
                    await session.execute(text("""
                        INSERT INTO users (id, email, full_name, role, status, is_active, password_hash, requires_password_change, sector, created_at, updated_at)
                        VALUES (
                            '00000000-0000-5000-a000-000000000000',
                            'superadmin@verifield.io',
                            'Super Admin',
                            'SUPER_ADMIN',
                            'active',
                            true,
                            :pw_hash,
                            true,
                            'cookstove',
                            now(),
                            now()
                        )
                    """), {"pw_hash": pw_hash})
                    await session.commit()
                    logger.info("Super Admin 'superadmin@verifield.io' seeded successfully!")

                # === CSI Carbon Sink MRV Module Schema Updates ===
                logger.info("Syncing CSI Carbon Sink module database schema...")
                await session.execute(text("SET LOCAL lock_timeout = 3000"))
                await session.execute(text("""
                    CREATE TABLE IF NOT EXISTS artisan_profiles (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        name VARCHAR(255) NOT NULL,
                        phone VARCHAR(20) NULL,
                        kiln_type VARCHAR(100) NOT NULL,
                        proficiency_passed BOOLEAN DEFAULT false,
                        volume_measuring_device_m3 FLOAT DEFAULT 0.0,
                        client_id VARCHAR(36) NULL UNIQUE,
                        gps JSONB NULL,
                        timestamp TIMESTAMP WITH TIME ZONE DEFAULT now(),
                        evidence_links JSONB NULL
                    )
                """))
                await session.execute(text("""
                    CREATE TABLE IF NOT EXISTS kiln_profiles (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        artisan_id UUID NOT NULL REFERENCES artisan_profiles(id) ON DELETE CASCADE,
                        serial_number VARCHAR(100) NOT NULL UNIQUE,
                        surface_area_m2 FLOAT NOT NULL,
                        depth_m FLOAT NOT NULL,
                        capacity_m3 FLOAT NOT NULL,
                        methane_emission_factor FLOAT DEFAULT 0.0,
                        client_id VARCHAR(36) NULL,
                        gps JSONB NULL,
                        timestamp TIMESTAMP WITH TIME ZONE DEFAULT now(),
                        evidence_links JSONB NULL
                    )
                """))
                await session.execute(text("""
                    CREATE TABLE IF NOT EXISTS biomass_profiles (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        name VARCHAR(255) NOT NULL,
                        mixing_ratio VARCHAR(100) NOT NULL,
                        carbon_content_pct FLOAT NOT NULL,
                        bulk_density_g_cm3 FLOAT NOT NULL,
                        methane_compensation_scheme VARCHAR(100) NOT NULL,
                        client_id VARCHAR(36) NULL,
                        gps JSONB NULL,
                        timestamp TIMESTAMP WITH TIME ZONE DEFAULT now(),
                        evidence_links JSONB NULL
                    )
                """))
                await session.execute(text("""
                    CREATE TABLE IF NOT EXISTS biochar_batches (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        kiln_id UUID NOT NULL REFERENCES kiln_profiles(id) ON DELETE CASCADE,
                        biomass_id UUID NOT NULL REFERENCES biomass_profiles(id) ON DELETE CASCADE,
                        batch_number VARCHAR(100) NOT NULL UNIQUE,
                        quantity_kg FLOAT NOT NULL,
                        produced_at TIMESTAMP WITH TIME ZONE NOT NULL,
                        lab_report_url VARCHAR(500) NULL,
                        client_id VARCHAR(36) NULL,
                        gps JSONB NULL,
                        timestamp TIMESTAMP WITH TIME ZONE DEFAULT now(),
                        evidence_links JSONB NULL
                    )
                """))
                await session.execute(text("""
                    CREATE TABLE IF NOT EXISTS qr_records (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        qr_id VARCHAR(100) NOT NULL UNIQUE,
                        batch_id UUID NOT NULL REFERENCES biochar_batches(id) ON DELETE CASCADE,
                        verification_status VARCHAR(20) DEFAULT 'verified',
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
                    )
                """))
                await session.execute(text("""
                    CREATE TABLE IF NOT EXISTS c_sink_units (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        name VARCHAR(255) NOT NULL,
                        total_co2e_t FLOAT NOT NULL,
                        carbon_content_pct FLOAT NOT NULL,
                        biomass_type VARCHAR(255) NOT NULL,
                        pyrolysis_technology VARCHAR(255) NOT NULL,
                        matrix_category VARCHAR(255) NOT NULL,
                        project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                        client_id VARCHAR(36) NULL,
                        gps JSONB NULL,
                        timestamp TIMESTAMP WITH TIME ZONE DEFAULT now(),
                        evidence_links JSONB NULL
                    )
                """))
                await session.execute(text("""
                    CREATE TABLE IF NOT EXISTS c_sink_transactions (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        c_sink_unit_id UUID NOT NULL REFERENCES c_sink_units(id) ON DELETE CASCADE,
                        transaction_type VARCHAR(20) NOT NULL,
                        registry_tx_id VARCHAR(255) NULL,
                        payload JSONB NOT NULL,
                        status VARCHAR(20) DEFAULT 'PENDING',
                        response_log TEXT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
                    )
                """))
                await session.execute(text("""
                    CREATE TABLE IF NOT EXISTS csi_parameters (
                        id VARCHAR(50) PRIMARY KEY,
                        value FLOAT NOT NULL,
                        description VARCHAR(255) NOT NULL,
                        source_reference VARCHAR(255) NULL,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
                    )
                """))
                await session.execute(text("ALTER TABLE activities ADD COLUMN IF NOT EXISTS biochar_batch_id UUID REFERENCES biochar_batches(id) ON DELETE SET NULL"))
                await session.execute(text("ALTER TABLE activities ADD COLUMN IF NOT EXISTS c_sink_unit_id UUID REFERENCES c_sink_units(id) ON DELETE SET NULL"))
                await session.commit()
                logger.info("CSI database tables verified/created successfully!")

                # Seed default parameters
                await session.execute(text("SET LOCAL lock_timeout = 3000"))
                await session.execute(text("""
                    INSERT INTO csi_parameters (id, value, description, source_reference)
                    VALUES 
                        ('diesel_emission_factor', 2.68, 'Diesel fuel lifecycle emission factor (kg CO2e/L)', 'CSI Global C-Sink standard'),
                        ('ch4_avoidance_traditional', 1.5, 'Methane emission avoidance for clean pyrolysis vs open burn (kg CH4/t)', 'CSI Guideline 2026'),
                        ('moisture_correction_factor', 0.85, 'Default biochar dry matter correction multiplier (1 - moisture %)', 'EBC guidelines v10.0'),
                        ('margin_of_security', 0.90, 'Standard CSI security margin correction factor (10% deduction)', 'CSI Artisan C-Sink standard')
                    ON CONFLICT (id) DO NOTHING
                """))
                
                # Seed default Artisan, Kiln and Biomass for immediate out-of-the-box local testing
                result = await session.execute(text("SELECT 1 FROM artisan_profiles LIMIT 1"))
                if not result.scalar():
                    artisan_id = '11111111-1111-1111-1111-111111111111'
                    kiln_id = '22222222-2222-2222-2222-222222222222'
                    biomass_id = '33333333-3333-3333-3333-333333333333'
                    batch_id = '44444444-4444-4444-4444-444444444444'
                    project_id = '00000000-0000-0000-0000-000000000001'
                    
                    await session.execute(text("""
                        INSERT INTO projects (id, project_code, name, sector, country, methodology_id, baseline_source, baseline_parameters)
                        VALUES (:id, 'VF-CS-001', 'CSI Biochar C-Sink Project', 'cookstove', 'Nigeria', 'CSI Global Artisan C-Sink Standard v2.1', 'diesel_generator', '{}'::jsonb)
                        ON CONFLICT (id) DO NOTHING
                    """), {"id": project_id})
                    
                    await session.execute(text("""
                        INSERT INTO artisan_profiles (id, name, phone, kiln_type, proficiency_passed, volume_measuring_device_m3)
                        VALUES (:id, 'Segun Biocharist', '+2348011223344', 'Kon-Tiki Flame Cap', true, 1.2)
                    """), {"id": artisan_id})
                    
                    await session.execute(text("""
                        INSERT INTO kiln_profiles (id, artisan_id, serial_number, surface_area_m2, depth_m, capacity_m3, methane_emission_factor)
                        VALUES (:id, :artisan_id, 'KILN-KT-001', 2.2, 0.95, 1.5, 0.05)
                    """), {"id": kiln_id, "artisan_id": artisan_id})
                    
                    await session.execute(text("""
                        INSERT INTO biomass_profiles (id, name, mixing_ratio, carbon_content_pct, bulk_density_g_cm3, methane_compensation_scheme)
                        VALUES (:id, 'Rice Husk Feedstock', '100% Rice Husk', 71.30, 0.12, 'avoidance')
                    """), {"id": biomass_id})
                    
                    await session.execute(text("""
                        INSERT INTO biochar_batches (id, kiln_id, biomass_id, batch_number, quantity_kg, produced_at)
                        VALUES (:id, :kiln_id, :biomass_id, 'BATCH-RH-2026-001', 350.0, now())
                    """), {"id": batch_id, "kiln_id": kiln_id, "biomass_id": biomass_id})
                    
                    await session.execute(text("""
                        INSERT INTO qr_records (qr_id, batch_id, verification_status)
                        VALUES ('CSI-EBC-BIO-9921', :batch_id, 'verified')
                    """), {"batch_id": batch_id})
                    
                    logger.info("Successfully seeded default Artisan, Kiln, Biomass, Batch, and QR registry record!")
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to auto-run SaaS or CSI database schema updates and seeds: {e}")

        async def warm_connection():
            try:
                async with async_session_factory() as session:
                    await session.execute(text("SELECT 1"))
            except Exception as e:
                logger.error(f"Database pre-warming helper failed: {e}")
        
        # Concurrently establish 5 connections to warm the QueuePool
        await asyncio.gather(*(warm_connection() for _ in range(5)))
        logger.info("Database connection pool pre-warming successfully complete!")

    asyncio.create_task(prewarm_pool())

    yield

    # Shutdown
    await shutdown_scheduler()
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
        "ConnectionRefusedError", "gaierror", "TimeoutError",
        "OperationalError", "InterfaceError", "PoolTimeout",
    )
    if any(t in error_name for t in db_error_types) or "Connection refused" in str(exc) or "nodename nor servname" in str(exc):
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
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://192.168.8.200:3000",
        "http://192.168.0.111:3000",
        "https://verifield-nexus.vercel.app"
    ],
    allow_origin_regex=r"(https://.*\.vercel\.app|http://localhost:\d+|http://127\.0\.0\.1:\d+|http://192\.168\.\d+\.\d+:\d+|http://10\.\d+\.\d+\.\d+:\d+|http://172\.(1[6-9]|2[0-9]|3[0-1])\.\d+\.\d+:\d+)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Static Files Mount
# ---------------------------------------------------------------------------
from fastapi.staticfiles import StaticFiles
import os
os.makedirs("static/avatars", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


# ---------------------------------------------------------------------------
# Register API Routers
# ---------------------------------------------------------------------------
API_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(activities.router, prefix=API_PREFIX)
app.include_router(properties.router, prefix=API_PREFIX)
app.include_router(analytics.router, prefix=API_PREFIX)
app.include_router(export.router, prefix=API_PREFIX)
app.include_router(cross_verification.router, prefix=API_PREFIX)
app.include_router(carbon.router, prefix=API_PREFIX)
app.include_router(audits.router, prefix=API_PREFIX)
app.include_router(sensors.router, prefix=API_PREFIX)
app.include_router(community.router, prefix=API_PREFIX)
app.include_router(registry.router, prefix=API_PREFIX)
app.include_router(api_settings.router, prefix=API_PREFIX)
app.include_router(energy_api.router, prefix=API_PREFIX)
app.include_router(projects_api.router, prefix=API_PREFIX)
app.include_router(access_requests.router, prefix=API_PREFIX)
app.include_router(csink.router, prefix=API_PREFIX)


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
