"""
=============================================================================
VeriField Nexus — NDVI Record Model
=============================================================================
Stores monthly NDVI (Normalized Difference Vegetation Index) scores
per asset for satellite-based vegetation monitoring.
=============================================================================
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Float, DateTime, text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class NdviRecord(Base):
    """Monthly NDVI observation for an asset/property."""
    __tablename__ = "ndvi_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id"), index=True, nullable=False
    )
    ndvi_score: Mapped[float] = mapped_column(Float, nullable=False)
    trend: Mapped[str] = mapped_column(
        String(20), nullable=False, default="stable"
    )  # 'increasing', 'stable', 'decreasing'
    observation_date: Mapped[str] = mapped_column(
        String(10), nullable=False  # YYYY-MM format
    )
    source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="sentinel2"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        nullable=False,
    )

    property = relationship("Property", backref="ndvi_records")
