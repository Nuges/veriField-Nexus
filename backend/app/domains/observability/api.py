from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db

from .schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    db_status = "unhealthy"
    try:
        await db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception:
        pass

    return HealthResponse(
        status="ok" if db_status == "healthy" else "degraded",
        version=settings.app_name,
        components={"database": db_status, "api": "healthy"},
    )


# A simple metrics endpoint stub. In a real system, prometheus_client would be used here.
@router.get("/metrics")
async def get_metrics():
    return Response(
        content="nexus_requests_total 1024\nnexus_active_users 42\n",
        media_type="text/plain",
    )
