from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.domains.authentication.models import User

from .repository import VerificationRepository
from .schemas import (AuditReportCreate, AuditReportResponse,
                      VerificationTaskCreate, VerificationTaskResponse)
from .service import VerificationService

router = APIRouter()


def get_verification_service(db: AsyncSession = Depends(get_db)) -> VerificationService:
    repository = VerificationRepository(db)
    return VerificationService(repository)


@router.post(
    "/tasks",
    response_model=VerificationTaskResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_verification_task(
    data: VerificationTaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: VerificationService = Depends(get_verification_service),
):
    return await service.create_verification_task(data, actor_id=current_user.id, db=db)


@router.get("/tasks", response_model=list[VerificationTaskResponse])
async def get_verification_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: VerificationService = Depends(get_verification_service),
):
    return await service.get_tasks()


@router.get("/tasks/{task_id}", response_model=VerificationTaskResponse)
async def get_verification_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: VerificationService = Depends(get_verification_service),
):
    task = await service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


from pydantic import BaseModel
class TaskUpdate(BaseModel):
    status: Optional[str] = None
    deadline: Optional[str] = None
    assigned_agent: Optional[str] = None

@router.patch("/tasks/{task_id}", response_model=VerificationTaskResponse)
async def update_verification_task(
    task_id: UUID,
    data: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: VerificationService = Depends(get_verification_service),
):
    # For now just update the status via the existing service method if provided
    if data.status:
        updated = await service.repository.update_task_status(task_id, data.status, {})
        if not updated:
            raise HTTPException(status_code=404, detail="Task not found")
        return updated
    
    # If just updating agent/deadline, return the task for now
    return await service.get_task(task_id)


@router.post(
    "/audits", response_model=AuditReportResponse, status_code=status.HTTP_201_CREATED
)
async def submit_audit_report(
    data: AuditReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: VerificationService = Depends(get_verification_service),
):
    return await service.submit_audit_report(data, actor_id=current_user.id, db=db)

@router.get("/sensors/{asset_id}")
async def get_sensor_readings(
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=501,
        content={"detail": "Sensor telemetry integration not yet implemented", "asset_id": asset_id},
    )

@router.get("/community/{asset_id}")
async def get_asset_community_validations(
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "SUPER_ADMIN" and current_user.organization_id:
        from sqlalchemy import text
        # Verify asset ownership if asset is a UUID
        try:
            from uuid import UUID
            asset_uuid = UUID(asset_id)
            chk_query = text("SELECT organization_id FROM assets WHERE id = :aid")
            asset_res = await db.execute(chk_query, {"aid": asset_uuid})
            asset_row = asset_res.mappings().first()
            if asset_row and asset_row["organization_id"] != current_user.organization_id:
                raise HTTPException(status_code=403, detail="Access to asset in another organization forbidden")
        except ValueError:
            pass

    from sqlalchemy import text
    query = text("SELECT id, asset_id, validator_id, response, timestamp FROM community_validations WHERE asset_id = :aid ORDER BY timestamp DESC")
    res = await db.execute(query, {"aid": asset_id})
    return [dict(r) for r in res.mappings().all()]

