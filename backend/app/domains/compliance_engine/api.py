from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import require_permission, normalize_canonical_role, ROLE_SUPER_ADMIN
from app.db.session import get_db
from app.domains.authentication.models import User
from app.domains.compliance_engine.service import ComplianceService
from app.domains.projects.models import Project

router = APIRouter(prefix="/compliance", tags=["Compliance Engine"])


@router.post("/project/{project_id}/evaluate")
async def evaluate_project_compliance(
    project_id: UUID,
    current_user: User = Depends(require_permission("compliance:read")),
    db: AsyncSession = Depends(get_db),
):
    canonical = normalize_canonical_role(current_user.role)
    if canonical != ROLE_SUPER_ADMIN:
        proj_stmt = select(Project).where(Project.id == project_id)
        proj_res = await db.execute(proj_stmt)
        project = proj_res.scalar_one_or_none()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        if not current_user.organization_id or str(project.organization_id).lower() != str(current_user.organization_id).lower():
            raise HTTPException(status_code=403, detail="Forbidden: Cannot evaluate compliance for another organization's project.")

    service = ComplianceService(db)
    try:
        run = await service.evaluate_project(project_id)
        return {
            "project_id": str(run.project_id),
            "eligibility_status": run.eligibility_status,
            "sampling_status": run.sampling_status,
            "conformance_issues": run.conformance_issues,
            "risk_score": run.risk_score,
            "last_evaluated": run.last_evaluated.isoformat(),
        }
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
