import logging

from app.core.events.base import BaseEvent
from app.core.events.publisher import publish_event

logger = logging.getLogger("verifield.activities.events")


async def publish_activity_created(
    activity_id: str, organization_id: str, payload_data: dict
):
    event = BaseEvent(
        event_type="activity.created",
        organization_id=organization_id,
        payload={
            "activity_id": activity_id,
            "organization_id": organization_id,
            **payload_data,
        },
    )
    await publish_event(event)


async def publish_activity_updated(
    activity_id: str, organization_id: str, payload_data: dict
):
    event = BaseEvent(
        event_type="activity.updated",
        organization_id=organization_id,
        payload={
            "activity_id": activity_id,
            "organization_id": organization_id,
            **payload_data,
        },
    )
    await publish_event(event)
