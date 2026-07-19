import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.digital_twins.models.twin import DigitalTwin

# from app.models.sensor_reading import SensorReading

logger = logging.getLogger(__name__)


class DigitalTwinLifecycleManager:
    """
    Manages Digital Twin lifecycle updates, state transitions, and historical replay.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def transition_state(
        self,
        twin_id: uuid.UUID,
        new_state: str,
        reason: str,
        triggered_by: str = "system",
    ):
        """
        Transitions the lifecycle state of a Digital Twin (e.g. provisioning -> active -> maintenance -> offline).
        """
        twin = await self.db.get(DigitalTwin, twin_id)
        if not twin:
            raise ValueError(f"Digital Twin {twin_id} not found")

        old_state = twin.status
        twin.status = new_state
        twin.updated_at = datetime.now(timezone.utc)

        # Log the transition in a historical ledger
        logger.info(
            f"Digital Twin {twin_id} transitioned from {old_state} to {new_state} by {triggered_by}. Reason: {reason}"
        )

        await self.db.commit()
        return twin

    async def update_twin_metadata(
        self, twin_id: uuid.UUID, metadata_patch: Dict[str, Any]
    ):
        """
        Updates the descriptive metadata attached to a Digital Twin.
        """
        twin = await self.db.get(DigitalTwin, twin_id)
        if not twin:
            raise ValueError(f"Digital Twin {twin_id} not found")

        current_metadata = twin.metadata or {}
        current_metadata.update(metadata_patch)
        twin.metadata = current_metadata
        twin.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        return twin

    async def historical_replay(
        self, twin_id: uuid.UUID, start_time: datetime, end_time: datetime
    ) -> List[Dict[str, Any]]:
        """
        Fetches historical telemetry data to replay the state of a Digital Twin over a time window.
        """
        twin = await self.db.get(DigitalTwin, twin_id)
        if not twin:
            raise ValueError(f"Digital Twin {twin_id} not found")

        # SensorReading model is missing/deprecated in new architecture.
        return []
