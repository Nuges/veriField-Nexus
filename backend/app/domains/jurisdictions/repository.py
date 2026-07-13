from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.jurisdictions.models import Jurisdiction


class JurisdictionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, jurisdiction_id: UUID) -> Optional[Jurisdiction]:
        stmt = select(Jurisdiction).where(
            Jurisdiction.id == jurisdiction_id, Jurisdiction.is_deleted == False
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Optional[Jurisdiction]:
        stmt = select(Jurisdiction).where(
            Jurisdiction.code == code, Jurisdiction.is_deleted == False
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_all(self, limit: int = 100, offset: int = 0) -> List[Jurisdiction]:
        stmt = (
            select(Jurisdiction)
            .where(Jurisdiction.is_deleted == False)
            .limit(limit)
            .offset(offset)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def create(self, jurisdiction: Jurisdiction) -> Jurisdiction:
        self.db.add(jurisdiction)
        await self.db.commit()
        await self.db.refresh(jurisdiction)
        return jurisdiction

    async def update(self, jurisdiction: Jurisdiction) -> Jurisdiction:
        try:
            self.db.add(jurisdiction)
            await self.db.commit()
            await self.db.refresh(jurisdiction)
            return jurisdiction
        except Exception as e:
            await self.db.rollback()
            if "StaleDataError" in str(type(e)):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Update failed: the record was modified by another transaction.",
                )
            raise

    async def soft_delete(self, jurisdiction: Jurisdiction) -> Jurisdiction:
        jurisdiction.is_deleted = True
        jurisdiction.deleted_at = datetime.now(timezone.utc)
        jurisdiction.status = "DELETED"
        return await self.update(jurisdiction)
