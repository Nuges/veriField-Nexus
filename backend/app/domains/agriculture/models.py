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
from decimal import Decimal
from typing import Any, List, Optional

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from geoalchemy2 import Geometry

# Ensure safe SQLite fallback when SpatiaLite extension is absent
try:
    import geoalchemy2.admin.dialects.sqlite
    _orig_after_create = geoalchemy2.admin.dialects.sqlite.after_create
    def _safe_after_create(target, connection, **kw):
        try:
            _orig_after_create(target, connection, **kw)
        except Exception:
            pass
    geoalchemy2.admin.dialects.sqlite.after_create = _safe_after_create
except Exception:
    pass


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
    geom: Mapped[Optional[Any]] = mapped_column(
        Geometry(geometry_type="GEOMETRY", srid=4326, spatial_index=True),
        nullable=True,
    )

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
    stratum_memberships = relationship("StratumMembership", back_populates="land_unit", cascade="all, delete-orphan")
    management_records = relationship("AgricultureManagementRecord", back_populates="land_unit")

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

    model_represents_30cm: Mapped[bool] = mapped_column(Boolean, default=False)
    extrapolation_method: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    compliance_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    evidence_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_records.id", ondelete="SET NULL"),
        nullable=True,
    )

    physical_sample_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("physical_samples.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
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
    belowground_model_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
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


class Stratum(Base):
    """
    Analytical grouping of land units sharing biophysical, management, or environmental characteristics.
    Supports VM0042 / VT0014 stratification criteria across analytical dimensions:
    - MANAGEMENT_PRACTICE (e.g. reduced tillage, cover cropping, organic inputs)
    - SOIL_TYPE / SOIL_TEXTURE (e.g. clay, sandy loam, silt)
    - AGRO_CLIMATIC_ZONE (e.g. temperate humid, arid, tropical)
    - CROPPING_SYSTEM, TOPOGRAPHY, COMBINED
    """

    __tablename__ = "agriculture_strata"

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

    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    stratum_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="MANAGEMENT_PRACTICE",
    )  # MANAGEMENT_PRACTICE, SOIL_TYPE, SOIL_TEXTURE, AGRO_CLIMATIC_ZONE, CROPPING_SYSTEM, TOPOGRAPHY, COMBINED

    area_ha: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
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
    project = relationship("Project", backref="strata")
    memberships = relationship("StratumMembership", back_populates="stratum", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Stratum(code='{self.code}', name='{self.name}', type='{self.stratum_type}', area_ha={self.area_ha:.2f})>"


class StratumMembership(Base):
    """
    Temporal association linking a LandUnit to an analytical Stratum.
    Enables re-stratification tracking over the project lifecycle.

    Temporal Invariant:
    A LandUnit cannot have overlapping ACTIVE memberships within the same stratification scheme
    (stratum_type). Re-stratification must terminate previous membership (valid_to)
    before or at the start of the new membership period (valid_from).
    """

    __tablename__ = "agriculture_stratum_memberships"

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

    stratum_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agriculture_strata.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    land_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("land_units.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="ACTIVE",
    )  # ACTIVE, RECLASSIFIED, HISTORICAL

    properties: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        nullable=False,
    )

    # Relationships
    stratum = relationship("Stratum", back_populates="memberships")
    land_unit = relationship("LandUnit", back_populates="stratum_memberships")

    def __repr__(self) -> str:
        return f"<StratumMembership(stratum_id={self.stratum_id}, land_unit_id={self.land_unit_id}, status='{self.status}')>"


class AgricultureManagementRecord(Base):
    """
    Categorical field management event record for baseline and project crediting periods.
    Captures tillage practices, synthetic and organic fertilizer applications,
    crop rotations, cover cropping, irrigation, and grazing events with full data provenance.

    Field Semantics:
    - record_type: The management practice or intervention being performed (e.g. TILLAGE, COVER_CROP, FERTILIZER_SYNTHETIC).
    - practice_category:
        * BASELINE: Historical pre-project management practices used to establish historical baseline carbon dynamics.
        * PROJECT_ACTIVITY: Practices implemented during the crediting period as part of the project intervention.
    - data_source:
        * REPORTED: Land manager self-reported record or survey.
        * FIELD_INTERVIEW: Structured interview conducted with land operator.
        * DOCUMENT: Primary operational documents (receipts, delivery notes, logs).
        * FIELD_OBSERVATION: Direct ground observation or audit.
        * REMOTE_SENSING_CORROBORATED: Corroborated with Earth Observation satellite imagery.
          Architectural Invariant: Remote sensing corroboration provides corroborative context,
          NOT direct algorithmic proof of carbon impact or practice execution.
    """

    __tablename__ = "agriculture_management_records"

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

    record_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )  # TILLAGE, FERTILIZER_SYNTHETIC, FERTILIZER_ORGANIC, CROP_ROTATION, COVER_CROP, IRRIGATION, RESIDUE_BURNING, GRAZING, OTHER

    practice_category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="BASELINE",
    )  # BASELINE, PROJECT_ACTIVITY

    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    data_source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="REPORTED",
    )  # REPORTED, FIELD_INTERVIEW, DOCUMENT, FIELD_OBSERVATION, REMOTE_SENSING_CORROBORATED

    corroboration: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="NONE",
        server_default="NONE",
    )  # NONE, REMOTE_SENSING, TELEMETRY, DOCUMENTARY, FIELD_REOBSERVATION, OTHER

    details: Mapped[dict] = mapped_column(JSONB, default=dict)

    evidence_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_records.id", ondelete="SET NULL"),
        nullable=True,
    )

    entered_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    qa_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="PENDING",
    )  # PENDING, VERIFIED, REJECTED

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
    project = relationship("Project", backref="management_records")
    land_unit = relationship("LandUnit", back_populates="management_records")

    def __repr__(self) -> str:
        return f"<AgricultureManagementRecord(type='{self.record_type}', category='{self.practice_category}', date={self.event_date})>"


