from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_bus import EventBus
from app.domains.organizations.models import Organization
from app.domains.organizations.repository import OrganizationRepository
from app.domains.organizations.schemas import (OrganizationCreate,
                                               OrganizationUpdate)


class OrganizationService:
    def __init__(self, repository: OrganizationRepository):
        self.repository = repository

    async def get_org(self, org_id: UUID) -> Optional[Organization]:
        return await self.repository.get_by_id(org_id)

    async def list_orgs(self, skip: int = 0, limit: int = 100) -> List[Organization]:
        return await self.repository.list_all(skip=skip, limit=limit)

    async def create_org(
        self,
        payload: OrganizationCreate,
        creator_id: Optional[UUID] = None,
        db: Optional[AsyncSession] = None,
    ) -> Organization:
        org = Organization(
            **payload.model_dump(exclude={"licensed_methodologies"}),
            licensed_methodologies=getattr(payload, "licensed_methodologies", []),
            created_by=creator_id,
            status="ACTIVE",
        )
        if payload.plan == "ENTERPRISE":
            org.max_installations = 10000
            org.max_agents = 50
        elif payload.plan == "PROFESSIONAL":
            org.max_installations = 1000
            org.max_agents = 20

        created = await self.repository.create(org)

        if db:
            await EventBus.publish(
                stream_name="organization_events",
                event_type="OrgCreated",
                payload={
                    "id": str(created.id),
                    "name": created.name,
                    "org_type": created.org_type,
                },
                actor_id=str(creator_id) if creator_id else "system",
            )

        return created

    async def update_org(
        self,
        org_id: UUID,
        payload: OrganizationUpdate,
        actor_id: Optional[UUID] = None,
        db: Optional[AsyncSession] = None,
    ) -> Optional[Organization]:
        org = await self.repository.get_by_id(org_id)
        if not org:
            return None

        updates: Dict[str, Any] = {}
        if payload.name is not None:
            updates["name"] = payload.name
        if payload.status is not None:
            updates["status"] = payload.status
        if payload.org_type is not None:
            updates["org_type"] = payload.org_type
        if payload.metadata_context is not None:
            updates["metadata_context"] = payload.metadata_context
        if payload.plan is not None:
            updates["plan"] = payload.plan
            if payload.plan == "ENTERPRISE":
                updates["max_installations"] = 10000
                updates["max_agents"] = 50
            elif payload.plan == "PROFESSIONAL":
                updates["max_installations"] = 1000
                updates["max_agents"] = 20
        if getattr(payload, "licensed_methodologies", None) is not None:
            updates["licensed_methodologies"] = payload.licensed_methodologies

        if not updates:
            return org

        updated_org = await self.repository.update(org_id, updates, org.version)
        if not updated_org:
            raise ValueError(
                f"Organization {org_id} was modified by another transaction."
            )

        if db:
            await EventBus.publish(
                stream_name="organization_events",
                event_type="OrgUpdated",
                payload={"id": str(org_id), "updates": updates},
                actor_id=str(actor_id) if actor_id else "system",
            )

        return updated_org

    async def soft_delete_org(
        self,
        org_id: UUID,
        actor_id: Optional[UUID] = None,
        db: Optional[AsyncSession] = None,
    ) -> bool:
        success = await self.repository.soft_delete(org_id)
        if success and db:
            await EventBus.publish(
                stream_name="organization_events",
                event_type="OrgArchived",
                payload={"id": str(org_id)},
                actor_id=str(actor_id) if actor_id else "system",
            )
        return success
