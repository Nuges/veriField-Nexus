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
        except Exception as e:
            logger.error(f"Failed to auto-run SaaS database schema updates and seeds: {e}")

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
    shutdown_scheduler()
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
