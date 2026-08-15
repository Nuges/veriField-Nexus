import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import require_permission
from app.db.session import get_db
from app.domains.authentication.models import User
from app.domains.digital_twins.models.twin import DigitalTwin
from app.domains.digital_twins.services.intelligence import \
    TwinIntelligenceEngine

router = APIRouter()


async def _enforce_twin_tenant_access(
    twin_id: str, user: User, db: AsyncSession
) -> None:
    """Verify the caller has organization-level access to the specified Digital Twin."""
    if user.role == "SUPER_ADMIN":
        return
    try:
        twin_uid = UUID(str(twin_id))
    except (ValueError, TypeError):
        raise HTTPException(status_code=404, detail="Digital Twin not found")

    result = await db.execute(select(DigitalTwin).where(DigitalTwin.id == twin_uid))
    twin = result.scalar_one_or_none()
    if not twin:
        raise HTTPException(status_code=404, detail="Digital Twin not found")
    if twin.asset_id:
        from app.domains.assets.models import Asset
        asset = await db.get(Asset, twin.asset_id)
        if asset and asset.organization_id != user.organization_id:
            raise HTTPException(status_code=404, detail="Digital Twin not found")


@router.post("/{twin_id}/simulate", tags=["Digital Twin Intelligence"])
async def simulate_twin(
    twin_id: str,
    forward_steps: int = Query(10, ge=1, le=100),
    step_size_minutes: int = Query(60, ge=1, le=1440),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("project:read")),
):
    """
    Runs a forward projection simulation for a specific Digital Twin.
    """
    await _enforce_twin_tenant_access(twin_id, user, db)
    engine = TwinIntelligenceEngine(db)
    try:
        results = await engine.run_simulation(twin_id, forward_steps, step_size_minutes)
        return {"simulation": results}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{twin_id}/playback", tags=["Digital Twin Intelligence"])
async def playback_history(
    twin_id: str,
    start_time: datetime,
    end_time: datetime,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("project:read")),
):
    """
    Replays the historical state of a Digital Twin over a specific time window.
    """
    await _enforce_twin_tenant_access(twin_id, user, db)
    engine = TwinIntelligenceEngine(db)
    states = await engine.playback_history(twin_id, start_time, end_time)
    return {"history": states}


@router.post("/{twin_id}/evaluate-failures", tags=["Digital Twin Intelligence"])
async def evaluate_failures(
    twin_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("project:read")),
):
    """
    Forces an immediate evaluation of failure prediction hooks.
    """
    await _enforce_twin_tenant_access(twin_id, user, db)
    engine = TwinIntelligenceEngine(db)
    result = await engine.evaluate_failure_prediction(twin_id)
    return result
