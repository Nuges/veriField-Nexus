"""
=============================================================================
VeriField Nexus — Carbon & Registry API
=============================================================================
Endpoints for carbon project management, quantification, and credit ledger.
=============================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import defer
from typing import List, Dict, Any, Optional
import uuid

from app.db.session import get_db
from app.core.security import require_admin
from app.models.project import Project
from app.models.carbon_calculation import CarbonCalculation
from app.models.activity import Activity
from app.models.user import User
from app.services.quantification_engine import QuantificationEngine
from pydantic import BaseModel

router = APIRouter(prefix="/carbon", tags=["Carbon & Registry"])


class ProjectCreate(BaseModel):
    name: str
    methodology_id: str
    baseline_parameters: Dict[str, Any]


class QuantifyRequest(BaseModel):
    """Optional body to specify which project to use."""
    project_id: Optional[uuid.UUID] = None


@router.post("/projects", summary="Create a new Carbon Project")
async def create_project(
    payload: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_admin)
):
    """Register a new project under a specific methodology."""
    proj = Project(
        name=payload.name,
        methodology_id=payload.methodology_id,
        baseline_parameters=payload.baseline_parameters
    )
    db.add(proj)
    await db.commit()
    await db.refresh(proj)
    return {"id": proj.id, "name": proj.name, "methodology": proj.methodology_id}


@router.post("/calculate/{activity_id}", summary="Quantify Carbon Credits")
async def quantify_carbon(
    activity_id: uuid.UUID,
    body: Optional[QuantifyRequest] = None,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_admin)
):
    """
    Triggers the deterministic calculation engine for a verified activity.
    Optionally specify a project_id; otherwise auto-detects methodology.
    """
    engine = QuantificationEngine(db)
    project_id = body.project_id if body else None
    try:
        calc = await engine.quantify_activity(activity_id, project_id)
        return {
            "calculation_id": calc.id,
            "tco2e": calc.tco2e_generated,
            "methodology": calc.methodology_used,
            "status": calc.status,
            "log": calc.calculation_log,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/projects/{project_id}/total", summary="Get Project Total tCO2e")
async def get_project_total(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_admin)
):
    """Get aggregated tCO2e total for a carbon project."""
    engine = QuantificationEngine(db)
    return await engine.get_project_total(project_id)


@router.get("/ledger", summary="Get Carbon Credit Ledger")
async def get_ledger(
    status_filter: Optional[str] = Query(None, alias="status"),
    include_log: bool = Query(False, alias="include_log"),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_admin),
):
    """Fetch the immutable ledger of calculated credits."""
    query = select(CarbonCalculation)
    
    if not include_log:
        query = query.options(defer(CarbonCalculation.calculation_log))
        
    query = (
        query.join(Activity, CarbonCalculation.activity_id == Activity.id)
        .join(User, Activity.user_id == User.id)
    )
    if user.organization:
        query = query.where(User.organization == user.organization)
    query = query.order_by(CarbonCalculation.created_at.desc())
    if status_filter:
        query = query.where(CarbonCalculation.status == status_filter)
    query = query.limit(100)

    result = await db.execute(query)
    calcs = result.scalars().all()
    return {
        "data": [
            {
                "id": c.id,
                "project_id": c.project_id,
                "activity_id": c.activity_id,
                "tco2e": c.tco2e_generated,
                "methodology": c.methodology_used,
                "status": c.status,
                "calculation_log": c.calculation_log if include_log else None,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in calcs
        ],
        "total_records": len(calcs),
    }


@router.post("/registry/verra/issue", summary="Mock Verra Registry API Push")
async def push_to_verra_registry(db: AsyncSession = Depends(get_db), user=Depends(require_admin)):
    """Mock integration: Packs the calculation logs into a JSON ready for Verra API."""
    stmt = select(CarbonCalculation)\
        .join(Activity, CarbonCalculation.activity_id == Activity.id)\
        .join(User, Activity.user_id == User.id)

    if user.organization:
        stmt = stmt.where(User.organization == user.organization)

    stmt = stmt.where(CarbonCalculation.status == "calculated")
    result = await db.execute(stmt)
    calcs = result.scalars().all()

    if not calcs:
        return {"detail": "No pending credits to issue."}

    total_tco2e = sum(c.tco2e_generated for c in calcs)

    # Update status
    for c in calcs:
        c.status = "pending_issuance"
    await db.commit()

    return {
        "registry": "Verra",
        "action": "Issue Request Sent",
        "total_tco2e": round(total_tco2e, 4),
        "payload_size": len(calcs),
        "audit_pack_generated": True
    }


@router.post("/registry/goldstandard/issue", summary="Mock Gold Standard Registry API Push")
async def push_to_goldstandard_registry(db: AsyncSession = Depends(get_db), user=Depends(require_admin)):
    """Mock integration: Packs the calculation logs into a JSON ready for Gold Standard API."""
    stmt = select(CarbonCalculation)\
        .join(Activity, CarbonCalculation.activity_id == Activity.id)\
        .join(User, Activity.user_id == User.id)

    if user.organization:
        stmt = stmt.where(User.organization == user.organization)

    stmt = stmt.where(CarbonCalculation.status == "calculated")
    result = await db.execute(stmt)
    calcs = result.scalars().all()

    if not calcs:
        return {"detail": "No pending credits to issue."}

    total_tco2e = sum(c.tco2e_generated for c in calcs)

    # Update status
    for c in calcs:
        c.status = "pending_issuance"
    await db.commit()

    return {
        "registry": "Gold Standard",
        "action": "Issue Request Sent",
        "total_tco2e": round(total_tco2e, 4),
        "payload_size": len(calcs),
        "audit_pack_generated": True
    }
