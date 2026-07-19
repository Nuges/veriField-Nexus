from typing import Any

from app.domains.ai_trust_engine.schemas import TrustLogResponse as TrustScoreResponse
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.domains.activities.repository import ActivityRepository
from app.domains.activities.schemas import (ActivityCreate,
                                            ActivityListResponse,
                                            ActivityResponse, ActivityUpdate)
from app.domains.activities.service import ActivityService
from app.domains.authentication.models import User
from app.domains.projects.repository import ProjectRepository

router = APIRouter(prefix="/activities", tags=["Activities"])


@router.post("", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
async def create_activity(
    payload: ActivityCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.core.abac import get_abac_engine

    abac = get_abac_engine(db, current_user)
    # Project-level access enforcement removed since activities are decoupled from projects

    org_id = current_user.organization_id

    repo = ActivityRepository(db)
    service = ActivityService(repo)

    # Check deduplication for offline-first clients using client_id
    if payload.client_id:
        existing = await service.get_activity_by_client(payload.client_id, org_id)
        if existing:
            return ActivityResponse.model_validate(existing)

    activity = await service.create_activity(
        payload, user_id=current_user.id, organization_id=org_id
    )
    return ActivityResponse.model_validate(activity)


@router.post("/batch")
async def create_activities_batch(
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.domains.projects.repository import ProjectRepository
    from app.domains.projects.models import Project
    from sqlalchemy import select
    import uuid
    import logging
    
    org_id = current_user.organization_id
    activities_data = payload.get("activities", [])
    results = []

    try:
        repo = ActivityRepository(db)
        service = ActivityService(repo)
        
        for act_data in activities_data:
            client_id = act_data.get("client_id")
            
            # Check deduplication
            if client_id:
                existing = await service.get_activity_by_client(client_id, org_id)
                if existing:
                    results.append({"client_id": client_id, "status": "duplicate"})
                    continue
                    
            # Adapt payload to ActivityCreate
            try:
                activity_create = ActivityCreate(
                    project_id=None,
                    activity_type=act_data.get("activity_type", "unknown"),
                    activity_data=act_data.get("activity_data", {}),
                    description=act_data.get("description"),
                    image_url=act_data.get("image_url"),
                    image_hash=act_data.get("image_hash"),
                    latitude=act_data.get("latitude"),
                    longitude=act_data.get("longitude"),
                    gps_accuracy=act_data.get("gps_accuracy"),
                    captured_at=act_data.get("captured_at", datetime.now().isoformat()),
                    client_id=client_id,
                )
                
                activity = await service.create_activity(
                    activity_create, user_id=current_user.id, organization_id=org_id
                )
                results.append({"client_id": client_id, "status": "submitted", "id": str(activity.id)})
            except Exception as e:
                results.append({"client_id": client_id, "status": "failed", "error": str(e)})

    except BaseException as outer_e:
        logging.error(f"Database error during batch submit: {outer_e}")
        raise HTTPException(status_code=503, detail="Service Unavailable: Database connection failed.")
    return {"results": results}

@router.get("", response_model=ActivityListResponse)
async def list_activities(
    activity_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    user_id: Optional[UUID] = Query(None),
    property_id: Optional[UUID] = Query(None),
    asset_id: Optional[UUID] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    min_trust: Optional[float] = Query(None, ge=0, le=100),
    max_trust: Optional[float] = Query(None, ge=0, le=100),
    duplicate_only: Optional[bool] = Query(None),
    methodology_id: Optional[UUID] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = ActivityRepository(db)

    org_id = current_user.organization_id

    activities, total = await repo.list_activities_paginated(
        organization_id=org_id,
        activity_type=activity_type,
        status=status,
        user_id=user_id,
        property_id=property_id,
        asset_id=asset_id,
        date_from=date_from,
        date_to=date_to,
        min_trust=min_trust,
        max_trust=max_trust,
        duplicate_only=duplicate_only,
        methodology_id=methodology_id,
        page=page,
        per_page=per_page,
        user_role=current_user.role,
        requesting_user_id=current_user.id,
    )

    total_pages = max(1, (total + per_page - 1) // per_page)

    return ActivityListResponse(
        activities=[ActivityResponse.model_validate(a) for a in activities],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


@router.get("/{activity_id}", response_model=ActivityResponse)
async def get_activity(
    activity_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = ActivityRepository(db)
    service = ActivityService(repo)

    org_id = (
        current_user.organization_id if current_user.role != "SUPER_ADMIN" else None
    )
    activity = await service.get_activity(activity_id, org_id)
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    return ActivityResponse.model_validate(activity)


@router.put("/{activity_id}", response_model=ActivityResponse)
async def update_activity(
    activity_id: UUID,
    payload: ActivityUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = ActivityRepository(db)
    service = ActivityService(repo)

    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(
            status_code=400, detail="User must belong to an organization."
        )

    updated = await service.update_activity_status(activity_id, payload, org_id)
    if not updated:
        raise HTTPException(
            status_code=404, detail="Activity not found or unauthorized."
        )
    return ActivityResponse.model_validate(updated)


import logging
# from app.schemas.analytics import TrustScoreResponse
import os
import shutil
import uuid

from fastapi import File, Request, UploadFile
from pydantic import BaseModel

from app.domains.ai_trust_engine.models import TrustLog


class DuplicateCheckRequest(BaseModel):
    latitude: float
    longitude: float
    activity_type: str


@router.post("/check-duplicate")
async def check_duplicate(
    payload: DuplicateCheckRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    from app.domains.activities.models import Activity as ActivityModel

    # Basic native duplicate check: find any verified activity of same type within tiny bounding box
    lat_tolerance = 0.0003  # roughly 30 meters
    lon_tolerance = 0.0003

    stmt = select(ActivityModel).where(
        ActivityModel.activity_type == payload.activity_type,
        ActivityModel.status == "verified",
        ActivityModel.latitude.between(payload.latitude - lat_tolerance, payload.latitude + lat_tolerance),
        ActivityModel.longitude.between(payload.longitude - lon_tolerance, payload.longitude + lon_tolerance)
    )
    result = await db.execute(stmt)
    duplicate = result.scalars().first()

    if duplicate:
        return {"is_duplicate": True, "duplicate_id": str(duplicate.id), "distance_meters": 15.0}
    return {"is_duplicate": False}


@router.post("/upload-proof")
async def upload_proof(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
        raise HTTPException(
            status_code=400,
            detail="Only JPG, JPEG, PNG, GIF, and WEBP images are supported.",
        )

    os.makedirs(os.path.join("static", "proofs"), exist_ok=True)
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    target_path = os.path.join("static", "proofs", unique_filename)

    try:
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Could not save uploaded file: {str(e)}",
        )

    base_url = str(request.base_url).rstrip("/")
    if "127.0.0.1:8000" in base_url or "localhost:8000" in base_url:
        base_url = base_url.replace("https://", "http://")
    proof_url = f"{base_url}/static/proofs/{unique_filename}"

    return {"image_url": proof_url}


@router.get("/{activity_id}/trust", response_model=TrustScoreResponse)
async def get_trust_score(
    activity_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select

    from app.domains.activities.models import Activity as ActivityModel

    # Check access permission
    result = await db.execute(
        select(ActivityModel).where(ActivityModel.id == activity_id)
    )
    activity = result.scalar_one_or_none()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity/Installation not found")

    if current_user.role == "SUPER_ADMIN":
        pass
    elif current_user.role in ("admin", "ORG_ADMIN"):
        if activity.organization_id != current_user.organization_id:
            raise HTTPException(status_code=403, detail="Access denied")
    else:
        if activity.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

    result = await db.execute(
        select(TrustLog)
        .where(TrustLog.activity_id == activity_id)
        .order_by(TrustLog.calculated_at.desc())
        .limit(1)
    )
    trust_log = result.scalars().first()
    if not trust_log:
        raise HTTPException(status_code=404, detail="Trust score not calculated yet")
    return TrustScoreResponse.model_validate(trust_log)


class ActivityStatusUpdate(BaseModel):
    status: str


@router.patch("/{activity_id}/status", response_model=ActivityResponse)
async def update_activity_status_patch(
    activity_id: UUID,
    payload: ActivityStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.domains.activities.models import Activity as ActivityModel

    if current_user.role not in ("SUPER_ADMIN", "admin", "ORG_ADMIN"):
        raise HTTPException(
            status_code=403, detail="Only admins can update activity status"
        )

    result = await db.execute(
        select(ActivityModel)
        .options(selectinload(ActivityModel.user))
        .where(ActivityModel.id == activity_id)
    )
    activity = result.scalar_one_or_none()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    if activity.is_locked:
        raise HTTPException(
            status_code=400,
            detail="CSI compliance lock: Locked audit records cannot be edited.",
        )

    if current_user.role != "SUPER_ADMIN":
        if activity.organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied. Activity belongs to another organization.",
            )

    activity.status = payload.status
    await db.commit()
    await db.refresh(activity)

    if activity.status == "verified":
        try:
            # 1. Create Asset if it doesn't exist
            if not activity.asset_id:
                from app.domains.assets.service import AssetService
                from app.domains.assets.repository import AssetRepository
                from app.domains.assets.schemas import AssetCreate
                
                project_id = activity.organization_id # Fallback
                if activity.property_id:
                    from app.domains.workspaces.models import Workspace
                    workspace = await db.get(Workspace, activity.property_id)
                    if workspace and workspace.project_id:
                        project_id = workspace.project_id

                asset_service = AssetService(AssetRepository(db))
                new_asset_schema = AssetCreate(
                    project_id=project_id,
                    name=f"Asset from Activity {activity.id}",
                    latitude=activity.latitude,
                    longitude=activity.longitude,
                    attributes=activity.activity_data
                )
                new_asset = await asset_service.create_asset(new_asset_schema, activity.organization_id)
                activity.asset_id = new_asset.id
                await db.commit()

            # 2. Run Carbon Calculation
            from app.domains.projects.service import CarbonCalculationService
            calc_service = CarbonCalculationService(db)
            
            tco2e_yield = float(activity.activity_data.get("estimated_carbon", 5.0))
            project_id_for_calc = activity.organization_id
            if activity.asset_id:
                from app.domains.assets.models import Asset
                asset_obj = await db.get(Asset, activity.asset_id)
                if asset_obj and asset_obj.project_id:
                    project_id_for_calc = asset_obj.project_id

            calc_record = await calc_service.create_calculation({
                "project_id": project_id_for_calc,
                "activity_id": activity.id,
                "tco2e_yield": tco2e_yield,
                "uncertainty": 0.05,
                "execution_inputs": activity.activity_data,
                "execution_outputs": {"tco2e": tco2e_yield, "manual_override": True},
            })
            logging.getLogger("verifield.api").info(f"Manual carbon calculation carried out. tCO2e: {tco2e_yield}")
            
        except Exception as e:
            logging.getLogger("verifield.api").error(
                f"Manual pipeline execution failed for {activity.id}: {e}"
            )

    # Re-fetch to load user info
    result = await db.execute(
        select(ActivityModel)
        .options(selectinload(ActivityModel.user))
        .where(ActivityModel.id == activity_id)
    )
    activity = result.scalar_one_or_none()

    return ActivityResponse.model_validate(activity)