# ---------------------------------------------------------------------------
# Phase 2: Ground Sampling, Chain of Custody & Laboratory Evidence Models
# ---------------------------------------------------------------------------

class SamplingCampaign(Base):
    """
    Ground sampling campaign for a monitoring period or baseline assessment.
    Represents an operational field campaign under an immutable methodology lock and boundary.
    """

    __tablename__ = "sampling_campaigns"

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

    campaign_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    purpose: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="BASELINE_SOC_DETERMINATION",
    )  # BASELINE_SOC_DETERMINATION, MONITORING_ROUND, STRATUM_VERIFICATION, RESEARCH
    baseline_or_monitoring_context: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="BASELINE",
    )  # BASELINE, MONITORING

    planned_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    planned_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="DRAFT",
    )  # DRAFT, PLANNED, LOCKED, IN_FIELD, COLLECTION_COMPLETE, LAB_IN_PROGRESS, QA_REVIEW, COMPLETE, CANCELLED

    methodology_lock_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict)
    project_boundary_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project_boundary_versions.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
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
    project = relationship("Project", backref="sampling_campaigns")
    plan_versions = relationship("SamplingPlanVersion", back_populates="campaign", cascade="all, delete-orphan")
    sampling_points = relationship("SamplingPoint", back_populates="campaign", cascade="all, delete-orphan")
    physical_samples = relationship("PhysicalSample", back_populates="campaign", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<SamplingCampaign(code='{self.campaign_code}', name='{self.name}', status='{self.status}')>"


class SamplingPlanVersion(Base):
    """
    Versioned sampling plan design within a campaign.
    Freezes stratification truth and design provenance once locked.
    """

    __tablename__ = "sampling_plan_versions"

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

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sampling_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="DRAFT",
    )  # DRAFT, ACTIVE, FROZEN, SUPERSEDED

    effective_as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    stratum_membership_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict)

    sampling_design_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="STRATIFIED_RANDOM",
    )  # SIMPLE_RANDOM, STRATIFIED_RANDOM, SYSTEMATIC_GRID, PURPOSIVE, EXTERNAL_DESIGN, MANUAL

    design_provenance: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="MANUAL",
    )  # MANUAL, IMPORTED, EXTERNAL_DESIGN, CONFIGURED_METHOD, SYSTEM_GENERATED

    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    plan_lock_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
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
    campaign = relationship("SamplingCampaign", back_populates="plan_versions")
    sampling_points = relationship("SamplingPoint", back_populates="plan_version")

    def __repr__(self) -> str:
        return f"<SamplingPlanVersion(v={self.version_number}, status='{self.status}', locked={self.is_locked})>"


class SamplingPoint(Base):
    """
    Planned geographical sample point located within a LandUnit and Stratum.
    """

    __tablename__ = "sampling_points"

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

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sampling_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    plan_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sampling_plan_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    land_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("land_units.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    stratum_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agriculture_strata.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    point_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    planned_lat: Mapped[float] = mapped_column(Float, nullable=False)
    planned_lon: Mapped[float] = mapped_column(Float, nullable=False)

    geom = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=True),
        nullable=True,
    )

    depth_from_cm: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    depth_to_cm: Mapped[float] = mapped_column(Float, nullable=False, default=30.0)
    depth_class_label: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    sampling_purpose: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="SOC_STOCK",
    )  # SOC_STOCK, BULK_DENSITY, TEXTURE, COMBINED

    replicate_group: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    soil_profile_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="PLANNED",
    )  # PLANNED, COLLECTED, CANCELLED, SKIPPED

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        nullable=False,
    )

    # Relationships
    campaign = relationship("SamplingCampaign", back_populates="sampling_points")
    plan_version = relationship("SamplingPlanVersion", back_populates="sampling_points")
    land_unit = relationship("LandUnit")
    stratum = relationship("Stratum")
    physical_sample = relationship("PhysicalSample", back_populates="sampling_point", uselist=False)

    def __repr__(self) -> str:
        return f"<SamplingPoint(code='{self.point_code}', lat={self.planned_lat}, lon={self.planned_lon}, status='{self.status}')>"


