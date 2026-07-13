import asyncio
from typing import List, Optional
from uuid import UUID

from app.domains.reporting.models import Report
from app.domains.reporting.repository import ReportRepository
from app.domains.reporting.schemas import ReportCreate


class ReportingService:
    def __init__(self, repository: ReportRepository):
        self.repository = repository

    async def get_report(self, report_id: UUID) -> Optional[Report]:
        return await self.repository.get_by_id(report_id)

    async def list_reports(
        self, org_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Report]:
        return await self.repository.list_for_org(org_id, skip=skip, limit=limit)

    async def generate_report(
        self, payload: ReportCreate, creator_id: Optional[UUID] = None
    ) -> Report:
        report = Report(
            org_id=payload.org_id,
            title=payload.title,
            report_type=payload.report_type,
            parameters=payload.parameters,
            created_by=creator_id,
            status="GENERATING",
        )
        created = await self.repository.create(report)

        # Dispatch background generation (simulated here)
        asyncio.create_task(self._mock_generation(created.id))

        return created

    async def _mock_generation(self, report_id: UUID):
        await asyncio.sleep(2)  # Simulate generation time
        await self.repository.update_status(
            report_id,
            status="COMPLETED",
            file_uri=f"s3://verifield-nexus-reports/{report_id}.pdf",
        )
