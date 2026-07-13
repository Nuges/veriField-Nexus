from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.marketplace.models import Listing


class MarketplaceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, listing_id: UUID) -> Optional[Listing]:
        stmt = select(Listing).where(Listing.id == listing_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_active(self, skip: int = 0, limit: int = 100) -> List[Listing]:
        stmt = (
            select(Listing).where(Listing.status == "ACTIVE").offset(skip).limit(limit)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def create(self, listing: Listing) -> Listing:
        self.db.add(listing)
        await self.db.commit()
        await self.db.refresh(listing)
        return listing

    async def update_status(self, listing_id: UUID, status: str) -> Optional[Listing]:
        stmt = (
            update(Listing)
            .where(Listing.id == listing_id)
            .values(status=status)
            .returning(Listing)
        )
        res = await self.db.execute(stmt)
        await self.db.commit()
        return res.scalar_one_or_none()
