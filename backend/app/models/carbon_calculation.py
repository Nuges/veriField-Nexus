import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Float, DateTime, text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CarbonCalculation(Base):
    """
    Immutable ledger of generated carbon credits.
    Stores the exact formula, inputs, and final tCO2e output for auditors.
    """
    __tablename__ = "carbon_calculations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), index=True, nullable=False
    )
    activity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("activities.id"), index=True, nullable=False
    )
    
    methodology_used: Mapped[str] = mapped_column(String, nullable=False)
    tco2e_generated: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Traceability for auditors
    calculation_log: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String, default="calculated") # calculated, pending_issuance, issued
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        nullable=False,
    )

    activity = relationship("Activity", backref="carbon_calculations")
