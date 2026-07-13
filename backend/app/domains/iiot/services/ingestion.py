import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.digital_twins.models.twin import DigitalTwin
from app.domains.hardware.models.sensor import SensorDefinition
from app.domains.iiot.models.gateway import IIoTEdgeSyncLog
from app.domains.iiot.models.telemetry import TelemetryPayload, TelemetryStream

logger = logging.getLogger(__name__)


class IIoTIngestionEngine:
    """
    Protocol-agnostic Edge Telemetry Ingestion Engine.
    Maps arbitrary payloads (MQTT, Modbus, OPC-UA) to the Digital Twin's telemetry stream
    based on metadata configurations.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def ingest_payload(
        self, device_id: uuid.UUID, protocol: str, payload: List[Dict[str, Any]]
    ) -> IIoTEdgeSyncLog:
        """
        Ingests an array of edge telemetry points.
        Format expected from Edge Gateway:
        [
            {"local_identifier": "40001", "value": 23.5, "timestamp": "2026-07-12T10:00:00Z"},
            {"local_identifier": "mqtt_topic/temp", "value": 24.1}
        ]
        """
        # Create sync log
        sync_log = IIoTEdgeSyncLog(
            device_id=device_id,
            protocol=protocol,
            payload_size_bytes=len(str(payload)),
            status="processing",
        )
        self.db.add(sync_log)
        await self.db.flush()

        try:
            # 1. Resolve Digital Twin
            twin_query = await self.db.execute(
                select(DigitalTwin).where(DigitalTwin.device_id == device_id)
            )
            twin = twin_query.scalar_one_or_none()
            if not twin:
                raise ValueError(f"No Digital Twin mapped to Device {device_id}")

            # 2. Resolve Sensor Definitions for this device
            sensor_query = await self.db.execute(
                select(SensorDefinition).where(
                    SensorDefinition.device_id == device_id,
                    SensorDefinition.is_active,
                )
            )
            sensors = {s.local_identifier: s for s in sensor_query.scalars().all()}

            # 3. Process Payload
            processed_count = 0
            for point in payload:
                local_id = point.get("local_identifier")
                val = point.get("value")
                ts_str = point.get("timestamp")

                if local_id not in sensors:
                    logger.warning(
                        f"Unknown local_identifier {local_id} for device {device_id}"
                    )
                    continue

                sensor_def = sensors[local_id]

                # Timestamp resolution
                if ts_str:
                    try:
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    except ValueError:
                        ts = datetime.now(timezone.utc)
                else:
                    ts = datetime.now(timezone.utc)

                # Construct Timeseries Telemetry Record
                # We need a stream id, assuming we can get or create one
                stream_query = await self.db.execute(
                    select(TelemetryStream).where(
                        TelemetryStream.device_id == device_id,
                        TelemetryStream.sensor_id == sensor_def.id,
                    )
                )
                stream = stream_query.scalar_one_or_none()
                if not stream:
                    stream = TelemetryStream(
                        device_id=device_id, sensor_id=sensor_def.id
                    )
                    self.db.add(stream)
                    await self.db.flush()

                reading = TelemetryPayload(
                    stream_id=stream.id,
                    normalized_value=float(val),
                    timestamp=ts,
                    raw_payload=point,
                )
                self.db.add(reading)
                processed_count += 1

            # Update Twin State Vector (Materialized View of current state)
            if payload:
                latest_state = twin.state_vector or {}
                for point in payload:
                    local_id = point.get("local_identifier")
                    if local_id in sensors:
                        latest_state[local_id] = {
                            "value": point.get("value"),
                            "timestamp": point.get("timestamp")
                            or datetime.now(timezone.utc).isoformat(),
                        }
                twin.state_vector = latest_state
                twin.last_sync_at = datetime.now(timezone.utc)

            # Mark Success
            sync_log.status = "success"
            sync_log.records_processed = processed_count
            await self.db.commit()

            return sync_log

        except Exception as e:
            await self.db.rollback()
            sync_log.status = "failed"
            sync_log.error_message = str(e)
            self.db.add(sync_log)
            await self.db.commit()
            raise e
