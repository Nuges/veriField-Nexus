import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RegistryConfig(Base):
    __tablename__ = "registry_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    adapter_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # e.g., 'verra', 'gold_standard'
    base_url: Mapped[str] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    credentials: Mapped[dict] = mapped_column(
        JSONB, default=dict
    )  # Should be encrypted in real app
    mapping_rules_json: Mapped[dict] = mapped_column(
        JSONB, default=dict
    )  # Metadata for mapping internal schema to external API

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )


class RegistrySyncLog(Base):
    __tablename__ = "registry_sync_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    registry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("registry_configs.id", ondelete="CASCADE")
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )  # Loose coupling
    action: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'registerProject', 'issueCredits', 'retireCredits'
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # 'pending', 'success', 'failed'
    idempotency_key: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True
    )

    request_payload: Mapped[dict] = mapped_column(JSONB, nullable=True)
    response_payload: Mapped[dict] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=True,
    )

    registry = relationship("RegistryConfig")
