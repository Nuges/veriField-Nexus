import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/health")
async def health_check():
    """Basic health check that the API is running."""
    return {"status": "ok", "service": "verifield-nexus-api"}

@router.get("/live")
async def liveness_probe():
    """Liveness probe for Kubernetes/Docker."""
    return {"status": "alive"}

@router.get("/ready")
async def readiness_probe(db: AsyncSession = Depends(get_db)):
    """Readiness probe that checks critical dependencies."""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as e:
        logger.error(f"Readiness probe failed: {e}")
        raise HTTPException(status_code=503, detail="Service Unavailable: Dependencies not ready.")

@router.get("/database")
async def database_health(db: AsyncSession = Depends(get_db)):
    """Specific database health check."""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "message": "Database connection successful"}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        raise HTTPException(status_code=503, detail="Database connection failed.")

@router.get("/storage")
async def storage_health():
    """Storage health check (mocked for now)."""
    return {"status": "ok", "message": "Storage accessible"}

@router.get("/queue")
async def queue_health():
    """Message queue health check (mocked for now)."""
    return {"status": "ok", "message": "Queue accessible"}
