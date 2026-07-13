import logging

from app.core.events.base import BaseEvent
from app.core.events.publisher import publish_event

logger = logging.getLogger("verifield.workspaces.events")


async def publish_workspace_created(workspace_id: str, organization_id: str):
    event = BaseEvent(
        event_type="workspace.created",
        organization_id=organization_id,
        payload={"workspace_id": workspace_id},
    )
    await publish_event(event)
