from typing import Any

TrustScoreResponse = Any
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
    proj_repo = ProjectRepository(db)
    project = await proj_repo.get_by_id(payload.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Associated Project not found")

    from app.core.abac import get_abac_engine

    abac = get_abac_engine(db, current_user)
    await abac.enforce_project_access(payload.project_id)
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


@router.get("", response_model=ActivityListResponse)
async def list_activities(
    activity_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    user_id: Optional[UUID] = Query(None),
    property_id: Optional[UUID] = Query(None),
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
    #     from app.services.gps_validator import GPSValidator

    validator = GPSValidator(db)
    result = await validator.check_duplicate(
        payload.latitude, payload.longitude, payload.activity_type
    )
    return result


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
        select(TrustLog).where(TrustLog.activity_id == activity_id)
    )
    trust_log = result.scalar_one_or_none()
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
            #             from app.services.quantification_engine import QuantificationEngine

            quant_engine = QuantificationEngine(db)
            await quant_engine.quantify_activity(activity.id, None)
        except Exception as e:
            logging.getLogger("verifield.api").error(
                f"Manual quantification failed for {activity.id}: {e}"
            )

        try:
            #             from app.services.blockchain import anchor_activity_on_chain

            await anchor_activity_on_chain(activity, db)
        except Exception as e:
            logging.getLogger("verifield.api").error(
                f"Manual blockchain anchoring failed for {activity.id}: {e}"
            )

    # Re-fetch to load user info
    result = await db.execute(
        select(ActivityModel)
        .options(selectinload(ActivityModel.user))
        .where(ActivityModel.id == activity_id)
    )
    activity = result.scalar_one_or_none()

    return ActivityResponse.model_validate(activity)
