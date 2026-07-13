from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.programmes.models import ClimateProgramme


class ProgrammeRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, programme_id: UUID) -> Optional[ClimateProgramme]:
        stmt = select(ClimateProgramme).where(
            ClimateProgramme.id == programme_id, ClimateProgramme.is_deleted == False
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_all(self, skip: int = 0, limit: int = 100) -> List[ClimateProgramme]:
        stmt = (
            select(ClimateProgramme)
            .where(ClimateProgramme.is_deleted == False)
            .offset(skip)
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def create(self, programme: ClimateProgramme) -> ClimateProgramme:
        self.db.add(programme)
        await self.db.commit()
        await self.db.refresh(programme)
        return programme
