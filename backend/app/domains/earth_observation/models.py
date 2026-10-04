"""
=============================================================================
VeriField Nexus — Centralized Earth Observation (EO) Data Models
=============================================================================
Defines relational entities for cross-sector satellite remote sensing and MRV:
1. EOProvider: Provider registry with truthful capability states.
2. EOProduct: Product catalog (Sentinel-2, Sentinel-1, Landsat, etc.).
3. EOAreaOfInterest (AOI): Project / Land Unit / Facility spatial footprints.
4. EOObservation: Dated remote sensing scene with provenance and cloud QA.
5. EODerivedLayer: Verified spectral indices (NDVI, EVI, NDWI) with formulas.
6. EOProcessingRun: Audit log of processing and analysis runs.
7. EOSpatialAnomaly: Factual vegetation/disturbance signals & review triggers.
8. ProjectBoundaryVersion: Immutable boundary history with effective dates.

INVARIANTS:
- Satellite index != Carbon. Spectral indices reflect canopy/vigor, NOT carbon.
- SAR backscatter is radar reflectivity, NEVER direct "Soil Moisture".
- Basemap imagery is geographic context, NEVER an observation record.
- Every observation and derived layer maintains SHA-256 cryptographic provenance.
=============================================================================
"""

import uuid
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
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


class EOProviderCapability(str, Enum):
    """
    Truthful capability states for Earth Observation data providers.
    A provider is LIVE_VERIFIED only after an actual provider request has succeeded.
    """
    LIVE_VERIFIED = "LIVE_VERIFIED"
    LIVE_CONFIGURED = "LIVE_CONFIGURED"
    MOCK_TESTED = "MOCK_TESTED"
    INTERFACE_ONLY = "INTERFACE_ONLY"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    DISABLED = "DISABLED"
    ERROR = "ERROR"


class EOObservationType(str, Enum):
    OPTICAL_MULTISPECTRAL = "OPTICAL_MULTISPECTRAL"
    SAR_C_BAND_BACKSCATTER = "SAR_C_BAND_BACKSCATTER"
    THERMAL_INFRARED = "THERMAL_INFRARED"
    HIGH_RES_OPTICAL = "HIGH_RES_OPTICAL"


class EOQualityStatus(str, Enum):
    USABLE = "USABLE"
    PARTIALLY_USABLE = "PARTIALLY_USABLE"
    CLOUD_OBSCURED = "CLOUD_OBSCURED"
    NO_DATA = "NO_DATA"
    PROCESSING_FAILED = "PROCESSING_FAILED"


class EOSpatialAnomalyType(str, Enum):
    VEGETATION_INDEX_CHANGE = "VEGETATION_INDEX_CHANGE"
    SPECTRAL_CHANGE = "SPECTRAL_CHANGE"
    OBSERVED_WATER_EXTENT_CHANGE = "OBSERVED_WATER_EXTENT_CHANGE"
    LAND_COVER_CHANGE_SIGNAL = "LAND_COVER_CHANGE_SIGNAL"
    POSSIBLE_DISTURBANCE = "POSSIBLE_DISTURBANCE"


class EOAnomalyStatus(str, Enum):
    OBSERVED = "OBSERVED"
    UNDER_REVIEW = "UNDER_REVIEW"
    CORROBORATED = "CORROBORATED"
    DISMISSED = "DISMISSED"
    RESOLVED = "RESOLVED"


class ProjectBoundaryVersion(Base):
    """
    Versioned record of a project's physical boundary geometry.
    Ensures historical observations retain reference to the exact boundary in effect.
    """
    __tablename__ = "project_boundary_versions"

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
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    boundary_geojson: Mapped[dict] = mapped_column(JSONB, nullable=False)
    geom: Mapped[Optional[Any]] = mapped_column(
        Geometry(geometry_type="GEOMETRY", srid=4326, spatial_index=True),
        nullable=True,
    )
    source: Mapped[str] = mapped_column(String(50), default="DECLARED")
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    area_ha: Mapped[float] = mapped_column(Float, nullable=False)
    perimeter_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    centroid_lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    centroid_lon: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    crs: Mapped[str] = mapped_column(String(20), default="EPSG:4326")
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

    project = relationship("Project", backref="boundary_versions")

    __table_args__ = (
        Index("ix_project_boundary_ver_unique", "project_id", "version_number", unique=True),
    )


