"""
=============================================================================
VeriField Nexus — Carbon & Registry API
=============================================================================
Endpoints for carbon project management, quantification, and credit ledger.
=============================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import defer
import uuid
import httpx
import asyncio
import logging
from typing import List, Dict, Any, Optional

from app.core.config import settings

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
    # New optional fields (forwarded to the expanded Project model)
    sector: str = "energy"
    country: str = "Nigeria"
    baseline_source: str = "diesel_generator"
    diesel_emission_factor: float = 2.68
    grid_emission_factor: float = 0.7


class QuantifyRequest(BaseModel):
    """Optional body to specify which project to use."""
    project_id: Optional[uuid.UUID] = None


@router.post("/projects", summary="Create a new Carbon Project (Deprecated — use POST /projects)")
async def create_project(
    payload: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_admin)
):
    """
    Register a new project under a specific methodology.
    
    NOTE: This endpoint is maintained for backward compatibility.
    Prefer using POST /api/v1/projects for full project configuration
    including crediting periods and project codes.
    """
    proj = Project(
        name=payload.name,
        methodology_id=payload.methodology_id,
        baseline_parameters=payload.baseline_parameters,
        sector=payload.sector,
        country=payload.country,
        baseline_source=payload.baseline_source,
        diesel_emission_factor=payload.diesel_emission_factor,
        grid_emission_factor=payload.grid_emission_factor,
    )
    db.add(proj)
    await db.commit()
    await db.refresh(proj)
    return {"id": proj.id, "name": proj.name, "methodology": proj.methodology_id}


@router.post("/calculate/{activity_id}", summary="Quantify Carbon Credits")
async def quantify_carbon(
    activity_id: uuid.UUID,
    body: Optional[QuantifyRequest] = Body(None),
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


@router.post("/registry/verra/issue", summary="Issue Credits to Verra Registry")
async def push_to_verra_registry(db: AsyncSession = Depends(get_db), user=Depends(require_admin)):
    """
    Submits pending carbon credit calculations to the Verra Registry API.
    Utilizes httpx with a 3-attempt exponential backoff retry loop.
    """
    logger = logging.getLogger("verifield.registry.verra")
    
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

    # Prepare real integration payload
    payload = {
        "issuance_request": {
            "source": "VeriField Nexus dMRV Platform",
            "timestamp": datetime.now(timezone.utc).isoformat() if hasattr(datetime, "now") else None,
            "organization": user.organization or "VeriField",
            "total_tco2e": round(total_tco2e, 4),
            "payload_size": len(calcs),
            "credits": [
                {
                    "calculation_id": str(c.id),
                    "activity_id": str(c.activity_id),
                    "tco2e": float(c.tco2e_generated),
                    "methodology": c.methodology_used,
                    "created_at": c.created_at.isoformat() if c.created_at else None
                }
                for c in calcs
            ]
        }
    }

    # Verify if registry API endpoint is configured
    url = settings.verra_api_url
    api_key = settings.verra_api_key

    if not url or not api_key:
        # Dry-run / Configuration Missing Mode: Return generated payload
        logger.warning("Verra API credentials not configured. Returning payload for dry-run/manual upload.")
        # Mark as pending_issuance locally so it's tracked as processed
        for c in calcs:
            c.status = "pending_issuance"
        await db.commit()

        return {
            "registry": "Verra",
            "action": "Dry-run (Configuration Missing)",
            "status": "warning",
            "warning": "Verra API endpoint or key is not set in backend settings. Outputting generated audit payload.",
            "total_tco2e": round(total_tco2e, 4),
            "payload_size": len(calcs),
            "payload": payload,
            "audit_pack_generated": True
        }

    # Execute HTTP call with retry logic
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-VeriField-Audit-Trace": str(uuid.uuid4())
    }

    success = False
    api_response = None
    
    # 3 attempts with exponential backoff: 2s, 4s, 8s
    for attempt in range(3):
        try:
            logger.info(f"Posting to Verra API (attempt {attempt + 1}/3) at {url}...")
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code in (200, 201, 202):
                    success = True
                    api_response = resp.json()
                    logger.info("Successfully posted carbon calculations to Verra API.")
                    break
                else:
                    logger.warning(
                        f"Verra API returned error status {resp.status_code}: {resp.text}. "
                        f"Attempt {attempt + 1}/3."
                    )
                    api_response = {"status_code": resp.status_code, "error": resp.text}
        except Exception as e:
            logger.warning(f"Connection error when calling Verra API: {e}. Attempt {attempt + 1}/3.")
            api_response = {"error": str(e)}

        if attempt < 2:
            await asyncio.sleep(2.0 * (2 ** attempt))

    if not success:
        logger.error("Failed to push carbon calculations to Verra API after 3 retries.")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": "Failed to connect to Verra Registry API terminal.",
                "last_response": api_response
            }
        )

    # Update state in DB upon successful API submission
    for c in calcs:
        c.status = "pending_issuance"
    await db.commit()

    return {
        "registry": "Verra",
        "action": "Issue Request Sent",
        "status": "success",
        "total_tco2e": round(total_tco2e, 4),
        "payload_size": len(calcs),
        "api_response": api_response,
        "audit_pack_generated": True
    }


@router.post("/registry/goldstandard/issue", summary="Issue Credits to Gold Standard Registry")
async def push_to_goldstandard_registry(db: AsyncSession = Depends(get_db), user=Depends(require_admin)):
    """
    Submits pending carbon credit calculations to the Gold Standard Registry API.
    Utilizes httpx with a 3-attempt exponential backoff retry loop.
    """
    logger = logging.getLogger("verifield.registry.goldstandard")
    
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

    # Prepare real integration payload
    payload = {
        "issuance_request": {
            "source": "VeriField Nexus dMRV Platform",
            "timestamp": datetime.now(timezone.utc).isoformat() if hasattr(datetime, "now") else None,
            "organization": user.organization or "VeriField",
            "total_tco2e": round(total_tco2e, 4),
            "payload_size": len(calcs),
            "credits": [
                {
                    "calculation_id": str(c.id),
                    "activity_id": str(c.activity_id),
                    "tco2e": float(c.tco2e_generated),
                    "methodology": c.methodology_used,
                    "created_at": c.created_at.isoformat() if c.created_at else None
                }
                for c in calcs
            ]
        }
    }

    # Verify if registry API endpoint is configured
    url = settings.goldstandard_api_url
    api_key = settings.goldstandard_api_key

    if not url or not api_key:
        # Dry-run / Configuration Missing Mode: Return generated payload
        logger.warning("Gold Standard API credentials not configured. Returning payload for dry-run/manual upload.")
        # Mark as pending_issuance locally so it's tracked as processed
        for c in calcs:
            c.status = "pending_issuance"
        await db.commit()

        return {
            "registry": "Gold Standard",
            "action": "Dry-run (Configuration Missing)",
            "status": "warning",
            "warning": "Gold Standard API endpoint or key is not set in backend settings. Outputting generated audit payload.",
            "total_tco2e": round(total_tco2e, 4),
            "payload_size": len(calcs),
            "payload": payload,
            "audit_pack_generated": True
        }

    # Execute HTTP call with retry logic
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-VeriField-Audit-Trace": str(uuid.uuid4())
    }

    success = False
    api_response = None
    
    # 3 attempts with exponential backoff: 2s, 4s, 8s
    for attempt in range(3):
        try:
            logger.info(f"Posting to Gold Standard API (attempt {attempt + 1}/3) at {url}...")
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code in (200, 201, 202):
                    success = True
                    api_response = resp.json()
                    logger.info("Successfully posted carbon calculations to Gold Standard API.")
                    break
                else:
                    logger.warning(
                        f"Gold Standard API returned error status {resp.status_code}: {resp.text}. "
                        f"Attempt {attempt + 1}/3."
                    )
                    api_response = {"status_code": resp.status_code, "error": resp.text}
        except Exception as e:
            logger.warning(f"Connection error when calling Gold Standard API: {e}. Attempt {attempt + 1}/3.")
            api_response = {"error": str(e)}

        if attempt < 2:
            await asyncio.sleep(2.0 * (2 ** attempt))

    if not success:
        logger.error("Failed to push carbon calculations to Gold Standard API after 3 retries.")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": "Failed to connect to Gold Standard Registry API terminal.",
                "last_response": api_response
            }
        )

    # Update state in DB upon successful API submission
    for c in calcs:
        c.status = "pending_issuance"
    await db.commit()

    return {
        "registry": "Gold Standard",
        "action": "Issue Request Sent",
        "status": "success",
        "total_tco2e": round(total_tco2e, 4),
        "payload_size": len(calcs),
        "api_response": api_response,
        "audit_pack_generated": True
    }
