from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.verification.models import AuditReport, VerificationTask


class VerificationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_task_by_id(self, task_id: UUID) -> Optional[VerificationTask]:
        stmt = select(VerificationTask).where(VerificationTask.id == task_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_tasks(self) -> list[VerificationTask]:
        stmt = select(VerificationTask).order_by(VerificationTask.created_at.desc())
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def create_task(self, task: VerificationTask) -> VerificationTask:
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def update_task_status(
        self, task_id: UUID, status: str, findings: Dict[str, Any]
    ) -> Optional[VerificationTask]:
        stmt = (
            update(VerificationTask)
            .where(VerificationTask.id == task_id)
            .values(status=status, findings=findings)
            .returning(VerificationTask)
        )
        res = await self.db.execute(stmt)
        await self.db.commit()
        return res.scalar_one_or_none()

    async def create_audit_report(self, report: AuditReport) -> AuditReport:
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)
        return report
