import uuid

from sqlalchemy import Boolean, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SensorMetadata(Base):
    """
    Pure metadata defining a sensor's type, unit, and constraints.
    """

    __tablename__ = "sensor_metadata"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    sensor_type: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False
    )  # 'temperature', 'flow', 'gps', 'energy'
    unit_of_measurement: Mapped[str] = mapped_column(String(20), nullable=False)
    data_type: Mapped[str] = mapped_column(String(20), default="float")
    validation_rules: Mapped[dict] = mapped_column(
        JSONB, default=dict
    )  # min, max, delta constraints


class SensorDefinition(Base):
    """
    An instance of a sensor mapped to a specific Device.
    """

    __tablename__ = "sensor_definitions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), index=True
    )
    metadata_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sensor_metadata.id"), index=True
    )

    local_identifier: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g. Modbus register address, or MQTT sub-topic
    calibration_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    device = relationship("Device")
    sensor_meta = relationship("SensorMetadata")