class PhysicalSample(Base):
    """
    Physical soil specimen with immutable unique identifier and verified custody chain.
    """

    __tablename__ = "physical_samples"

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

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sampling_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    plan_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sampling_plan_versions.id", ondelete="SET NULL"),
        nullable=True,
    )

    sampling_point_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sampling_points.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    land_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("land_units.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    stratum_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agriculture_strata.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    sample_code: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    soil_profile_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    core_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    sample_dry_mass_g: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    core_diameter_mm: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="PLANNED",
    )  # PLANNED, COLLECTED, SEALED, IN_TRANSIT, RECEIVED_BY_LAB, REJECTED_BY_LAB, ANALYSIS_IN_PROGRESS, ANALYZED, QA_ACCEPTED, QA_REJECTED, ARCHIVED, DISPOSED

    qr_barcode_code: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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
    campaign = relationship("SamplingCampaign", back_populates="physical_samples")
    sampling_point = relationship("SamplingPoint", back_populates="physical_sample")
    land_unit = relationship("LandUnit", viewonly=True)
    stratum = relationship("Stratum", viewonly=True)
    collection_event = relationship("SampleCollectionEvent", back_populates="physical_sample", uselist=False, cascade="all, delete-orphan")
    custody_events = relationship(
        "ChainOfCustodyEvent",
        back_populates="physical_sample",
        order_by="ChainOfCustodyEvent.event_timestamp.asc()",
        cascade="all, delete-orphan",
    )
    laboratory_receipt = relationship("LaboratoryReceipt", back_populates="physical_sample", uselist=False, cascade="all, delete-orphan")
    laboratory_analyses = relationship("LaboratoryAnalysis", back_populates="physical_sample", cascade="all, delete-orphan")
    qa_review = relationship("SampleQAReview", back_populates="physical_sample", uselist=False, cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<PhysicalSample(code='{self.sample_code}', status='{self.status}')>"


class SampleCollectionEvent(Base):
    """
    Field sample extraction record recording planned vs actual coordinates and deviations.
    """

    __tablename__ = "sample_collection_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    physical_sample_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("physical_samples.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    sampling_point_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sampling_points.id", ondelete="CASCADE"),
        nullable=False,
    )

    actual_lat: Mapped[float] = mapped_column(Float, nullable=False)
    actual_lon: Mapped[float] = mapped_column(Float, nullable=False)

    actual_geom = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=True),
        nullable=True,
    )

    deviation_distance_m: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    deviation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    collection_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    collector_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    collector_name: Mapped[str] = mapped_column(String(100), nullable=False)

    actual_depth_from_cm: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    actual_depth_to_cm: Mapped[float] = mapped_column(Float, nullable=False, default=30.0)
    sample_condition: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="GOOD",
    )  # GOOD, MOIST, DISTURBED, COMPACTED, STONEY, DEGRADED

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    photo_evidence_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_records.id", ondelete="SET NULL"),
        nullable=True,
    )
    photo_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    device_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, unique=True)
    sync_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    server_received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        nullable=False,
    )

    # Relationships
    physical_sample = relationship("PhysicalSample", back_populates="collection_event")

    def __repr__(self) -> str:
        return f"<SampleCollectionEvent(sample_id={self.physical_sample_id}, lat={self.actual_lat}, lon={self.actual_lon}, dev={self.deviation_distance_m:.1f}m)>"


class ChainOfCustodyEvent(Base):
    """
    Append-only physical sample custody transfer event.
    """

    __tablename__ = "chain_of_custody_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    physical_sample_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("physical_samples.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # COLLECTION, SEALING, TRANSFER, TRANSPORT_DISPATCH, CARRIER_PICKUP, LAB_RECEIPT, LAB_PROCESSING, QA_REVIEW, DISPOSAL

    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    custodian_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    custodian_name: Mapped[str] = mapped_column(String(100), nullable=False)
    custodian_organization: Mapped[str] = mapped_column(String(150), nullable=False)

    from_location: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    to_location: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)

    condition: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="INTACT",
    )  # INTACT, DAMAGED, LEAKING, TEMPERATURE_COMPROMISED
    seal_intact: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    seal_identifier: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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

    # Relationships
    physical_sample = relationship("PhysicalSample", back_populates="custody_events")

    def __repr__(self) -> str:
        return f"<ChainOfCustodyEvent(type='{self.event_type}', custodian='{self.custodian_name}', at={self.event_timestamp})>"


class LaboratoryReceipt(Base):
    """
    Formal laboratory sample intake record.
    """

    __tablename__ = "laboratory_receipts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    physical_sample_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("physical_samples.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    laboratory_name: Mapped[str] = mapped_column(String(150), nullable=False)
    laboratory_id_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_by_name: Mapped[str] = mapped_column(String(100), nullable=False)

    condition_on_receipt: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="ACCEPTABLE",
    )  # ACCEPTABLE, DAMAGED_CONTAINER, COMPROMISED_SEAL, INSUFFICIENT_MASS, CONTAMINATED

    seal_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="SEALED_INTACT",
    )  # SEALED_INTACT, BROKEN_SEAL, UNSEALED

    intake_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="ACCEPTED",
    )  # ACCEPTED, REJECTED

    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    receipt_evidence_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_records.id", ondelete="SET NULL"),
        nullable=True,
    )

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        nullable=False,
    )

    # Relationships
    physical_sample = relationship("PhysicalSample", back_populates="laboratory_receipt")

    def __repr__(self) -> str:
        return f"<LaboratoryReceipt(lab='{self.laboratory_name}', intake='{self.intake_status}')>"


