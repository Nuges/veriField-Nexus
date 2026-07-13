import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProtocolDefinition(Base):
    """
    Universal protocol parsing schema definition.
    Allows dynamic deserialization of payloads (e.g. Hex, Protobuf, JSON) based on configuration.
    """

    __tablename__ = "protocol_definitions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )  # e.g. 'EDGE_V1', 'MODBUS_RTU', 'MQTT_JSON'
    version: Mapped[str] = mapped_column(String(20), nullable=False)

    # JSON schema defining the expected input structure or bytes mapping
    parser_schema: Mapped[dict] = mapped_column(JSONB, default=dict)

    # AST or DSL for transforming the raw payload into a standard universal Event
    transformation_rules: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )
