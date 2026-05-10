import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Float, DateTime, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Project(Base):
    """
    Groups activities/assets under a specific methodology (e.g. Verra VM0006).
    Stores baseline parameters needed for the deterministic calculations.
    """
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    methodology_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    registry_id: Mapped[str] = mapped_column(String, nullable=True)
    
    # Baseline configuration (e.g., fuel consumption per household)
    baseline_parameters: Mapped[dict] = mapped_column(JSONB, default=dict)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        nullable=False,
    )

    carbon_calculations = relationship("CarbonCalculation", backref="project")
