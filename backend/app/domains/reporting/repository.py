from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.reporting.models import Report


class ReportRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, report_id: UUID) -> Optional[Report]:
        stmt = select(Report).where(Report.id == report_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_for_org(
        self, org_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Report]:
        stmt = select(Report).where(Report.org_id == org_id)
        stmt = stmt.order_by(Report.created_at.desc()).offset(skip).limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def create(self, report: Report) -> Report:
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)
        return report

    async def update_status(
        self, report_id: UUID, status: str, file_uri: Optional[str] = None
    ) -> Optional[Report]:
        updates = {"status": status}
        if file_uri is not None:
            updates["file_uri"] = file_uri

        stmt = (
            update(Report)
            .where(Report.id == report_id)
            .values(**updates)
            .returning(Report)
        )
        res = await self.db.execute(stmt)
        await self.db.commit()
        return res.scalar_one_or_none()
