from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.methodologies.models.base_registry import (Methodology,
                                                            MethodologyVersion)


class MethodologyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_methodology(self, meth_id: UUID) -> Optional[Methodology]:
        result = await self.db.execute(
            select(Methodology)
            .options(
                selectinload(Methodology.registry),
                selectinload(Methodology.family),
                selectinload(Methodology.versions),
            )
            .where(Methodology.id == meth_id)
        )
        return result.scalars().first()

    async def get_methodology_by_code(self, code: str) -> Optional[Methodology]:
        result = await self.db.execute(
            select(Methodology)
            .options(
                selectinload(Methodology.registry),
                selectinload(Methodology.family),
                selectinload(Methodology.versions),
            )
            .where(Methodology.code == code)
        )
        return result.scalars().first()

    async def list_methodologies(self) -> List[Methodology]:
        result = await self.db.execute(
            select(Methodology)
            .options(
                selectinload(Methodology.registry),
                selectinload(Methodology.family),
                selectinload(Methodology.versions),
            )
            .order_by(Methodology.code)
        )
        return list(result.scalars().all())

    async def get_active_version(self, meth_id: UUID) -> Optional[MethodologyVersion]:
        stmt = (
            select(MethodologyVersion)
            .where(
                MethodologyVersion.methodology_id == meth_id,
                MethodologyVersion.status == "active",
            )
            .order_by(MethodologyVersion.release_date.desc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def create_methodology(self, data: dict) -> Methodology:
        meth = Methodology(**data)
        self.db.add(meth)
        await self.db.commit()
        await self.db.refresh(meth)
        return meth

    async def create_methodology_version(
        self, meth_id: UUID, data: dict
    ) -> MethodologyVersion:
        version = MethodologyVersion(methodology_id=meth_id, **data, status="draft")
        self.db.add(version)
        await self.db.commit()
        await self.db.refresh(version)
        return version

    async def update_version_status(
        self, version_id: UUID, status: str, retirement_date=None
    ) -> Optional[MethodologyVersion]:
        result = await self.db.execute(
            select(MethodologyVersion).where(MethodologyVersion.id == version_id)
        )
        version = result.scalars().first()
        if not version:
            return None

        # If setting to active, we might want to deprecate others, but for now just update status
        version.status = status
        if retirement_date:
            version.retirement_date = retirement_date

        await self.db.commit()
        await self.db.refresh(version)
        return version