class LaboratoryAnalysis(Base):
    """
    Standardized laboratory assay performed on an accepted physical sample.
    """

    __tablename__ = "laboratory_analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    physical_sample_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("physical_samples.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    laboratory_name: Mapped[str] = mapped_column(String(150), nullable=False)
    laboratory_accreditation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    accreditation_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="UNVERIFIED",
    )  # NOT_PROVIDED, UNVERIFIED, VERIFIED, EXPIRED
    accreditation_evidence_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_records.id", ondelete="SET NULL"),
        nullable=True,
    )
    analysis_batch_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    analytical_method: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="DRY_COMBUSTION",
    )  # DRY_COMBUSTION, WALKLEY_BLACK, ELEMENTAL_ANALYZER_CN, CORE_BULK_DENSITY, HYDROMETER_TEXTURE, PIPETTE_TEXTURE, OTHER

    method_standard_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    analysis_date: Mapped[date] = mapped_column(Date, nullable=False)
    report_reference_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    analyst_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    qa_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="PENDING",
    )  # PENDING, VERIFIED, REJECTED

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

    # Relationships
    physical_sample = relationship("PhysicalSample", back_populates="laboratory_analyses")
    results = relationship("LaboratoryResult", back_populates="analysis", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<LaboratoryAnalysis(method='{self.analytical_method}', lab='{self.laboratory_name}', date={self.analysis_date})>"


class LaboratoryResult(Base):
    """
    Physical analyte observation with immutable raw value and optional normalized equivalent.
    """

    __tablename__ = "laboratory_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("laboratory_analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    physical_sample_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("physical_samples.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    analyte: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )  # SOC_STOCK_PCT, TOTAL_ORGANIC_CARBON_G_KG, BULK_DENSITY_G_CM3, COARSE_FRAGMENTS_PCT, PH, ELECTRICAL_CONDUCTIVITY_DS_M, SAND_PCT, SILT_PCT, CLAY_PCT, MOISTURE_PCT, OTHER

    raw_value: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    raw_unit: Mapped[str] = mapped_column(String(30), nullable=False)

    normalized_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    normalized_unit: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    normalization_method: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    normalization_version: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    detection_limit: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    quantification_limit: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    uncertainty_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)
    qualifier: Mapped[str] = mapped_column(String(20), nullable=False, default="=")

    is_superseded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    superseded_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("laboratory_results.id", ondelete="SET NULL"),
        nullable=True,
    )
    supersedes_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("laboratory_results.id", ondelete="SET NULL"),
        nullable=True,
    )
    revision_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        nullable=False,
    )

    # Relationships
    analysis = relationship("LaboratoryAnalysis", back_populates="results")

    def __repr__(self) -> str:
        return f"<LaboratoryResult(analyte='{self.analyte}', raw='{self.raw_value} {self.raw_unit}', superseded={self.is_superseded})>"


class SampleQAReview(Base):
    """
    Factual verification review of sample location, depth, custody, and assay completeness.
    """

    __tablename__ = "sample_qa_reviews"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    physical_sample_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("physical_samples.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    reviewer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewer_name: Mapped[str] = mapped_column(String(100), nullable=False)
    review_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    overall_qa_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="PENDING",
    )  # PENDING, ACCEPTED, REJECTED, FLAGGED

    location_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deviation_acceptable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    depth_valid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    custody_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    lab_receipt_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    required_assays_present: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        nullable=False,
    )

    # Relationships
    physical_sample = relationship("PhysicalSample", back_populates="qa_review")

    def __repr__(self) -> str:
        return f"<SampleQAReview(sample_id={self.physical_sample_id}, status='{self.overall_qa_status}')>"


class QuantificationInputSnapshot(Base):
    """
    Immutable snapshot of ground evidence and methodology configuration
    assembled for quantification readiness.
    Provides a tamper-evident, cryptographically hashed input contract.
    """

    __tablename__ = "quantification_input_snapshots"

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

    snapshot_code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="LOCKED")  # PREVIEW, LOCKED, ARCHIVED
    context: Mapped[str] = mapped_column(String(30), nullable=False, default="MONITORING")  # BASELINE, MONITORING, COMBINED

    period_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    period_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    methodology_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("methodology_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    methodology_code: Mapped[str] = mapped_column(String(50), nullable=False, default="VM0042")
    methodology_version: Mapped[str] = mapped_column(String(30), nullable=False, default="2.2")
    rule_set_version: Mapped[str] = mapped_column(String(50), nullable=False, default="VM0042_V2.2_RULES_V1.0")

    project_boundary_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project_boundary_versions.id", ondelete="SET NULL"),
        nullable=True,
    )

    sampling_campaign_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sampling_campaigns.id", ondelete="SET NULL"),
        nullable=True,
    )

    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    is_locked: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    total_eligible_measurements: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_excluded_measurements: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    readiness_summary: Mapped[dict] = mapped_column(JSONB, default=dict)
    input_package: Mapped[dict] = mapped_column(JSONB, default=dict)
    source_evidence_ids: Mapped[list] = mapped_column(JSONB, default=list)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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
    project = relationship("Project", backref="quantification_input_snapshots")
    locked_by = relationship("User", foreign_keys=[locked_by_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    sampling_campaign = relationship("SamplingCampaign")

    def __repr__(self) -> str:
        return f"<QuantificationInputSnapshot(code='{self.snapshot_code}', status='{self.status}', hash='{self.snapshot_hash[:10]}...')>"


class LaboratoryImportBatch(Base):
    """
    Persistent audit envelope for bulk laboratory spreadsheet ingestion (.csv / .xlsx).
    Preserves original uploaded spreadsheet as immutable Evidence with cryptographic SHA-256 hash.
    Tracks mapping configuration, row validation metrics, and transactional commit state.
    """

    __tablename__ = "laboratory_import_batches"

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

    sampling_campaign_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sampling_campaigns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    laboratory_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)  # CSV, XLSX
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    evidence_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_records.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="UPLOADED",
        index=True,
    )  # UPLOADED, PARSING, MAPPING_REQUIRED, VALIDATED, READY_TO_IMPORT, IMPORTING, IMPORTED, PARTIALLY_IMPORTED, FAILED, CANCELLED

    source_type: Mapped[str] = mapped_column(String(30), nullable=False, default="FILE_IMPORT")

    uploaded_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        nullable=False,
    )

    mapping_version: Mapped[str] = mapped_column(String(30), nullable=False, default="V1.0")
    mapping_config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valid_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warning_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    imported_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_summary: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

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
    project = relationship("Project", backref="laboratory_import_batches")
    organization = relationship("Organization")
    sampling_campaign = relationship("SamplingCampaign")
    uploader = relationship("User", foreign_keys=[uploaded_by])
    rows = relationship("LaboratoryImportRow", back_populates="batch", cascade="all, delete-orphan", order_by="LaboratoryImportRow.source_row_number")


