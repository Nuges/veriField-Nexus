"""
=============================================================================
VeriField Nexus — Trust Log Model
=============================================================================
Stores the detailed breakdown of trust score calculations for each
activity. This provides an audit trail and enables score debugging.
=============================================================================
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Float, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TrustLog(Base):
    """
    Trust score calculation log.
    
    Each activity gets one trust log entry containing:
    - Individual component scores (GPS, image, frequency)
    - Final composite score
    - Any flags raised during calculation
    
    Score Components:
        - gps_score (0-30): How consistent the GPS data is
        - image_score (0-35): How unique the submitted image is
        - frequency_score (0-35): How reasonable the submission pattern is
        - final_score (0-100): Weighted sum of all components
    """
    __tablename__ = "trust_logs"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    # --- Linked activity ---
    activity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("activities.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # One-to-one relationship
        index=True,
    )

    # --- Individual Score Components ---
    gps_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    image_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    frequency_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # --- Final Composite Score ---
    final_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # --- Flags raised during calculation ---
    # e.g., {"gps_too_far": true, "duplicate_image": false, "high_frequency": true}
    flags: Mapped[dict] = mapped_column(JSONB, nullable=True, default=dict)

    # --- Timestamp ---
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )

    # --- Relationships ---
    activity = relationship("Activity", back_populates="trust_log")

    def __repr__(self) -> str:
        return (
            f"<TrustLog(activity={self.activity_id}, "
            f"score={self.final_score}, flags={self.flags})>"
        )
