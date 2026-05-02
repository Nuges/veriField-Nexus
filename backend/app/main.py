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
from app.api.v1 import auth, activities, properties, analytics, export, cross_verification


# ---------------------------------------------------------------------------
# Lifespan — runs on startup and shutdown
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Database tables should be managed by Alembic in production
    to avoid blocking operations and cold start delays.
    """
    yield
    # Shutdown
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
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