class LaboratoryImportRow(Base):
    """
    Granular row-level provenance record linking raw spreadsheet values to
    canonical laboratory analyses and results. Retains original uncoerced text.
    """

    __tablename__ = "laboratory_import_rows"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    import_batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("laboratory_import_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
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

    source_sheet_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    source_row_number: Mapped[int] = mapped_column(Integer, nullable=False)

    raw_row_payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    mapped_payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    validation_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="VALID",
        index=True,
    )  # VALID, WARNING, ERROR, DUPLICATE, IMPORTED, SKIPPED

    validation_messages: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    matched_sample_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("physical_samples.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    matched_sample_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    canonical_analyte: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    raw_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    raw_unit: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    normalized_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    normalized_unit: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    resulting_lab_result_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("laboratory_results.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
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
    batch = relationship("LaboratoryImportBatch", back_populates="rows")
    matched_sample = relationship("PhysicalSample")
    resulting_lab_result = relationship("LaboratoryResult")


class AgriculturePrerequisiteAssessment(Base):
    """
    Authoritative, immutable assessment of VM0042 v2.2 + 2026-06-11 C&C methodology
    prerequisites for Agriculture Phase 3B-0.
    Strictly gates subsequent Phase 3B quantification and ledger minting.
    """

    __tablename__ = "agriculture_prerequisite_assessments"

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

    snapshot_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("quantification_input_snapshots.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    assessment_code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PREVIEW")  # PREVIEW, LOCKED, ARCHIVED, SUPERSEDED
    overall_readiness: Mapped[str] = mapped_column(String(30), nullable=False, default="INCOMPLETE")  # READY, READY_WITH_ADVISORY, INCOMPLETE, BLOCKED

    methodology_code: Mapped[str] = mapped_column(String(50), nullable=False, default="VM0042")
    methodology_version: Mapped[str] = mapped_column(String(30), nullable=False, default="2.2")
    corrections_clarifications_version: Mapped[str] = mapped_column(String(30), nullable=False, default="2026-06-11")
    rule_set_version: Mapped[str] = mapped_column(String(60), nullable=False, default="VM0042_V2.2_RULES_CC20260611_V1.0")

    vcs_standard_version: Mapped[str] = mapped_column(String(30), nullable=False, default="VCS_V4.7")
    vcs_resolution_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
    quantification_route_map: Mapped[dict] = mapped_column(JSONB, default=dict)
    esm_input_dossier: Mapped[dict] = mapped_column(JSONB, default=dict)
    sampling_design_assessment: Mapped[dict] = mapped_column(JSONB, default=dict)
    uncertainty_input_readiness: Mapped[dict] = mapped_column(JSONB, default=dict)
    baseline_monitoring_pairing: Mapped[dict] = mapped_column(JSONB, default=dict)

    dimensions: Mapped[dict] = mapped_column(JSONB, default=dict)
    blocking_reasons: Mapped[list] = mapped_column(JSONB, default=list)
    advisory_notes: Mapped[list] = mapped_column(JSONB, default=list)

    assessment_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    superseded_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agriculture_prerequisite_assessments.id", ondelete="SET NULL"),
        nullable=True,
    )

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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
    project = relationship("Project")
    snapshot = relationship("QuantificationInputSnapshot")
    locked_by = relationship("User", foreign_keys=[locked_by_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    superseded_by = relationship("AgriculturePrerequisiteAssessment", remote_side=[id])

    @property
    def governing_vcs_standard(self) -> str:
        return (self.vcs_resolution_metadata or {}).get("governing_vcs_standard", "VCS_4_7")

    @property
    def v5_template_variant(self) -> str:
        return (self.vcs_resolution_metadata or {}).get("v5_template_variant", "NONE")

    @property
    def project_description_template(self) -> str:
        return (self.vcs_resolution_metadata or {}).get("project_description_template", "VCS_PROJECT_DESCRIPTION_V4.4")

    def __repr__(self) -> str:
        return f"<AgriculturePrerequisiteAssessment(code='{self.assessment_code}', readiness='{self.overall_readiness}', locked={self.is_locked})>"


class AgricultureSOCStockSnapshot(Base):
    """
    Immutable canonical input snapshot for Soil Organic Carbon (SOC) stock
    and Equivalent Soil Mass (ESM) calculations under VM0042 v2.2.
    """

    __tablename__ = "agriculture_soc_stock_snapshots"

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

    prerequisite_assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agriculture_prerequisite_assessments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    snapshot_code: Mapped[str] = mapped_column(String(60), nullable=False, unique=True, index=True)
    measurement_period_type: Mapped[str] = mapped_column(String(30), nullable=False)  # BASELINE, MONITORING
    snapshot_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        nullable=False,
    )

    # Relationships
    project = relationship("Project")
    prerequisite_assessment = relationship("AgriculturePrerequisiteAssessment")


class AgricultureSOCStockResult(Base):
    """
    Authoritative measured Soil Organic Carbon (SOC) Stock result and Equivalent Soil Mass (ESM)
    normalization ledger row for VM0042 v2.2.
    Stores carbon stock in metric tonnes carbon per hectare (t C / ha).
    Strictly prohibits premature tCO2e or crediting subtraction during Phase 3B-1.
    """

    __tablename__ = "agriculture_soc_stock_results"

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

    quantification_unit_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("land_units.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    stratum_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agriculture_strata.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    sampling_point_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sampling_points.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    soil_profile_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    campaign_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sampling_campaigns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    prerequisite_assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agriculture_prerequisite_assessments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    input_snapshot_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("quantification_input_snapshots.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    stock_snapshot_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agriculture_soc_stock_snapshots.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    result_code: Mapped[str] = mapped_column(String(60), nullable=False, unique=True, index=True)
    measurement_period_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)  # BASELINE, MONITORING
    aggregation_level: Mapped[str] = mapped_column(String(30), nullable=False, default="SAMPLE_POINT")  # SAMPLE_POINT, STRATUM, QUANTIFICATION_UNIT, PROJECT

    methodology_version: Mapped[str] = mapped_column(String(30), nullable=False, default="2.2")
    corrections_clarifications_version: Mapped[str] = mapped_column(String(30), nullable=False, default="2026-06-11")
    calculation_engine_version: Mapped[str] = mapped_column(String(60), nullable=False, default="VM0042_V2_2_ESM_ENGINE_V1.0")
    esm_algorithm: Mapped[str] = mapped_column(String(50), nullable=False, default="LAYER_MASS_PROPORTIONING")  # LAYER_MASS_PROPORTIONING, CUBIC_SPLINE

    # Soil Mass and Depth Parameters
    reference_soil_mass_t_ha: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    reference_depth_cm: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, default=Decimal("30.00"))
    equivalent_depth_cm: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)
    total_sampled_soil_mass_t_ha: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    max_sampled_depth_cm: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)

    # Carbon Stock Quantities (Canonical Unit: metric tonnes C per hectare)
    soc_stock_t_c_per_ha: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unadjusted_stock_t_c_per_ha: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)

    # Compliance & Lineage Attributes
    shallow_soil_exception_applied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    depth_sufficiency_status: Mapped[str] = mapped_column(String(50), nullable=False, default="DEPTH_SUFFICIENT")
    area_ha: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    sample_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    strata_weights: Mapped[dict] = mapped_column(JSONB, default=dict)
    component_breakdown: Mapped[dict] = mapped_column(JSONB, default=dict)

    result_status: Mapped[str] = mapped_column(String(30), nullable=False, default="CALCULATED")  # CALCULATED, VERIFIED, SUPERSEDED, BLOCKED
    calculation_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    input_snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    superseded_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agriculture_soc_stock_results.id", ondelete="SET NULL"),
        nullable=True,
    )

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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
    project = relationship("Project")
    quantification_unit = relationship("LandUnit")
    stratum = relationship("Stratum")
    sampling_point = relationship("SamplingPoint")
    campaign = relationship("SamplingCampaign")
    prerequisite_assessment = relationship("AgriculturePrerequisiteAssessment")
    stock_snapshot = relationship("AgricultureSOCStockSnapshot")
    layers = relationship("AgricultureSOCLayerResult", back_populates="stock_result", cascade="all, delete-orphan")


