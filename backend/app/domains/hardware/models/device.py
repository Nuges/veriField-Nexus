import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Device(Base):
    """
    Universal Base Model for all physical hardware components.
    """

    __tablename__ = "devices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    mac_address: Mapped[str] = mapped_column(
        String(50), nullable=True, unique=True, index=True
    )
    serial_number: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    manufacturer: Mapped[str] = mapped_column(String(100), nullable=True)
    model: Mapped[str] = mapped_column(String(100), nullable=True)
    device_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'edge_cabinet', 'embedded_device', 'sensor'

    firmware_version: Mapped[str] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="Inventory", nullable=False) # Inventory, Commission, Provision, Assign, Calibrate, Activate, Monitor, Maintenance, Retire

    # Cryptography & Provisioning
    public_key: Mapped[str] = mapped_column(String, nullable=True)
    provision_token: Mapped[str] = mapped_column(String(255), nullable=True)
    certificate: Mapped[str] = mapped_column(String, nullable=True)

    # Health & Telemetry State
    heartbeat_interval: Mapped[int] = mapped_column(nullable=True, default=60) # seconds
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    health_score: Mapped[float] = mapped_column(nullable=False, default=100.0)
    
    battery_level: Mapped[float] = mapped_column(nullable=True)
    signal_strength: Mapped[float] = mapped_column(nullable=True)
    
    # Polymorphic inheritance properties
    capabilities: Mapped[dict] = mapped_column(JSONB, default=dict)
    event_history: Mapped[list] = mapped_column(JSONB, default=list)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )

    __mapper_args__ = {
        "polymorphic_on": "device_type",
        "polymorphic_identity": "device",
    }


class EdgeCabinet(Device):
    """
    Fixed Universal Enclosure (Modbus, Power, UPS).
    """

    __mapper_args__ = {"polymorphic_identity": "edge_cabinet"}


class EmbeddedDevice(Device):
    """
    Mobile/Portable Universal IoT unit.
    """

    __mapper_args__ = {"polymorphic_identity": "embedded_device"}


class Gateway(Device):
    """
    Data collection and forwarding hub.
    """

    __mapper_args__ = {"polymorphic_identity": "gateway"}
