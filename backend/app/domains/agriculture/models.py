"""
=============================================================================
VeriField Nexus — Agriculture & Land Use Data Models
=============================================================================
Defines relational entities for:
- Land Units (Hierarchical: Project -> Parcel -> Field -> Stratum -> Monitoring Plot)
- Soil Samples (Depths, lab analytical methods, VM0042 compliance classification)
- Tree Observations (VM0047 raw field measurements vs derived allometric biomass)
- Satellite Observations (EO scenes, derived vegetation/moisture indices, lineage)
- Agriculture Model Runs (VMD0053 / VT0014 execution provenance & spatial uncertainty)
=============================================================================
"""

import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LandUnit(Base):
    """
    Hierarchical Land Management Unit.
    Supports Project -> Parcel -> Field / Management Unit -> Stratum -> Monitoring Plot.
    All boundaries use exact WGS84 geodesic ellipsoidal calculations.
    """

    __tablename__ = "land_units"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("land_units.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    unit_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
        default="FIELD",
    )  # PARCEL, FIELD, STRATUM, MONITORING_PLOT

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)

    boundary_geojson: Mapped[dict] = mapped_column(JSONB, nullable=False)

    boundary_source: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="DECLARED",
    )  # DECLARED, GNSS_SURVEY, RTK_GNSS, CADASTRAL, IMPORTED_GIS, MANUALLY_DRAWN

    boundary_crs: Mapped[str] = mapped_column(String(20), default="EPSG:4326")

    area_ha: Mapped[float] = mapped_column(Float, nullable=False)
    perimeter_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    centroid_lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    centroid_lon: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    land_use_category: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )  # CROPLAND, AGROFORESTRY, GRASSLAND, PADDY_RICE, ORCHARD, SILVOPASTURE, FALLOW

    soil_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    slope_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    properties: Mapped[dict] = mapped_column(JSONB, default=dict)

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
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    project = relationship("Project", backref="land_units")
    parent = relationship("LandUnit", remote_side=[id], backref="children")
    soil_samples = relationship("SoilSample", back_populates="land_unit", cascade="all, delete-orphan")
    tree_observations = relationship("TreeObservation", back_populates="land_unit", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<LandUnit(id={self.id}, name='{self.name}', type='{self.unit_type}', area_ha={self.area_ha:.2f})>"


class SoilSample(Base):
    """
    Soil core sample measurement with depth-specific analysis.
    Implements VM0042 depth use-classification (>= 30cm vs < 30cm).
    """

    __tablename__ = "soil_samples"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    land_unit_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("land_units.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    sample_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    sampling_date: Mapped[date] = mapped_column(Date, nullable=False)

    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    depth_upper_cm: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    depth_lower_cm: Mapped[float] = mapped_column(Float, nullable=False)  # e.g. 30.0 or 15.0

    bulk_density_g_cm3: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    soc_stock_pct: Mapped[float] = mapped_column(Float, nullable=False)  # Soil Organic Carbon %
    total_organic_carbon_g_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Computed: SOC stock in t C/ha = SOC% * bulk_density * depth_thickness_cm * (1 - coarse_frag/100)
    computed_soc_stock_t_c_ha: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    coarse_fragments_pct: Mapped[float] = mapped_column(Float, default=0.0)

    ph: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    electrical_conductivity_ds_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    texture_class: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    lab_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="DRY_COMBUSTION",
    )  # DRY_COMBUSTION, WALKLEY_BLACK, SPECTROSCOPY_NIR, SPECTROSCOPY_MIR, OTHER

    lab_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    lab_accreditation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    qa_status: Mapped[str] = mapped_column(
        String(30),
        default="PENDING",
    )  # PENDING, ACCEPTED, FLAGGED, REJECTED

    compliance_classification: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="REFERENCE_ONLY",
    )  # EX_POST_QUANTIFICATION_ELIGIBLE, MODEL_CALIBRATION_ELIGIBLE, MODEL_VALIDATION_ELIGIBLE, REFERENCE_ONLY, NON_COMPLIANT

    compliance_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    evidence_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_records.id", ondelete="SET NULL"),
        nullable=True,
    )

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
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    land_unit = relationship("LandUnit", back_populates="soil_samples")
    project = relationship("Project", backref="soil_samples")

    def __repr__(self) -> str:
        return f"<SoilSample(code='{self.sample_code}', depth={self.depth_upper_cm}-{self.depth_lower_cm}cm, soc={self.soc_stock_pct}%, class='{self.compliance_classification}')>"