class AgricultureSOCLayerResult(Base):
    """
    Component layer breakdown of measured soil organic carbon and Equivalent Soil Mass
    normalization for a specific profile layer in AgricultureSOCStockResult.
    """

    __tablename__ = "agriculture_soc_layer_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    stock_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agriculture_soc_stock_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    sample_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("physical_samples.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    layer_index: Mapped[int] = mapped_column(Integer, nullable=False)
    depth_upper_cm: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    depth_lower_cm: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    layer_thickness_cm: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)

    bulk_density_g_cm3: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4), nullable=True)
    bulk_density_provenance: Mapped[str] = mapped_column(String(50), nullable=False, default="MEASURED")
    soil_mass_provenance: Mapped[str] = mapped_column(String(50), nullable=False, default="CORE_BULK_DENSITY_DERIVED")
    coarse_fragment_fraction: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4), nullable=True, default=Decimal("0.0000"))
    coarse_fragment_provenance: Mapped[str] = mapped_column(String(50), nullable=False, default="MEASURED")
    coarse_fragment_mass_g: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    fine_soil_mass_g: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)

    soc_concentration_g_kg: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    laboratory_result_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("laboratory_results.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Derived Masses
    layer_soil_mass_t_ha: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    layer_soc_mass_t_c_ha: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    cumulative_soil_mass_t_ha: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    cumulative_soc_mass_t_c_ha: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)

    # ESM Allocation for this Layer
    fraction_in_reference_mass: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4), nullable=True)
    included_soil_mass_t_ha: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    included_soc_mass_t_c_ha: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        nullable=False,
    )

    # Relationships
    stock_result = relationship("AgricultureSOCStockResult", back_populates="layers")
    sample = relationship("PhysicalSample")
    laboratory_result = relationship("LaboratoryResult")


