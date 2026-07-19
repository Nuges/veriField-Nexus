import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .models.twin import DigitalTwin, DigitalTwinState
from app.domains.assets.models import Asset
from app.domains.hardware.models.device import Device

logger = logging.getLogger(__name__)

class DigitalTwinEngine:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_twin_for_asset(self, asset_id: uuid.UUID) -> DigitalTwin:
        """Automatically create a digital twin for an asset."""
        twin = DigitalTwin(
            asset_id=asset_id,
            twin_status="provisioned",
            state_vector={"health": 100.0, "alerts": []}
        )
        self.db.add(twin)
        await self.db.commit()
        await self.db.refresh(twin)
        return twin

    async def ingest_telemetry(self, device_id: uuid.UUID, payload: Dict[str, Any]) -> None:
        """Process live telemetry from a device and update the bound digital twin."""
        # Find twin bound to this device
        result = await self.db.execute(select(DigitalTwin).where(DigitalTwin.device_id == device_id))
        twin = result.scalars().first()
        
        if not twin:
            logger.warning(f"No Digital Twin bound to device {device_id}")
            return
            
        # Update state vector
        current_state = dict(twin.state_vector)
        current_state.update(payload)
        
        # Determine health impact from telemetry (simulation logic for engine thresholds)
        if payload.get("temperature", 0) > 80:
            current_state["alerts"].append("High Temperature Warning")
            current_state["health"] = max(0, current_state.get("health", 100) - 10)
            
        twin.state_vector = current_state
        twin.last_sync_at = datetime.now(timezone.utc)
        
        # Save historical state snapshot
        state_snapshot = DigitalTwinState(
            digital_twin_id=twin.id,
            timestamp=datetime.now(timezone.utc),
            state_data=current_state
        )
        self.db.add(state_snapshot)
        await self.db.commit()

    async def get_twin_state(self, asset_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """Retrieve the current state of a digital twin by asset ID."""
        result = await self.db.execute(select(DigitalTwin).where(DigitalTwin.asset_id == asset_id))
        twin = result.scalars().first()
        if not twin:
            return None
            
        return {
            "twin_id": str(twin.id),
            "status": twin.twin_status,
            "last_sync": twin.last_sync_at.isoformat() if twin.last_sync_at else None,
            "state": twin.state_vector
        }
