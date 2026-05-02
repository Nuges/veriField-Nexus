"""
=============================================================================
VeriField Nexus — Anomaly Flag Model
=============================================================================
Stores anomaly flags raised by the AI detection engine. Each flag
represents a specific type of suspicious behavior that needs review.
=============================================================================
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AnomalyFlag(Base):
    """
    Anomaly detection flag model.
    
    Flag Types:
        - "gps_spoofing": GPS coordinates appear fabricated
        - "image_duplicate": Image is too similar to a previous submission
        - "high_frequency": Submission rate exceeds normal patterns
        - "time_anomaly": Activity submitted at suspicious hours
        - "impossible_travel": GPS locations suggest impossible movement speed
        - "pattern_anomaly": ML model detected unusual behavior patterns
    
    Severity Levels:
        - "low": Minor concern, informational
        - "medium": Needs review, may affect trust score
        - "high": Serious concern, activity should be investigated
        - "critical": Likely fraudulent, immediate action needed
    """
    __tablename__ = "anomaly_flags"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    # --- Linked activity and user ---
    activity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("activities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # --- Flag Details ---
    flag_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False, default="medium"
    )

    # --- Resolution Status ---
    resolved: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    resolved_by: Mapped[str] = mapped_column(String(255), nullable=True)
    resolution_notes: Mapped[str] = mapped_column(Text, nullable=True)

    # --- Timestamp ---
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )

    # --- Relationships ---
    activity = relationship("Activity", back_populates="anomaly_flags")

    def __repr__(self) -> str:
        return (
            f"<AnomalyFlag(type={self.flag_type}, severity={self.severity}, "
            f"resolved={self.resolved})>"
        )