class TreeObservation(Base):
    """
    Tree measurement observation for Afforestation / Reforestation / Revegetation (VM0047).
    Strictly separates raw ground observations from derived allometric biomass calculations.
    Supports AREA_BASED (plot sample) and CENSUS_BASED (individual tagged tree) monitoring.
    """

    __tablename__ = "tree_observations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    land_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("land_units.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    sampling_approach: Mapped[str] = mapped_column(
        String(30),
        default="AREA_BASED",
        nullable=False,
    )  # AREA_BASED, CENSUS_BASED

    tag_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    species_scientific: Mapped[str] = mapped_column(String(100), nullable=False)
    species_common: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Raw Measurements
    dbh_cm: Mapped[float] = mapped_column(Float, nullable=False)  # Diameter at breast height (1.3m)
    height_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    crown_diameter_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    health_status: Mapped[str] = mapped_column(
        String(30),
        default="HEALTHY",
    )  # HEALTHY, STRESSED, DEAD_STANDING, DEAD_FALLEN, COPPICING

    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    measurement_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Derived Biomass (strictly computed via registered allometric equations in calculation runs)
    allometric_equation_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    derived_aboveground_biomass_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    derived_belowground_biomass_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    derived_carbon_stock_t_co2e: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    calculation_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    evidence_photo_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

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
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    land_unit = relationship("LandUnit", back_populates="tree_observations")
    project = relationship("Project", backref="tree_observations")

    def __repr__(self) -> str:
        return f"<TreeObservation(id={self.id}, species='{self.species_scientific}', dbh={self.dbh_cm}cm, height={self.height_m}m)>"


class SatelliteObservation(Base):
    """
    Earth Observation (EO) satellite scene metadata and derived spectral indices.
    Enforces the architectural invariant: Satellite index != Carbon.
    SAR observations are labeled as 'SAR observation' or 'soil-moisture proxy', never 'Soil Moisture'.
    """

    __tablename__ = "satellite_observations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    land_unit_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("land_units.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # SENTINEL_2, SENTINEL_1, LANDSAT_8_9, PLANET_SCOPE, SKYSAT

    scene_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    acquisition_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cloud_coverage_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    spatial_resolution_m: Mapped[float] = mapped_column(Float, nullable=False)

    observation_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # OPTICAL_MULTISPECTRAL, SAR_C_BAND_BACKSCATTER, THERMAL_INFRARED, HIGH_RES_OPTICAL

    raw_band_uris: Mapped[dict] = mapped_column(JSONB, default=dict)
    derived_indices: Mapped[dict] = mapped_column(JSONB, default=dict)
    provenance_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    processing_level: Mapped[str] = mapped_column(String(20), default="L2A")
    lineage_manifest: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        nullable=False,
    )

    # Relationships
    project = relationship("Project", backref="satellite_observations")
    land_unit = relationship("LandUnit", backref="satellite_observations")

    def __repr__(self) -> str:
        return f"<SatelliteObservation(provider='{self.provider}', scene='{self.scene_id}', date={self.acquisition_timestamp})>"


class AgricultureModelRun(Base):
    """
    Model calibration, validation, and execution provenance (VMD0053 / VT0014).
    Stores model inputs, parameterizations, performance metrics, and explicit spatial uncertainty.
    """

    __tablename__ = "agriculture_model_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    model_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )  # VT0014_DIGITAL_SOIL_MAPPING, DAYCENT, DNDC, ROTH_C, CHAVE_ALLOMETRICS

    model_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # DIGITAL_SOIL_MAPPING, BIOGEOCHEMICAL_PROCESS, EMPIRICAL_ALLOMETRIC, REMOTE_SENSING_FUSION

    version: Mapped[str] = mapped_column(String(30), nullable=False)
    run_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="COMPLETED",
    )  # RUNNING, COMPLETED, FAILED, NOT_CONFIGURED

    input_parameters: Mapped[dict] = mapped_column(JSONB, default=dict)
    input_dataset_hashes: Mapped[dict] = mapped_column(JSONB, default=dict)
    performance_metrics: Mapped[dict] = mapped_column(JSONB, default=dict)
    uncertainty_metrics: Mapped[dict] = mapped_column(JSONB, default=dict)
    output_manifest: Mapped[dict] = mapped_column(JSONB, default=dict)
    provenance_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        nullable=False,
    )

    # Relationships
    project = relationship("Project", backref="model_runs")

    def __repr__(self) -> str:
        return f"<AgricultureModelRun(model='{self.model_name}', version='{self.version}', status='{self.status}')>"
