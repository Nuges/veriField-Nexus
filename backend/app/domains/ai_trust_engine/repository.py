from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.ai_trust_engine.models import TrustLog


class TrustEngineRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_activity(self, activity_id: UUID) -> Optional[TrustLog]:
        stmt = select(TrustLog).where(TrustLog.activity_id == activity_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_id(self, log_id: UUID) -> Optional[TrustLog]:
        stmt = select(TrustLog).where(TrustLog.id == log_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_recent(self, skip: int = 0, limit: int = 100) -> List[TrustLog]:
        stmt = (
            select(TrustLog)
            .order_by(TrustLog.calculated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def create(self, log: TrustLog) -> TrustLog:
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        return log
