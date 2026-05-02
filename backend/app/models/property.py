"""
=============================================================================
VeriField Nexus — Property Model
=============================================================================
Represents a physical property (building, farm, facility) that can
have activities assigned to it. Tracks sustainability metrics
for real estate module integration.
=============================================================================
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Float, DateTime, ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Property(Base):
    """
    Property model for the Real Estate Sustainability module.
    
    Property Types:
        - "residential": Homes, apartments
        - "commercial": Offices, retail spaces
        - "agricultural": Farms, plantations
        - "industrial": Factories, warehouses
        - "mixed": Mixed-use properties
    
    Sustainability Metrics (stored in JSONB):
        {
            "carbon_offset_kg": 150.5,
            "energy_saved_kwh": 2400,
            "clean_cooking_sessions": 89,
            "sustainability_score": 78.5,
            "last_calculated": "2024-01-15T10:30:00Z"
        }
    """
    __tablename__ = "properties"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    # --- Owner ---
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # --- Property Details ---
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=True)
    property_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="residential"
    )

    # --- Location ---
    latitude: Mapped[float] = mapped_column(Float, nullable=True)
    longitude: Mapped[float] = mapped_column(Float, nullable=True)

    # --- Sustainability Metrics (calculated from activities) ---
    sustainability_metrics: Mapped[dict] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
    )

    # --- Timestamps ---
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

    # --- Relationships ---
    owner = relationship("User", back_populates="properties")
    activities = relationship("Activity", back_populates="property", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Property(id={self.id}, name={self.name}, type={self.property_type})>"
