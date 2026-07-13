import logging

from app.core.events.base import BaseEvent
from app.core.events.publisher import publish_event

logger = logging.getLogger("verifield.projects.events")


async def publish_project_created(
    project_id: str, organization_id: str, methodology_id: str
):
    event = BaseEvent(
        event_type="project.created",
        organization_id=organization_id,
        payload={"project_id": project_id, "methodology_id": methodology_id},
    )
    await publish_event(event)


async def publish_project_approved(project_id: str, organization_id: str):
    event = BaseEvent(
        event_type="project.approved",
        organization_id=organization_id,
        payload={"project_id": project_id},
    )
    await publish_event(event)