class AgricultureSOCChangeResult(Base):
    """
    Authoritative scenario SOC stock change, stoichiometric 44/12 CO2 conversion,
    sampling variance, and VM0042 Equation (74) uncertainty deduction under QA2 Measure & Re-Measure.
    """

    __tablename__ = "agriculture_soc_change_results"

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

    baseline_stock_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agriculture_soc_stock_results.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    monitoring_stock_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agriculture_soc_stock_results.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    prerequisite_assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agriculture_prerequisite_assessments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    result_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    methodology_version: Mapped[str] = mapped_column(String(30), nullable=False, default="2.2")
    corrections_clarifications_version: Mapped[str] = mapped_column(String(30), nullable=False, default="2026-06-11")
    calculation_engine_version: Mapped[str] = mapped_column(String(50), nullable=False, default="VM0042_V2_2_SOC_CHANGE_V1.0")
    quantification_approach: Mapped[str] = mapped_column(String(30), nullable=False, default="APPROACH_2")

    t_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    t_final: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    elapsed_years: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)

    esm_algorithm: Mapped[str] = mapped_column(String(50), nullable=False, default="WENDT_HAUSER_2013_CUBIC_SPLINE")
    reference_soil_mass_t_ha: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    reference_depth_cm: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, default=Decimal("30.00"))
    total_project_area_ha: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)

    baseline_mean_soc_t_c_per_ha: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    monitoring_mean_soc_t_c_per_ha: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)

    # VM0042 Equations (44) & (45): Annual SOC Stock Change Rate (t C / ha / yr)
    delta_soc_project_t_c_ha_yr: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    delta_soc_baseline_t_c_ha_yr: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=Decimal("0.0000"))
    delta_soc_net_t_c_ha_yr: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)

    # Stoichiometric Conversion: 44/12 (tCO2e / ha / yr)
    delta_co2_project_tco2e_ha_yr: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    delta_co2_baseline_tco2e_ha_yr: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=Decimal("0.0000"))
    delta_co2_net_tco2e_ha_yr: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)

    # VM0042 Section 8.5.2 & QA2 Net Comparative Effect (tCO2e / yr)
    total_project_delta_co2_tco2e_yr: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    total_baseline_delta_co2_tco2e_yr: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("0.0000"))
    total_net_delta_co2_tco2e_yr: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)

    # Authoritative VM0042 Nomenclature
    baseline_soc_change_tco2e_yr: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("0.0000"))
    project_soc_change_tco2e_yr: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("0.0000"))
    qa2_net_soc_effect_tco2e_yr: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("0.0000"))
    uncertainty_adjusted_soc_effect_tco2e_yr: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("0.0000"))

    # VM0042 Section 8.5.1 Equations (44) & (45) Sign Indicator: +1 if (project - baseline >= 0) else -1
    sign_indicator: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Readiness & Estimator Classifications
    eq44_eq45_status: Mapped[str] = mapped_column(String(50), nullable=False, default="PARTIALLY_CONFIGURED_SOC_ONLY")
    df_estimator: Mapped[str] = mapped_column(String(50), nullable=False, default="DEFAULT_STRATIFIED_RANDOM_DF_ESTIMATOR")

    co2_to_c_ratio: Mapped[Decimal] = mapped_column(Numeric(10, 8), nullable=False, default=Decimal("44") / Decimal("12"))

    # VM0042 Equations (70) & (71): Variance and Covariance
    variance_delta_soc_project: Mapped[Decimal] = mapped_column(Numeric(16, 8), nullable=False)
    variance_delta_soc_baseline: Mapped[Decimal] = mapped_column(Numeric(16, 8), nullable=False, default=Decimal("0.00000000"))
    total_variance_delta_soc: Mapped[Decimal] = mapped_column(Numeric(16, 8), nullable=False)
    standard_error_delta_soc_t_c_ha_yr: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    standard_error_tco2e_yr: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)

    # VM0042 Equation (74): Student's t Uncertainty Deduction (p = 0.667) - ZERO DEADBAND
    degrees_of_freedom: Mapped[int] = mapped_column(Integer, nullable=False)
    student_t_value_0667: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    relative_uncertainty_pct: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    allowable_uncertainty_pct: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False, default=Decimal("0.0000"))
    uncertainty_deduction_pct: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False, default=Decimal("0.0000"))
    uncertainty_deduction_fraction: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False, default=Decimal("0.000000"))
    adjusted_net_delta_co2_tco2e_yr: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)

    # Laboratory Measurement Error Router
    measurement_error_status: Mapped[str] = mapped_column(String(50), nullable=False, default="NEGLIGIBLE_PER_VM0042_CONDITIONS")
    measurement_error_router: Mapped[str] = mapped_column(String(50), nullable=False, default="CONVENTIONAL_DRY_COMBUSTION")

    # Detailed Stratum Breakdown & Lineage JSONB
    strata_results: Mapped[list] = mapped_column(JSONB, default=list)
    component_breakdown: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Scope Boundary Invariants
    carbon_accounting_status: Mapped[str] = mapped_column(String(50), nullable=False, default="NOT_CONFIGURED")
    ledger_status: Mapped[str] = mapped_column(String(50), nullable=False, default="BLOCKED_FOR_AGRICULTURE")
    result_status: Mapped[str] = mapped_column(String(30), nullable=False, default="CALCULATED")  # CALCULATED, VERIFIED, SUPERSEDED, BLOCKED

    calculation_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    input_snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    superseded_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agriculture_soc_change_results.id", ondelete="SET NULL"),
        nullable=True,
    )

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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
    project = relationship("Project")
    baseline_stock_result = relationship("AgricultureSOCStockResult", foreign_keys=[baseline_stock_result_id])
    monitoring_stock_result = relationship("AgricultureSOCStockResult", foreign_keys=[monitoring_stock_result_id])
    prerequisite_assessment = relationship("AgriculturePrerequisiteAssessment")


