import logging

from app.core.events.base import BaseEvent
from app.core.events.publisher import publish_event

logger = logging.getLogger("verifield.orgs.events")


async def publish_org_created(org_id: str, name: str):
    event = BaseEvent(
        event_type="organization.created",
        organization_id=org_id,
        payload={"org_id": org_id, "name": name},
    )
    await publish_event(event)
