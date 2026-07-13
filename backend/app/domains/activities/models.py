import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Activity(Base):
    """
    Field activity submission model.
    Structured with composite primary key (id, organization_id, created_at) for monthly partitioning.
    """

    __tablename__ = "activities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
        index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    activity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    activity_data: Mapped[dict] = mapped_column(JSONB, nullable=True, default=dict)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    image_url: Mapped[str] = mapped_column(String(500), nullable=True)
    image_hash: Mapped[str] = mapped_column(String(64), nullable=True, index=True)

    latitude: Mapped[float] = mapped_column(Float, nullable=True)
    longitude: Mapped[float] = mapped_column(Float, nullable=True)
    gps_accuracy: Mapped[float] = mapped_column(Float, nullable=True)

    environment_type: Mapped[str] = mapped_column(
        String(10), nullable=True, default=None
    )
    radius_used_m: Mapped[float] = mapped_column(Float, nullable=True, default=None)
    duplicate_flag: Mapped[bool] = mapped_column(nullable=True, default=False)
    override_reason: Mapped[str] = mapped_column(Text, nullable=True, default=None)

    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )

    trust_score: Mapped[float] = mapped_column(Float, nullable=True, default=None)
    trust_flags: Mapped[dict] = mapped_column(JSONB, nullable=True, default=dict)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )

    client_id: Mapped[str] = mapped_column(String(36), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        primary_key=True,
    )

    validation_status: Mapped[Optional[str]] = mapped_column(
        String(20), default="pending", nullable=True
    )
    validation_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)

    # Generic evidence JSON payload
    evidence_payload: Mapped[dict] = mapped_column(JSONB, nullable=True, default=dict)

    # Relationships
    user = relationship("User", back_populates="activities", lazy="selectin")
    property = relationship("Property", back_populates="activities")
    asset = relationship("Asset", back_populates="activities")
    # trust_log = relationship(
    #     "TrustLog",
    #     back_populates="activity",
    #     uselist=False,
    #     lazy="selectin",
    #     primaryjoin="Activity.id == foreign(TrustLog.activity_id)",
    # )
    # anomaly_flags = relationship(
    #     "AnomalyFlag", back_populates="activity", lazy="selectin", primaryjoin="Activity.id == foreign(AnomalyFlag.activity_id)"
    # )

    @__builtins__["property"]
    def agent_name(self) -> Optional[str]:
        return self.user.full_name if self.user else None

    def __repr__(self) -> str:
        return (
            f"<Activity(id={self.id}, type={self.activity_type}, "
            f"trust={self.trust_score}, status={self.status})>"
        )