class AgricultureNetGHGResult(Base):
    """
    Authoritative Net GHG Reductions & Removals, Leakage Allocation,
    and Section 8.7 VCU Readiness quantification under VM0042 v2.2 + 11 June 2026 C&C.
    """

    __tablename__ = "agriculture_net_ghg_results"

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

    soc_change_result_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agriculture_soc_change_results.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    prerequisite_assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agriculture_prerequisite_assessments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    result_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    methodology_version: Mapped[str] = mapped_column(String(30), nullable=False, default="2.2")
    corrections_clarifications_version: Mapped[str] = mapped_column(String(30), nullable=False, default="2026-06-11")
    calculation_engine_version: Mapped[str] = mapped_column(String(50), nullable=False, default="VM0042_V2_2_NET_GHG_V1.0")
    ruleset_version: Mapped[str] = mapped_column(String(50), nullable=False, default="VM0042_V2.2_RULES_CC20260611_V1.0")

    verification_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verification_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    elapsed_years: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)

    # Table 5 Applicability Snapshot
    applicability_matrix: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Emissions Totals (tCO2e/yr)
    total_baseline_emissions_tco2e: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("0.0000"))
    total_project_emissions_tco2e: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("0.0000"))
    total_emission_reductions_from_sources_tco2e: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("0.0000"))

    # Carbon Stock Changes
    eq44_baseline_total_carbon_stock_change_tco2e: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("0.0000"))
    eq45_project_total_carbon_stock_change_tco2e: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("0.0000"))
    eq44_eq45_status: Mapped[str] = mapped_column(String(50), nullable=False, default="CALCULATED")

    # Equations 37–43
    gross_reductions_er_tco2e: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("0.0000"))
    gross_removals_cr_tco2e: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("0.0000"))
    total_leakage_tco2e: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("0.0000"))
    leakage_allocation_er_lker_tco2e: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("0.0000"))
    leakage_allocation_cr_lkcr_tco2e: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("0.0000"))
    net_reductions_ernet_tco2e: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("0.0000"))
    net_removals_crnet_tco2e: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("0.0000"))
    total_net_ghg_errnet_tco2e: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("0.0000"))

    # Section 8.7 VCU Readiness (Eqs. 75–79)
    npr_rating_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4), nullable=True)
    risk_assessment_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    buffer_deduction_reductions_tco2e: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    buffer_deduction_removals_tco2e: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    total_buffer_deduction_tco2e: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    internal_vcu_eligible_reductions_tco2e: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    internal_vcu_eligible_removals_tco2e: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    internal_vcu_eligible_total_tco2e: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    vcu_readiness_status: Mapped[str] = mapped_column(String(50), nullable=False, default="NOT_CONFIGURED")

    # Workflow & Integration Boundaries
    internal_mrv_status: Mapped[str] = mapped_column(String(50), nullable=False, default="CALCULATED")
    vvb_status: Mapped[str] = mapped_column(String(50), nullable=False, default="NOT_CONFIGURED / EXTERNAL")
    registry_status: Mapped[str] = mapped_column(String(50), nullable=False, default="NOT_CONFIGURED / EXTERNAL")
    ledger_status: Mapped[str] = mapped_column(String(50), nullable=False, default="BLOCKED_FOR_AGRICULTURE")
    result_status: Mapped[str] = mapped_column(String(30), nullable=False, default="CALCULATED")

    calculation_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    input_snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    superseded_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agriculture_net_ghg_results.id", ondelete="SET NULL"),
        nullable=True,
    )

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    component_breakdown: Mapped[dict] = mapped_column(JSONB, default=dict)

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
    project = relationship("Project")
    soc_change_result = relationship("AgricultureSOCChangeResult")
    prerequisite_assessment = relationship("AgriculturePrerequisiteAssessment")
    vintages = relationship("AgricultureVintageGHGResult", back_populates="net_ghg_result", cascade="all, delete-orphan")


class AgricultureVintageGHGResult(Base):
    """
    Annual vintage line-item result belonging to an AgricultureNetGHGResult.
    """

    __tablename__ = "agriculture_vintage_ghg_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    net_ghg_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agriculture_net_ghg_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    vintage_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    total_baseline_emissions_tco2e: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("0.0000"))
    total_project_emissions_tco2e: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("0.0000"))
    total_emission_reductions_from_sources_tco2e: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("0.0000"))

    eq44_baseline_total_carbon_stock_change_tco2e: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("0.0000"))
    eq45_project_total_carbon_stock_change_tco2e: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("0.0000"))

    gross_reductions_er_tco2e: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("0.0000"))
    gross_removals_cr_tco2e: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("0.0000"))
    total_leakage_tco2e: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("0.0000"))
    leakage_allocation_er_lker_tco2e: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("0.0000"))
    leakage_allocation_cr_lkcr_tco2e: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("0.0000"))
    net_reductions_ernet_tco2e: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("0.0000"))
    net_removals_crnet_tco2e: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("0.0000"))
    total_net_ghg_errnet_tco2e: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("0.0000"))

    buffer_deduction_reductions_tco2e: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    buffer_deduction_removals_tco2e: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    total_buffer_deduction_tco2e: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    internal_vcu_eligible_reductions_tco2e: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    internal_vcu_eligible_removals_tco2e: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    internal_vcu_eligible_total_tco2e: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)

    vintage_details: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        nullable=False,
    )

    # Relationships
    net_ghg_result = relationship("AgricultureNetGHGResult", back_populates="vintages")
