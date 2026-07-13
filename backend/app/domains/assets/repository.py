from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.assets.models import Asset


class AssetRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(
        self, asset_id: UUID, organization_id: Optional[UUID] = None
    ) -> Optional[Asset]:
        stmt = select(Asset).where(Asset.id == asset_id)
        if organization_id:
            stmt = stmt.where(Asset.organization_id == organization_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_by_organization(
        self, organization_id: UUID, project_id: Optional[UUID] = None
    ) -> List[Asset]:
        stmt = select(Asset).where(Asset.organization_id == organization_id)
        if project_id:
            stmt = stmt.where(Asset.project_id == project_id)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def list_by_project(self, project_id: UUID) -> List[Asset]:
        stmt = select(Asset).where(Asset.project_id == project_id)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def create(self, asset: Asset) -> Asset:
        self.db.add(asset)
        await self.db.commit()
        await self.db.refresh(asset)
        return asset

    async def update(self, asset: Asset) -> Asset:
        await self.db.commit()
        await self.db.refresh(asset)
        return asset

    async def delete(self, asset: Asset) -> None:
        await self.db.delete(asset)
        await self.db.commit()
