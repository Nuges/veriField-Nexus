from typing import List, Optional
from uuid import UUID

from app.domains.workspaces.events import publish_workspace_created
from app.domains.workspaces.models import Property
from app.domains.workspaces.repository import PropertyRepository
from app.domains.workspaces.schemas import PropertyCreate, PropertyUpdate


class PropertyService:
    def __init__(self, repository: PropertyRepository):
        self.repository = repository

    async def get_property(
        self, prop_id: UUID, organization_id: Optional[UUID] = None
    ) -> Optional[Property]:
        return await self.repository.get_by_id(prop_id, organization_id)

    async def list_properties(self, organization_id: UUID) -> List[Property]:
        return await self.repository.list_by_organization(organization_id)

    async def create_property(
        self, payload: PropertyCreate, owner_id: UUID, organization_id: UUID
    ) -> Property:
        prop = Property(
            owner_id=owner_id,
            organization_id=organization_id,
            name=payload.name,
            address=payload.address,
            property_type=payload.property_type,
            latitude=payload.latitude,
            longitude=payload.longitude,
            sustainability_metrics={},
        )
        created = await self.repository.create(prop)
        await publish_workspace_created(str(created.id), str(organization_id))
        return created

    async def update_property(
        self, prop_id: UUID, payload: PropertyUpdate, organization_id: UUID
    ) -> Optional[Property]:
        prop = await self.repository.get_by_id(prop_id, organization_id)
        if not prop:
            return None

        if payload.name is not None:
            prop.name = payload.name
        if payload.address is not None:
            prop.address = payload.address
        if payload.property_type is not None:
            prop.property_type = payload.property_type
        if payload.latitude is not None:
            prop.latitude = payload.latitude
        if payload.longitude is not None:
            prop.longitude = payload.longitude

        return await self.repository.update(prop)

    async def delete_property(self, prop_id: UUID, organization_id: UUID) -> bool:
        prop = await self.repository.get_by_id(prop_id, organization_id)
        if not prop:
            return False
        await self.repository.delete(prop)
        return True