class EOAreaOfInterest(Base):
    """
    Designated Area of Interest (AOI) for Earth Observation queries and analysis.
    Derived from Project Boundary, Land Unit, Facility, or custom polygon.
    """
    __tablename__ = "eo_areas_of_interest"

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
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    aoi_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="PROJECT_BOUNDARY",
    )  # PROJECT_BOUNDARY, LAND_UNIT, STRATUM, FIELD, FACILITY, CUSTOM
    source_entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    boundary_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project_boundary_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    geometry_geojson: Mapped[dict] = mapped_column(JSONB, nullable=False)
    geom: Mapped[Optional[Any]] = mapped_column(
        Geometry(geometry_type="GEOMETRY", srid=4326, spatial_index=True),
        nullable=True,
    )
    bbox: Mapped[dict] = mapped_column(JSONB, nullable=False)  # {"min_lon": float, "min_lat": float, "max_lon": float, "max_lat": float}
    area_ha: Mapped[float] = mapped_column(Float, nullable=False)
    crs: Mapped[str] = mapped_column(String(20), default="EPSG:4326")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
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

    project = relationship("Project", backref="eo_aois")
    observations = relationship("EOObservation", back_populates="aoi", cascade="all, delete-orphan")


class EOProvider(Base):
    """
    Registered Earth Observation data provider and its verified runtime capability.
    """
    __tablename__ = "eo_providers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    provider_type: Mapped[str] = mapped_column(String(50), nullable=False)  # COPERNICUS, USGS, PLANET, CUSTOM
    capability_state: Mapped[str] = mapped_column(
        String(30),
        default=EOProviderCapability.NOT_CONFIGURED.value,
        nullable=False,
    )
    endpoint_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    auth_configured: Mapped[bool] = mapped_column(Boolean, default=False)
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    verification_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        nullable=False,
    )


class EOProduct(Base):
    """
    Catalog of distinct satellite products offered by providers.
    """
    __tablename__ = "eo_products"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    provider_code: Mapped[str] = mapped_column(String(50), ForeignKey("eo_providers.code"), nullable=False, index=True)
    product_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)  # Sentinel-2A/B, Sentinel-1A, Landsat 8/9
    sensor: Mapped[str] = mapped_column(String(50), nullable=False)    # MSI, C-SAR, OLI-TIRS
    observation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    spatial_resolution_m: Mapped[float] = mapped_column(Float, nullable=False)
    default_processing_level: Mapped[str] = mapped_column(String(20), default="L2A")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class EOObservation(Base):
    """
    An immutable, dated Earth Observation scene captured by a satellite sensor.
    Maintains cryptographic SHA-256 provenance linking raw assets, parameters, and metadata.
    """
    __tablename__ = "eo_observations"

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
    aoi_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("eo_areas_of_interest.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    land_unit_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("land_units.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    boundary_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project_boundary_versions.id", ondelete="SET NULL"),
        nullable=True,
    )

    provider_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    sensor: Mapped[str] = mapped_column(String(50), nullable=False)
    product_code: Mapped[str] = mapped_column(String(50), nullable=False)
    scene_id: Mapped[str] = mapped_column(String(150), nullable=False, index=True)

    acquisition_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    processing_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    spatial_resolution_m: Mapped[float] = mapped_column(Float, nullable=False)
    cloud_cover_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    crs: Mapped[str] = mapped_column(String(20), default="EPSG:4326")
    geometry_geojson: Mapped[dict] = mapped_column(JSONB, nullable=False)
    footprint_geom: Mapped[Optional[Any]] = mapped_column(
        Geometry(geometry_type="GEOMETRY", srid=4326, spatial_index=True),
        nullable=True,
    )
    bbox: Mapped[dict] = mapped_column(JSONB, nullable=False)

    observation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    processing_level: Mapped[str] = mapped_column(String(20), default="L2A")
    processing_version: Mapped[str] = mapped_column(String(50), default="1.0.0")

    quality_status: Mapped[str] = mapped_column(
        String(30),
        default=EOQualityStatus.USABLE.value,
        nullable=False,
    )
    quality_flags: Mapped[dict] = mapped_column(JSONB, default=dict)

    raw_band_uris: Mapped[dict] = mapped_column(JSONB, default=dict)
    raw_band_checksums: Mapped[dict] = mapped_column(JSONB, default=dict)
    asset_uri: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    checksum_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    provenance_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    lineage_manifest: Mapped[dict] = mapped_column(JSONB, default=dict)

    is_baseline: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    baseline_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        nullable=False,
    )

    project = relationship("Project", backref="eo_observations")
    aoi = relationship("EOAreaOfInterest", back_populates="observations")
    derived_layers = relationship("EODerivedLayer", back_populates="source_observation", cascade="all, delete-orphan")
    anomalies = relationship("EOSpatialAnomaly", back_populates="observation", cascade="all, delete-orphan")

    @property
    def bounding_box(self) -> Optional[List[float]]:
        if not self.bbox:
            return None
        if isinstance(self.bbox, dict):
            return [
                self.bbox.get("min_lon"),
                self.bbox.get("min_lat"),
                self.bbox.get("max_lon"),
                self.bbox.get("max_lat"),
            ]
        if isinstance(self.bbox, (list, tuple)) and len(self.bbox) == 4:
            return list(self.bbox)
        return None

    __table_args__ = (
        Index("ix_eo_obs_proj_acq", "project_id", "acquisition_timestamp"),
        Index("ix_eo_obs_org_prov", "organization_id", "provider_code"),
    )


