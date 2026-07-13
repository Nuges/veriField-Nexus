import logging

from app.core.events.base import BaseEvent
from app.core.events.publisher import publish_event

logger = logging.getLogger("verifield.auth.events")


async def publish_user_created(user_id: str, email: str, organization_id: str):
    event = BaseEvent(
        event_type="user.created",
        organization_id=organization_id,
        payload={"user_id": user_id, "email": email},
    )
    await publish_event(event)
