from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.domains.authentication.models import User
from app.domains.reporting.repository import ReportRepository
from app.domains.reporting.schemas import ReportCreate, ReportResponse
from app.domains.reporting.service import ReportingService

router = APIRouter(tags=["Reporting"])


def get_reporting_service(db: AsyncSession = Depends(get_db)) -> ReportingService:
    repository = ReportRepository(db)
    return ReportingService(repository)


@router.get("/", response_model=List[ReportResponse])
async def list_org_reports(
    org_id: UUID,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    service: ReportingService = Depends(get_reporting_service),
):
    # In a full impl, check if current_user belongs to org_id
    return await service.list_reports(org_id, skip=skip, limit=limit)


@router.post("/", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    data: ReportCreate,
    current_user: User = Depends(get_current_user),
    service: ReportingService = Depends(get_reporting_service),
):
    return await service.generate_report(data, creator_id=current_user.id)


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ReportingService = Depends(get_reporting_service),
):
    report = await service.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report
