"""
=============================================================================
VeriField Nexus — Activity Model
=============================================================================
Represents a single field activity submission. Each activity includes:
- What was done (activity type + structured data)
- Where it happened (GPS coordinates)
- When it happened (timestamps)
- Proof (photo capture with image hash)
- Verification (trust score from Trust Engine)
=============================================================================
"""

import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, Float, DateTime, ForeignKey, Text, Boolean, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Activity(Base):
    """
    Field activity submission model (Cookstove Installation System).
    
    Activity Types:
        - "CLEAN_COOKING": Clean cooking stove installation & usage logging
    
    Status:
        - "pending": Submitted, awaiting trust score calculation
        - "verified": Trust score >= 80 (high confidence)
        - "review": Trust score 50-79 (needs human review)
        - "flagged": Trust score < 50 or anomaly detected
        - "rejected": Manually rejected by admin
    """
    __tablename__ = "activities"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    # --- Who submitted ---
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # --- Optional property association ---
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # --- What was done ---
    activity_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    # Flexible JSON data for activity-specific fields
    # e.g., {"fuel_type": "LPG", "duration_minutes": 45, "meals_cooked": 3}
    activity_data: Mapped[dict] = mapped_column(
        JSONB, nullable=True, default=dict
    )
    description: Mapped[str] = mapped_column(Text, nullable=True)

    # --- Photo proof ---
    image_url: Mapped[str] = mapped_column(String(500), nullable=True)
    # Perceptual hash for duplicate detection
    image_hash: Mapped[str] = mapped_column(String(64), nullable=True, index=True)

    # --- Where it happened ---
    latitude: Mapped[float] = mapped_column(Float, nullable=True)
    longitude: Mapped[float] = mapped_column(Float, nullable=True)
    gps_accuracy: Mapped[float] = mapped_column(Float, nullable=True)  # meters

    # --- Smart GPS Validation ---
    environment_type: Mapped[str] = mapped_column(
        String(10), nullable=True, default=None  # "URBAN" or "RURAL"
    )
    radius_used_m: Mapped[float] = mapped_column(
        Float, nullable=True, default=None  # Dynamic radius used for duplicate check
    )
    duplicate_flag: Mapped[bool] = mapped_column(
        nullable=True, default=False  # True if nearby duplicate detected
    )
    override_reason: Mapped[str] = mapped_column(
        Text, nullable=True, default=None  # Agent reason for overriding duplicate warning
    )

    # --- When it happened ---
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )

    # --- Trust & Verification ---
    trust_score: Mapped[float] = mapped_column(
        Float, nullable=True, default=None  # Calculated async by Trust Engine
    )
    trust_flags: Mapped[dict] = mapped_column(
        JSONB, nullable=True, default=dict
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )

    # --- Sync metadata (for offline-first support) ---
    # Client-generated UUID to prevent duplicate submissions
    client_id: Mapped[str] = mapped_column(
        String(36), nullable=True, unique=True, index=True
    )

    # Record creation timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )

    # --- Carbon C-Sink Module Mappings ---
    biochar_batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("biochar_batches.id", ondelete="SET NULL"),
        nullable=True,
    )
    c_sink_unit_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("c_sink_units.id", ondelete="SET NULL"),
        nullable=True,
    )


    # --- Relationships ---
    user = relationship("User", back_populates="activities")
    property = relationship("Property", back_populates="activities")
    trust_log = relationship(
        "TrustLog", back_populates="activity", uselist=False, lazy="selectin"
    )
    anomaly_flags = relationship(
        "AnomalyFlag", back_populates="activity", lazy="selectin"
    )

    def __repr__(self) -> str:
        return (
            f"<Activity(id={self.id}, type={self.activity_type}, "
            f"trust={self.trust_score}, status={self.status})>"
        )

