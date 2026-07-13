from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.domains.ai_trust_engine.repository import TrustEngineRepository
from app.domains.ai_trust_engine.schemas import TrustLogResponse
from app.domains.authentication.models import User

router = APIRouter(tags=["AI Trust Engine"])


@router.get("/logs", response_model=List[TrustLogResponse])
async def list_trust_logs(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = TrustEngineRepository(db)
    return await repo.list_recent(skip=skip, limit=limit)


@router.get("/logs/activity/{activity_id}", response_model=TrustLogResponse)
async def get_trust_log_by_activity(
    activity_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = TrustEngineRepository(db)
    log = await repo.get_by_activity(activity_id)
    if not log:
        raise HTTPException(
            status_code=404, detail="Trust log not found for this activity"
        )
    return log


from fastapi import Query

from app.core.rbac import require_permission
from app.domains.ai_trust_engine.forecasting import ExecutiveForecastingService


@router.get("/forecast/project/{project_id}", tags=["AI Trust Engine"])
async def get_project_forecast(
    project_id: str,
    months_ahead: int = Query(12, ge=1, le=60),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_permission("project:read")),
):
    """
    Generate an AI-driven executive forecast for a project's future carbon yield.
    """
    svc = ExecutiveForecastingService(db)
    result = await svc.generate_carbon_forecast(project_id, months_ahead)
    return result


from app.domains.ai_trust_engine.service import TelemetryAnomalyDetector


@router.post("/telemetry-anomaly/{property_id}", tags=["AI Trust Engine"])
async def check_telemetry_anomaly(
    property_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_permission("project:read")),
):
    """
    Evaluates recent telemetry data for statistical anomalies indicating sensor spoofing or failure.
    """
    detector = TelemetryAnomalyDetector()
    result = await detector.evaluate(db, property_id)
    return result
