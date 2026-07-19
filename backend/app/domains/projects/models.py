import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Float, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Project(Base):
    """
    Project Configuration Model (Layer 1 of 3-Layer MRV)
    """

    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    project_code: Mapped[str] = mapped_column(
        String(20),
        nullable=True,
        unique=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(String, nullable=False)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    jurisdiction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jurisdictions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    programme_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("climate_programmes.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    methodology_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("methodologies.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    sector_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("methodology_families.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    methodology_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("methodology_versions.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    country: Mapped[str] = mapped_column(
        String(100),
        nullable=True,
    )
    registry_id: Mapped[str] = mapped_column(String, nullable=True)

    baseline_source: Mapped[str] = mapped_column(
        String(30),
        nullable=True,
        default="diesel_generator",
    )

    diesel_emission_factor: Mapped[float] = mapped_column(
        Float,
        nullable=True,
        default=2.68,
    )
    grid_emission_factor: Mapped[float] = mapped_column(
        Float,
        nullable=True,
        default=0.7,
    )

    crediting_start: Mapped[date] = mapped_column(
        Date,
        nullable=True,
    )
    crediting_end: Mapped[date] = mapped_column(
        Date,
        nullable=True,
    )

    baseline_parameters: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        nullable=True,
    )

    # Relationships
    carbon_calculations = relationship("CarbonCalculation", backref="project")
    jurisdiction = relationship("Jurisdiction", back_populates="projects")
    organization = relationship("Organization", backref="projects")

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name={self.name}, code={self.project_code})>"


class CarbonCalculation(Base):
    """
    Authoritative Carbon Calculation Ledger.
    """

    __tablename__ = "carbon_calculations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    activity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("activities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    methodology_used: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    tco2e_generated: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    calculation_log: Mapped[dict] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=True, default="calculated")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )

    def __repr__(self) -> str:
        return f"<CarbonCalculation(id={self.id}, project_id={self.project_id}, tco2e={self.tco2e_generated})>"
