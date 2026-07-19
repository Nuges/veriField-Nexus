from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from app.domains.activities.events import publish_activity_created
from app.domains.activities.models import Activity
from app.domains.activities.repository import ActivityRepository
from app.domains.activities.schemas import ActivityCreate, ActivityUpdate


class ActivityService:
    def __init__(self, repository: ActivityRepository):
        self.repository = repository

    async def get_activity(
        self, activity_id: UUID, organization_id: Optional[UUID] = None
    ) -> Optional[Activity]:
        return await self.repository.get_by_id(activity_id, organization_id)

    async def get_activity_by_client(
        self, client_id: str, organization_id: Optional[UUID] = None
    ) -> Optional[Activity]:
        return await self.repository.get_by_client_id(client_id, organization_id)

    async def list_activities(
        self, organization_id: UUID, status: Optional[str] = None
    ) -> List[Activity]:
        return await self.repository.list_by_organization(organization_id, status)

    async def create_activity(
        self, payload: ActivityCreate, user_id: UUID, organization_id: UUID
    ) -> Activity:

        activity = Activity(
            organization_id=organization_id,
            user_id=user_id,
            property_id=payload.property_id,
            asset_id=payload.asset_id,
            activity_type=payload.activity_type,
            activity_data=payload.activity_data or {},
            description=payload.description,
            image_url=payload.image_url,
            image_hash=payload.image_hash,
            latitude=payload.latitude,
            longitude=payload.longitude,
            gps_accuracy=payload.gps_accuracy,
            captured_at=payload.captured_at,
            status="pending",
            client_id=payload.client_id,
            override_reason=payload.override_reason,
            evidence_payload=payload.evidence_payload,
            validation_status="pending",
            is_locked=False,
            created_at=datetime.now(timezone.utc),
        )

        created = await self.repository.create(activity)

        # Publish event for async background processing
        payload_dict = {
            "activity_type": created.activity_type,
            "captured_at": (
                created.captured_at.isoformat() if created.captured_at else None
            ),
            "latitude": created.latitude,
            "longitude": created.longitude,
            "image_url": created.image_url,
            "image_hash": created.image_hash,
            "client_id": created.client_id,
            "data": created.activity_data,
        }
        await publish_activity_created(
            str(created.id), str(organization_id), payload_dict
        )

        return created

    async def update_activity_status(
        self, activity_id: UUID, payload: ActivityUpdate, organization_id: UUID
    ) -> Optional[Activity]:
        activity = await self.repository.get_by_id(activity_id, organization_id)
        if not activity:
            return None

        if payload.status is not None:
            activity.status = payload.status
        if payload.trust_score is not None:
            activity.trust_score = payload.trust_score
        if payload.validation_status is not None:
            activity.validation_status = payload.validation_status
        if payload.override_reason is not None:
            activity.override_reason = payload.override_reason

        return await self.repository.update(activity)
