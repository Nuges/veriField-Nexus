from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_bus import EventBus
from app.domains.marketplace.models import Listing
from app.domains.marketplace.repository import MarketplaceRepository
from app.domains.marketplace.schemas import ListingCreate


class MarketplaceService:
    def __init__(self, repository: MarketplaceRepository):
        self.repository = repository

    async def get_listing(self, listing_id: UUID) -> Optional[Listing]:
        return await self.repository.get_by_id(listing_id)

    async def list_active_listings(
        self, skip: int = 0, limit: int = 100
    ) -> List[Listing]:
        return await self.repository.list_active(skip=skip, limit=limit)

    async def create_listing(
        self, payload: ListingCreate, actor_id: UUID, db: Optional[AsyncSession] = None
    ) -> Listing:
        listing = Listing(
            org_id=payload.org_id,
            project_id=payload.project_id,
            quantity=payload.quantity,
            price_per_unit=payload.price_per_unit,
            currency=payload.currency,
            status="ACTIVE",
        )
        created = await self.repository.create(listing)

        if db:
            await EventBus.publish(
                stream_name="marketplace_events",
                event_type="ListingCreated",
                payload={
                    "listing_id": str(created.id),
                    "project_id": str(created.project_id),
                    "quantity": created.quantity,
                },
                actor_id=str(actor_id),
            )

        return created

    async def cancel_listing(
        self, listing_id: UUID, actor_id: UUID, db: Optional[AsyncSession] = None
    ) -> Optional[Listing]:
        updated = await self.repository.update_status(listing_id, "CANCELLED")
        if updated and db:
            await EventBus.publish(
                stream_name="marketplace_events",
                event_type="ListingCancelled",
                payload={"listing_id": str(updated.id)},
                actor_id=str(actor_id),
            )
        return updated