class EODerivedLayer(Base):
    """
    A verified spatial or spectral index layer computed from an observation.
    Must maintain explicit formula definition, band mappings, and processor version.
    """
    __tablename__ = "eo_derived_layers"

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
    observation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("eo_observations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    aoi_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("eo_areas_of_interest.id", ondelete="SET NULL"),
        nullable=True,
    )

    layer_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )  # NDVI, EVI, NDWI_GAO_1996, NDWI_MCFEETERS_1996, SAR_VV_BACKSCATTER, SAR_VH_BACKSCATTER, OBSERVED_CHANGE
    formula_identifier: Mapped[str] = mapped_column(String(100), nullable=False)
    formula: Mapped[str] = mapped_column(String(255), nullable=False)
    band_mapping: Mapped[dict] = mapped_column(JSONB, nullable=False)
    processor_version: Mapped[str] = mapped_column(String(50), nullable=False)

    spatial_resolution_m: Mapped[float] = mapped_column(Float, nullable=False)
    statistics: Mapped[dict] = mapped_column(JSONB, default=dict)  # {"mean": float, "min": float, "max": float, "std": float}
    asset_uri: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    quality_status: Mapped[str] = mapped_column(String(30), default=EOQualityStatus.USABLE.value)
    provenance_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        nullable=False,
    )

    source_observation = relationship("EOObservation", back_populates="derived_layers")


class EOProcessingRun(Base):
    """
    Execution provenance audit record for any EO ingestion, analysis, or batch job.
    """
    __tablename__ = "eo_processing_runs"

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
    run_type: Mapped[str] = mapped_column(String(50), nullable=False)  # DISCOVERY, INGESTION, DERIVED_INDICES, CHANGE_DETECTION
    status: Mapped[str] = mapped_column(String(30), default="COMPLETED", nullable=False)
    parameters: Mapped[dict] = mapped_column(JSONB, default=dict)
    input_observation_ids: Mapped[list] = mapped_column(JSONB, default=list)
    output_layer_ids: Mapped[list] = mapped_column(JSONB, default=list)
    execution_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    provenance_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        nullable=False,
    )


class EOSpatialAnomaly(Base):
    """
    A factual spatial or spectral change signal detected across temporal observations.
    Triggers an existing VerificationTask or review recommendation for field team inspection.
    """
    __tablename__ = "eo_spatial_anomalies"

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
    aoi_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("eo_areas_of_interest.id", ondelete="SET NULL"),
        nullable=True,
    )
    observation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("eo_observations.id", ondelete="SET NULL"),
        nullable=True,
    )
    anomaly_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=EOSpatialAnomalyType.VEGETATION_INDEX_CHANGE.value,
    )
    severity: Mapped[str] = mapped_column(String(20), default="MEDIUM")  # LOW, MEDIUM, HIGH
    status: Mapped[str] = mapped_column(
        String(30),
        default=EOAnomalyStatus.OBSERVED.value,
        nullable=False,
    )
    geom: Mapped[Optional[Any]] = mapped_column(
        Geometry(geometry_type="GEOMETRY", srid=4326, spatial_index=True),
        nullable=True,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    review_recommendation: Mapped[str] = mapped_column(Text, nullable=False)

    baseline_observation_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    comparison_metric: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    delta_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    verification_task_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("verification_tasks.id", ondelete="SET NULL"),
        nullable=True,
    )
    corroborating_activity_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    corroboration_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    corroborated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        nullable=False,
    )

    observation = relationship("EOObservation", back_populates="anomalies")
    verification_task = relationship("VerificationTask", backref="eo_anomalies")
