import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import Date, DateTime, Float, ForeignKey, String, UniqueConstraint, event, text
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
    Harmonized schema supporting modern CIOS MRV engine and backward-compatible operations.
    """

    __tablename__ = "carbon_calculations"
    __table_args__ = (
        UniqueConstraint("project_id", "activity_id", name="uq_carbon_calc_project_activity"),
    )

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
    activity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("activities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    methodology_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("methodology_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    methodology_used: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    # Carbon Yield / Volume Metrics (synchronized)
    tco2e_yield: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        default=0.0,
        server_default=text("0.0"),
    )
    tco2e_generated: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        default=0.0,
        server_default=text("0.0"),
    )
    uncertainty: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        default=0.05,
    )

    # Detailed Computation & Audit Trails (synchronized)
    execution_inputs: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
    )
    execution_outputs: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
    )
    audit_replay: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
    )
    registry_references: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
    )
    calculation_log: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
    )

    # Lifecycle State
    status: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        default="calculated",
        server_default=text("'calculated'"),
    )

    # Timestamps (synchronized)
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )

    def __init__(self, **kwargs):
        # Synchronize yield / generated values
        if "tco2e_yield" in kwargs and "tco2e_generated" not in kwargs:
            kwargs["tco2e_generated"] = kwargs["tco2e_yield"]
        elif "tco2e_generated" in kwargs and "tco2e_yield" not in kwargs:
            kwargs["tco2e_yield"] = kwargs["tco2e_generated"]

        # Synchronize execution logs / outputs
        if "calculation_log" in kwargs and "execution_outputs" not in kwargs:
            kwargs["execution_outputs"] = kwargs["calculation_log"]
        elif "execution_outputs" in kwargs and "calculation_log" not in kwargs:
            kwargs["calculation_log"] = kwargs["execution_outputs"]
        if "calculation_log" in kwargs and "execution_inputs" not in kwargs:
            kwargs["execution_inputs"] = kwargs["calculation_log"]

        # Synchronize executed_at / created_at
        if "executed_at" in kwargs and "created_at" not in kwargs:
            kwargs["created_at"] = kwargs["executed_at"]
        elif "created_at" in kwargs and "executed_at" not in kwargs:
            kwargs["executed_at"] = kwargs["created_at"]

        # Synchronize methodology identifiers
        if "methodology_used" in kwargs and "methodology_version_id" not in kwargs:
            kwargs["methodology_version_id"] = kwargs["methodology_used"]
        elif "methodology_version_id" in kwargs and "methodology_used" not in kwargs:
            kwargs["methodology_used"] = kwargs["methodology_version_id"]

        super().__init__(**kwargs)

    def __repr__(self) -> str:
        vol = self.tco2e_yield if self.tco2e_yield is not None else self.tco2e_generated
        return f"<CarbonCalculation(id={self.id}, project_id={self.project_id}, tco2e={vol})>"


@event.listens_for(CarbonCalculation, "before_insert")
@event.listens_for(CarbonCalculation, "before_update")
def _sync_carbon_calculation_fields(mapper, connection, target):
    # Keep tco2e_yield and tco2e_generated in sync
    if target.tco2e_generated is not None and (target.tco2e_yield is None or target.tco2e_yield == 0.0):
        target.tco2e_yield = target.tco2e_generated
    elif target.tco2e_yield is not None and (target.tco2e_generated is None or target.tco2e_generated == 0.0):
        target.tco2e_generated = target.tco2e_yield

    # Keep calculation_log and execution_outputs in sync
    if target.calculation_log is not None and not target.execution_outputs:
        target.execution_outputs = target.calculation_log
    elif target.execution_outputs is not None and not target.calculation_log:
        target.calculation_log = target.execution_outputs

    # Keep created_at and executed_at in sync
    if target.created_at is not None and target.executed_at is None:
        target.executed_at = target.created_at
    elif target.executed_at is not None and target.created_at is None:
        target.created_at = target.executed_at

    # Keep methodology_used and methodology_version_id in sync
    if target.methodology_used is not None and target.methodology_version_id is None:
        target.methodology_version_id = target.methodology_used
    elif target.methodology_version_id is not None and target.methodology_used is None:
        target.methodology_used = target.methodology_version_id

    if target.status is None:
        target.status = "calculated"
