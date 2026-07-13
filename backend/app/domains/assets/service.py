from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from app.domains.assets.events import publish_asset_created
from app.domains.assets.models import Asset
from app.domains.assets.repository import AssetRepository
from app.domains.assets.schemas import AssetCreate, AssetUpdate


class AssetService:
    def __init__(self, repository: AssetRepository):
        self.repository = repository

    async def get_asset(
        self, asset_id: UUID, organization_id: Optional[UUID] = None
    ) -> Optional[Asset]:
        return await self.repository.get_by_id(asset_id, organization_id)

    async def list_assets(
        self, organization_id: UUID, project_id: Optional[UUID] = None
    ) -> List[Asset]:
        return await self.repository.list_by_organization(organization_id, project_id)

    async def create_asset(self, payload: AssetCreate, organization_id: UUID) -> Asset:
        # Schema validation will be handled by the Methodology Engine (Phase 5)
        # validate_asset_attributes(payload.attributes or {}, schema)

        asset = Asset(
            organization_id=organization_id,
            project_id=payload.project_id,
            name=payload.name,
            asset_type_id=payload.asset_type_id,
            status="active",
            latitude=payload.latitude,
            longitude=payload.longitude,
            attributes=payload.attributes or {},
            created_at=datetime.now(timezone.utc),
        )

        created = await self.repository.create(asset)
        await publish_asset_created(
            str(created.id), str(organization_id), str(payload.project_id)
        )
        return created

    async def update_asset(
        self, asset_id: UUID, payload: AssetUpdate, organization_id: UUID
    ) -> Optional[Asset]:
        asset = await self.repository.get_by_id(asset_id, organization_id)
        if not asset:
            return None

        if payload.name is not None:
            asset.name = payload.name
        if payload.status is not None:
            asset.status = payload.status
        if payload.latitude is not None:
            asset.latitude = payload.latitude
        if payload.longitude is not None:
            asset.longitude = payload.longitude

        if payload.attributes is not None:
            # Re-validate schema on update will be handled by Methodology Engine
            asset.attributes = payload.attributes

        return await self.repository.update(asset)

    async def delete_asset(self, asset_id: UUID, organization_id: UUID) -> bool:
        asset = await self.repository.get_by_id(asset_id, organization_id)
        if not asset:
            return False
        await self.repository.delete(asset)
        return True
