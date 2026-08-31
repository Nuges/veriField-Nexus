from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import require_permission, validate_separation_of_duties, normalize_canonical_role, ROLE_SUPER_ADMIN
from app.core.security import get_current_user
from app.db.session import get_db
from app.domains.authentication.models import User
from app.domains.projects.models import Project

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
    current_user: User = Depends(require_permission("audit:write")),
    service: VerificationService = Depends(get_verification_service),
):
    return await service.create_verification_task(data, actor_id=current_user.id, db=db)


@router.get("", response_model=None)
@router.get("/", response_model=None)
@router.get("/tasks", response_model=None)
@router.get("/audits", response_model=None)
async def get_audits_endpoint(
    status: Optional[str] = None,
    per_page: int = 50,
    page: int = 1,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("audit:read")),
    service: VerificationService = Depends(get_verification_service),
):
    tasks = await service.get_tasks()
    user_canonical = normalize_canonical_role(current_user.role)

    # Scoping: If not super admin, resolve projects in user's tenant or assigned to user
    permitted_project_ids = set()
    if user_canonical != ROLE_SUPER_ADMIN and current_user.organization_id:
        proj_stmt = select(Project.id).where(
            Project.organization_id == current_user.organization_id,
            Project.is_deleted == False,
        )
        proj_res = await db.execute(proj_stmt)
        permitted_project_ids = {row[0] for row in proj_res.fetchall()}

    audits = []
    for t in tasks:
        t_status = (t.status or "pending").lower()
        if status and status.lower() != "all" and t_status != status.lower():
            continue

        # Tenant & Verifier scope check
        if user_canonical != ROLE_SUPER_ADMIN:
            is_assigned = t.verifier_id and str(t.verifier_id) == str(current_user.id)
            is_org_project = t.project_id in permitted_project_ids
            if not is_assigned and not is_org_project:
                continue

        audits.append({
            "id": str(t.id),
            "status": t.status or "pending",
            "deadline": t.deadline.isoformat() if t.deadline else None,
            "property_name": "Registered Carbon Asset",
            "property_address": "Federal Capital Territory, Nigeria",
            "property_type": "Clean Energy",
            "agent_name": "Field Auditor",
            "assigned_agent": str(t.verifier_id) if t.verifier_id else None,
            "findings": t.findings or {},
            "created_at": t.created_at.isoformat() if t.created_at else None
        })
    return {"audits": audits, "total": len(audits), "page": page, "per_page": per_page}


@router.get("/tasks/{task_id}")
@router.get("/audits/{task_id}")
@router.get("/{task_id}")
async def get_audit_by_id(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("audit:read")),
    service: VerificationService = Depends(get_verification_service),
):
    task = await service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Audit task not found")
    return {
        "id": str(task.id),
        "status": task.status or "pending",
        "deadline": task.deadline.isoformat() if task.deadline else None,
        "property_name": "Registered Carbon Asset",
        "property_address": "Federal Capital Territory, Nigeria",
        "property_type": "Clean Energy",
        "agent_name": "Field Auditor",
        "assigned_agent": str(task.verifier_id) if task.verifier_id else None,
        "findings": task.findings or {},
        "created_at": task.created_at.isoformat() if task.created_at else None
    }


from pydantic import BaseModel
class TaskUpdate(BaseModel):
    status: Optional[str] = None
    deadline: Optional[str] = None
    assigned_agent: Optional[str] = None

@router.patch("/tasks/{task_id}")
@router.patch("/audits/{task_id}")
@router.patch("/{task_id}")
async def update_verification_task(
    task_id: UUID,
    data: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("audit:write")),
    service: VerificationService = Depends(get_verification_service),
):
    if data.status:
        updated = await service.repository.update_task_status(task_id, data.status, {})
        if not updated:
            raise HTTPException(status_code=404, detail="Task not found")
        return updated
    
    return await service.get_task(task_id)


@router.post(
    "/audits", response_model=AuditReportResponse, status_code=status.HTTP_201_CREATED
)
async def submit_audit_report(
    data: AuditReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("audit:write")),
    service: VerificationService = Depends(get_verification_service),
):
    # Enforce Separation of Duties: Check if actor is the developer of the project
    proj_stmt = select(Project).where(Project.id == data.project_id)
    proj_res = await db.execute(proj_stmt)
    proj = proj_res.scalar_one_or_none()
    developer_id = proj.developer_id if proj else None

    validate_separation_of_duties(current_user, developer_id, action="VERIFY")

    return await service.submit_audit_report(data, actor_id=current_user.id, db=db)


@router.get("/sensors/{asset_id}")
async def get_sensor_readings(
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("asset:read")),
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
    current_user: User = Depends(require_permission("asset:read")),
):
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=501,
        content={"detail": "Community validations integration not yet implemented", "asset_id": asset_id},
    )
