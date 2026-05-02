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
from datetime import datetime, timezone
from sqlalchemy import String, Float, DateTime, ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Activity(Base):
    """
    Field activity submission model.
    
    Activity Types:
        - "cooking": Clean cooking activities (stove usage, fuel type)
        - "farming": Agricultural activities (planting, harvesting, soil management)
        - "energy": Energy usage monitoring (solar, biogas, grid)
        - "sustainability": Real estate sustainability activities
        - "other": Custom activity types
    
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
