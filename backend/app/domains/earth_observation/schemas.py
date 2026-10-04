"""
=============================================================================
VeriField Nexus — Earth Observation Pydantic Schemas
=============================================================================
Request and response models for:
- Provider capability matrix
- Areas of Interest (AOIs) and Project Boundary Versions
- Scene search and ingestion
- Observations and Derived Layers
- Spatial Anomalies and Corroboration
- Baseline Packages and MRV Evidence Manifests
=============================================================================
"""

import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ─── Provider Schemas ───

class ProviderCapabilityInfo(BaseModel):
    provider_code: str
    capability: str
    is_configured: bool
    granular_capabilities: Optional[Dict[str, str]] = None


class ProviderMatrixResponse(BaseModel):
    providers: Dict[str, ProviderCapabilityInfo]


# ─── AOI & Boundary Schemas ───

class BoundarySetRequest(BaseModel):
    name: str = Field(default="Project Boundary", max_length=150)
    geometry_geojson: Dict[str, Any]
    source: str = Field(default="DECLARED", max_length=50)
    reason: Optional[str] = None


class ProjectBoundaryVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    version_number: int
    effective_date: date
    source: str
    reason: Optional[str] = None
    area_ha: float
    perimeter_m: Optional[float] = None
    centroid_lat: Optional[float] = None
    centroid_lon: Optional[float] = None
    crs: str
    created_at: datetime


class AOIResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    aoi_type: str
    boundary_version_id: Optional[uuid.UUID] = None
    geometry_geojson: Dict[str, Any]
    bbox: Dict[str, float]
    area_ha: float
    crs: str
    is_active: bool
    created_at: datetime


# ─── Scene Search & Ingestion Schemas ───

class SceneSearchRequest(BaseModel):
    bounding_box: List[float] = Field(..., min_length=4, max_length=4)  # [min_lon, min_lat, max_lon, max_lat]
    date_from: datetime
    date_to: datetime
    provider_code: Optional[str] = None
    max_cloud_cover: float = Field(default=30.0, ge=0.0, le=100.0)


class RawSceneResponse(BaseModel):
    scene_id: str
    provider_code: str
    platform: str
    sensor: str
    product_code: str
    observation_type: str
    acquisition_timestamp: datetime
    spatial_resolution_m: float
    bounding_box: List[float]
    processing_level: str
    cloud_cover_pct: Optional[float] = None
    quality_status: str


class ObservationIngestRequest(BaseModel):
    scene_id: str
    provider_code: str
    platform: str
    sensor: str
    product_code: str
    observation_type: str
    acquisition_timestamp: datetime
    spatial_resolution_m: float
    bounding_box: List[float] = Field(..., min_length=4, max_length=4)
    geometry_geojson: Dict[str, Any]
    processing_level: str = "L2A"
    cloud_cover_pct: Optional[float] = None
    raw_band_uris: Dict[str, str] = Field(default_factory=dict)
    raw_band_checksums: Dict[str, str] = Field(default_factory=dict)
    asset_uri: Optional[str] = None
    quality_flags: Dict[str, Any] = Field(default_factory=dict)
    lineage_manifest: Dict[str, Any] = Field(default_factory=dict)
    is_baseline: bool = False
    baseline_notes: Optional[str] = None


class ObservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    aoi_id: Optional[uuid.UUID] = None
    provider_code: str
    platform: str
    sensor: str
    product_code: str
    scene_id: str
    acquisition_timestamp: datetime
    spatial_resolution_m: float
    cloud_cover_pct: Optional[float] = None
    quality_status: str
    observation_type: str
    processing_level: str
    provenance_hash: str
    is_baseline: bool
    geometry_geojson: Optional[Dict[str, Any]] = None
    bbox: Optional[Dict[str, Any]] = None
    raw_band_uris: Optional[Dict[str, str]] = None
    asset_uri: Optional[str] = None
    quality_flags: Optional[Dict[str, Any]] = None
    created_at: datetime


# ─── Derived Layer Schemas ───

class DerivedLayerComputeRequest(BaseModel):
    observation_id: uuid.UUID
    layer_type: str  # NDVI, EVI, NDWI_GAO_1996, NDWI_MCFEETERS_1996, SAR_VV_BACKSCATTER, SAR_VH_BACKSCATTER
    statistics: Dict[str, float] = Field(..., description="e.g. {'mean': 0.65, 'min': 0.1, 'max': 0.85, 'std': 0.12}")
    asset_uri: Optional[str] = None


class DerivedLayerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    observation_id: uuid.UUID
    aoi_id: Optional[uuid.UUID] = None
    layer_type: str
    formula_identifier: str
    formula: str
    band_mapping: Dict[str, Any]
    processor_version: str
    spatial_resolution_m: float
    statistics: Dict[str, Any]
    quality_status: str
    provenance_hash: str
    created_at: datetime


# ─── Spatial Anomaly Schemas ───

class AnomalyCorroborateRequest(BaseModel):
    corroborated: bool
    notes: str
    verification_task_id: Optional[uuid.UUID] = None
    corroborating_activity_id: Optional[uuid.UUID] = None


class AnomalyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    aoi_id: Optional[uuid.UUID] = None
    observation_id: Optional[uuid.UUID] = None
    anomaly_type: str
    severity: str
    status: str
    description: str
    review_recommendation: str
    comparison_metric: Optional[str] = None
    delta_value: Optional[float] = None
    detected_at: datetime
    corroborated_at: Optional[datetime] = None
    corroboration_notes: Optional[str] = None


# ─── Baseline & Manifest Schemas ───

class BaselinePackageCreateRequest(BaseModel):
    notes: Optional[str] = None


class BaselinePackageResponse(BaseModel):
    baseline_package_id: str
    project_id: str
    organization_id: str
    aoi_id: str
    boundary_version_number: int
    boundary_area_ha: float
    sealed_at: str
    package_seal_hash: str
    notes: str
    observation_count: int
    observations: List[Dict[str, Any]]
