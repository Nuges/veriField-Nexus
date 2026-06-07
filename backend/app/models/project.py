import uuid
from datetime import date, datetime, timezone
from sqlalchemy import String, Float, Date, DateTime, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Project(Base):
    """
    ==========================================================================
    VeriField Nexus — Project Configuration Model (Layer 1 of 3-Layer MRV)
    ==========================================================================
    Groups sites/activities under a specific methodology (e.g. AMS-I.F, VM0050).
    Stores baseline parameters and emission factors needed for the deterministic
    carbon calculation engine. This is the ADMIN-ONLY configuration layer.

    Architecture:
        Project (config/methodology) → Site (captured data) → Calculation Engine
    ==========================================================================
    """
    __tablename__ = "projects"

    # --- Primary Key (UUID for relational integrity) ---
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    # --- Human-readable project code (e.g. "VF-EN-001", "VF-CK-003") ---
    project_code: Mapped[str] = mapped_column(
        String(20), nullable=True, unique=True, index=True,
    )

    # --- Project Identity ---
    name: Mapped[str] = mapped_column(String, nullable=False)
    sector: Mapped[str] = mapped_column(
        String(30), nullable=True, default="energy", index=True,
        # Enum values: "cookstove", "energy"
    )
    country: Mapped[str] = mapped_column(
        String(100), nullable=True, default="Nigeria",
    )

    # --- Methodology & Registry ---
    methodology_id: Mapped[str] = mapped_column(
        String, nullable=False, index=True,
        # e.g. "AMS-I.F", "VM0050", "ENERGY_DISPLACEMENT"
    )
    registry_id: Mapped[str] = mapped_column(String, nullable=True)

    # --- Baseline Source Configuration ---
    baseline_source: Mapped[str] = mapped_column(
        String(30), nullable=True, default="diesel_generator",
        # Enum values: "diesel_generator", "grid"
    )

    # --- Emission Factors (IPCC 2006 defaults, overridable per project) ---
    diesel_emission_factor: Mapped[float] = mapped_column(
        Float, nullable=True, default=2.68,
        # kgCO2 per litre of diesel (IPCC default)
    )
    grid_emission_factor: Mapped[float] = mapped_column(
        Float, nullable=True, default=0.7,
        # kgCO2 per kWh of grid electricity
    )

    # --- Crediting Period (Verra/Gold Standard aligned) ---
    crediting_start: Mapped[date] = mapped_column(
        Date, nullable=True,
    )
    crediting_end: Mapped[date] = mapped_column(
        Date, nullable=True,
    )

    # --- Flexible Baseline Configuration (JSONB for methodology-specific params) ---
    baseline_parameters: Mapped[dict] = mapped_column(JSONB, default=dict)

    # --- Timestamps ---
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

    # --- Relationships ---
    carbon_calculations = relationship("CarbonCalculation", backref="project")
