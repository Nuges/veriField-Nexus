import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DigitalTwin(Base):
    """
    The Digital Twin anchors the physical Asset to the logical Hardware and Telemetry streams.
    No asset exists without its Digital Twin.
    """

    __tablename__ = "digital_twins"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
        index=True,
    )

    twin_status: Mapped[str] = mapped_column(
        String(50), default="provisioned"
    )  # 'provisioned', 'online', 'offline', 'maintenance'
    state_vector: Mapped[dict] = mapped_column(
        JSONB, default=dict
    )  # Real-time aggregated view

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )
    last_sync_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    asset = relationship("Asset")
    device = relationship("Device")


class DigitalTwinState(Base):
    """
    Time-series snapshot of a Digital Twin's state.
    """

    __tablename__ = "digital_twin_states"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    digital_twin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("digital_twins.id", ondelete="CASCADE"),
        index=True,
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    state_data: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )

    digital_twin = relationship("DigitalTwin")
