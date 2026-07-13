from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.evidence.models import Evidence


class EvidenceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, evidence_id: UUID) -> Optional[Evidence]:
        stmt = select(Evidence).where(Evidence.id == evidence_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_by_activity(
        self, activity_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Evidence]:
        stmt = (
            select(Evidence)
            .where(Evidence.activity_id == activity_id)
            .offset(skip)
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def create(self, evidence: Evidence) -> Evidence:
        self.db.add(evidence)
        await self.db.commit()
        await self.db.refresh(evidence)
        return evidence

    async def update_status(
        self, evidence_id: UUID, status: str, verified_by: Optional[UUID] = None
    ) -> Optional[Evidence]:
        stmt = (
            update(Evidence)
            .where(Evidence.id == evidence_id)
            .values(status=status, verified_by=verified_by)
            .returning(Evidence)
        )
        res = await self.db.execute(stmt)
        await self.db.commit()
        return res.scalar_one_or_none()
