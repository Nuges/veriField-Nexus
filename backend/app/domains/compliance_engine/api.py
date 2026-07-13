from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.domains.authentication.models import User
from app.domains.compliance_engine.service import ComplianceService

router = APIRouter(prefix="/compliance", tags=["Compliance Engine"])


@router.post("/project/{project_id}/evaluate")
async def evaluate_project_compliance(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
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
