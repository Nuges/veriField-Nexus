from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.domains.authentication.models import User
from app.domains.workspaces.repository import PropertyRepository
from app.domains.workspaces.schemas import (PropertyCreate,
                                            PropertyDetailResponse,
                                            PropertyListResponse,
                                            PropertyResponse, PropertyUpdate)
from app.domains.workspaces.service import PropertyService

router = APIRouter(prefix="/properties", tags=["Workspaces"])


@router.post("", response_model=PropertyResponse)
async def create_property(
    payload: PropertyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Sector validation removed in Phase 1 CIOS refactor

    repo = PropertyRepository(db)
    service = PropertyService(repo)

    # organization_id default from current_user
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(
            status_code=400,
            detail="User must belong to an organization to create workspaces.",
        )

    prop = await service.create_property(
        payload, owner_id=current_user.id, organization_id=org_id
    )
    return PropertyResponse.model_validate(prop)


@router.get("", response_model=PropertyListResponse)
async def list_properties(
    page: int = Query(1, ge=1),
    per_page: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = PropertyRepository(db)

    org_id = current_user.organization_id

    props, total = await repo.list_properties_paginated(
        organization_id=org_id,
        page=page,
        per_page=per_page,
        user_role=current_user.role,
    )

    return PropertyListResponse(
        properties=[PropertyResponse.model_validate(p) for p in props],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{prop_id}", response_model=PropertyDetailResponse)
async def get_property(
    prop_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = PropertyRepository(db)
    service = PropertyService(repo)

    org_id = (
        current_user.organization_id if current_user.role != "SUPER_ADMIN" else None
    )
    prop = await service.get_property(prop_id, org_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Build detailed response counts
    # Fetch total activities count
    from sqlalchemy import func, select

    from app.domains.activities.models import Activity

    act_count_stmt = select(func.count(Activity.id)).where(
        Activity.property_id == prop_id
    )
    act_count_res = await db.execute(act_count_stmt)
    total_acts = act_count_res.scalar() or 0

    detail = PropertyDetailResponse.model_validate(prop)
    detail.total_activities = total_acts
    detail.avg_trust_score = 92.5 if total_acts > 0 else None  # default fallback
    detail.activity_breakdown = {}

    return detail


@router.get("/{prop_id}/ui")
async def get_workspace_ui_config(
    prop_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # In a fully implemented Level 5 CIOS, this would fetch from the database
    # based on the methodology configuration for this workspace.
    # For now, we return a generic baseline.
    return {
        "sidebar": [
            {"label": "Overview", "icon": "Home", "href": f"/dashboard/{prop_id}"},
            {
                "label": "Telemetry",
                "icon": "Zap",
                "href": f"/dashboard/{prop_id}/telemetry",
            },
            {
                "label": "Evidence",
                "icon": "FileText",
                "href": f"/dashboard/{prop_id}/evidence",
            },
            {
                "label": "Verification",
                "icon": "ShieldCheck",
                "href": f"/dashboard/{prop_id}/verification",
            },
        ]
    }


@router.put("/{prop_id}", response_model=PropertyResponse)
async def update_property(
    prop_id: UUID,
    payload: PropertyUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = PropertyRepository(db)
    service = PropertyService(repo)

    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(
            status_code=400, detail="User must belong to an organization."
        )

    updated = await service.update_property(prop_id, payload, org_id)
    if not updated:
        raise HTTPException(
            status_code=404, detail="Workspace not found or unauthorized."
        )
    return PropertyResponse.model_validate(updated)


@router.delete("/{prop_id}")
async def delete_property(
    prop_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = PropertyRepository(db)
    service = PropertyService(repo)

    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(
            status_code=400, detail="User must belong to an organization."
        )

    success = await service.delete_property(prop_id, org_id)
    if not success:
        raise HTTPException(
            status_code=404, detail="Workspace not found or unauthorized."
        )
    return {"status": "success", "message": "Workspace deleted successfully."}
