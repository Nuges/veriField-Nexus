import logging

from app.core.events.base import BaseEvent
from app.core.events.publisher import publish_event

logger = logging.getLogger("verifield.assets.events")


async def publish_asset_created(asset_id: str, organization_id: str, project_id: str):
    event = BaseEvent(
        event_type="asset.created",
        organization_id=organization_id,
        payload={"asset_id": asset_id, "project_id": project_id},
    )
    await publish_event(event)
