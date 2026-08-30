from fastapi import APIRouter, Depends, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    generate_latest,
    REGISTRY,
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db

from .schemas import HealthResponse

router = APIRouter()

# Live Prometheus metrics registry
NEXUS_REQUESTS_TOTAL = Counter("nexus_requests_total", "Total requests handled by VeriField Nexus")
SYSTEM_UPTIME = Gauge("verifield_system_uptime_seconds", "VeriField Nexus uptime in seconds")
DB_HEALTH = Gauge("verifield_database_healthy", "Database health status (1=healthy, 0=unhealthy)")
NEXUS_INFO = Gauge(
    "verifield_nexus_build_info",
    "VeriField Nexus application metadata",
    ["version", "app_name"],
)
NEXUS_INFO.labels(version=settings.app_version, app_name=settings.app_name).set(1)


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    db_status = "unhealthy"
    try:
        await db.execute(text("SELECT 1"))
        db_status = "healthy"
        DB_HEALTH.set(1)
    except Exception:
        DB_HEALTH.set(0)

    return HealthResponse(
        status="ok" if db_status == "healthy" else "degraded",
        version=settings.app_name,
        components={"database": db_status, "api": "healthy"},
    )


@router.get("/metrics")
async def get_metrics(db: AsyncSession = Depends(get_db)):
    """
    Exposes live Prometheus metrics for infrastructure scrapers (Prometheus / Grafana).
    """
    try:
        await db.execute(text("SELECT 1"))
        DB_HEALTH.set(1)
    except Exception:
        DB_HEALTH.set(0)

    metrics_output = generate_latest(REGISTRY)
    return Response(
        content=metrics_output,
        media_type=CONTENT_TYPE_LATEST,
    )

