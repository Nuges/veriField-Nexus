from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.domains.authentication.models import User

from .repository import MarketplaceRepository
from .schemas import ListingCreate, ListingResponse
from .service import MarketplaceService

router = APIRouter()


def get_marketplace_service(db: AsyncSession = Depends(get_db)) -> MarketplaceService:
    repository = MarketplaceRepository(db)
    return MarketplaceService(repository)


@router.post(
    "/listings", response_model=ListingResponse, status_code=status.HTTP_201_CREATED
)
async def create_listing(
    data: ListingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: MarketplaceService = Depends(get_marketplace_service),
):
    if current_user.role not in ["SUPER_ADMIN", "ORG_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized to create listings")

    return await service.create_listing(data, actor_id=current_user.id, db=db)


@router.get("/listings", response_model=List[ListingResponse])
async def list_active_listings(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    service: MarketplaceService = Depends(get_marketplace_service),
):
    return await service.list_active_listings(skip=skip, limit=limit)


@router.get("/listings/{listing_id}", response_model=ListingResponse)
async def get_listing(
    listing_id: UUID,
    db: AsyncSession = Depends(get_db),
    service: MarketplaceService = Depends(get_marketplace_service),
):
    listing = await service.get_listing(listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing
