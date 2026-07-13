import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.domains.digital_twins.models.twin import DigitalTwin, DigitalTwinState
from app.domains.iiot.models.telemetry import TelemetryPayload, TelemetryStream


class SyncService:
    """
    Synchronizes Digital Twin states with underlying Telemetry Streams.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def sync_twin_state(self, twin_id: uuid.UUID) -> Optional[DigitalTwin]:
        """
        Recalculates the real-time aggregated state_vector of a Digital Twin.
        """
        result = await self.db.execute(select(DigitalTwin).filter_by(id=twin_id))
        twin = result.scalar_one_or_none()
        if not twin:
            return None

        # Get all telemetry streams for the device attached to this twin
        if not twin.device_id:
            return twin

        streams_res = await self.db.execute(
            select(TelemetryStream).filter_by(device_id=twin.device_id)
        )
        streams = streams_res.scalars().all()

        aggregated_state = {}
        for stream in streams:
            # Get latest payload
            payload_res = await self.db.execute(
                select(TelemetryPayload)
                .filter_by(stream_id=stream.id)
                .order_by(TelemetryPayload.timestamp.desc())
                .limit(1)
            )
            latest_payload = payload_res.scalar_one_or_none()
            if latest_payload:
                sensor_key = str(stream.sensor_id)
                aggregated_state[sensor_key] = {
                    "last_value": latest_payload.normalized_value,
                    "last_timestamp": latest_payload.timestamp.isoformat(),
                    "raw": latest_payload.raw_payload,
                }

        # Update twin state vector
        twin.state_vector = aggregated_state
        twin.last_sync_at = datetime.now(timezone.utc)

        # Take a snapshot
        snapshot = DigitalTwinState(
            digital_twin_id=twin.id,
            timestamp=datetime.now(timezone.utc),
            state_data=aggregated_state,
        )
        self.db.add(snapshot)

        await self.db.commit()
        return twin

    async def record_telemetry(
        self,
        stream_id: uuid.UUID,
        raw_payload: dict,
        normalized_value: float,
        timestamp: datetime,
    ) -> TelemetryPayload:
        """
        Records a new telemetry event and triggers a twin sync.
        """
        payload = TelemetryPayload(
            stream_id=stream_id,
            raw_payload=raw_payload,
            normalized_value=normalized_value,
            timestamp=timestamp,
        )
        self.db.add(payload)
        await self.db.flush()

        # Find the associated digital twin
        stream_res = await self.db.execute(
            select(TelemetryStream).filter_by(id=stream_id)
        )
        stream = stream_res.scalar_one_or_none()
        if stream and stream.device_id:
            twin_res = await self.db.execute(
                select(DigitalTwin).filter_by(device_id=stream.device_id)
            )
            twin = twin_res.scalar_one_or_none()
            if twin:
                await self.sync_twin_state(twin.id)

        await self.db.commit()
        return payload
