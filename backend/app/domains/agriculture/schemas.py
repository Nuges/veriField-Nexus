"""
=============================================================================
VeriField Nexus — Agriculture & Land Use Pydantic Schemas
=============================================================================
Request and response models for:
- Land Units (Parcels, Fields, Strata, Monitoring Plots)
- Soil Samples (Depth-stratified, lab accredited, VM0042 classified)
- Tree Observations (Raw measurements, allometric derivations)
- Satellite Observations (EO scenes, spectral indices, SAR proxies)
- Model Runs (VMD0053 / VT0014 execution & spatial uncertainty)
- Typed Agricultural Activity Payloads
- Verification Dossiers & Cryptographic Seals
=============================================================================
"""

import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domains.agriculture.geospatial import (
    BoundarySource,
    LandUnitType,
    validate_geojson_polygon,
)
from app.domains.agriculture.soil.depth_classifier import (
    SoilComplianceClassification,
)


# ─── Land Unit Schemas ───

class LandUnitBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    code: Optional[str] = Field(None, max_length=50)
    unit_type: str = Field(default="FIELD")
    boundary_geojson: Dict[str, Any]
    boundary_source: str = Field(default="DECLARED")
    boundary_crs: str = Field(default="EPSG:4326")
    land_use_category: Optional[str] = None
    soil_type: Optional[str] = None
    slope_pct: Optional[float] = None
    is_active: bool = True
    properties: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("boundary_geojson")
    @classmethod
    def validate_boundary(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        is_valid, err = validate_geojson_polygon(v)
        if not is_valid:
            raise ValueError(f"Invalid land unit boundary GeoJSON: {err}")
        return v

    @field_validator("unit_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        valid_types = {t.value for t in LandUnitType}
        if v.upper() not in valid_types:
            raise ValueError(f"Invalid unit_type '{v}'. Permitted: {sorted(valid_types)}")
        return v.upper()

    @field_validator("boundary_source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        valid_sources = {s.value for s in BoundarySource}
        if v.upper() not in valid_sources:
            raise ValueError(f"Invalid boundary_source '{v}'. Permitted: {sorted(valid_sources)}")
        return v.upper()


class LandUnitCreate(LandUnitBase):
    project_id: uuid.UUID
    parent_id: Optional[uuid.UUID] = None


class LandUnitUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    code: Optional[str] = None
    unit_type: Optional[str] = None
    boundary_geojson: Optional[Dict[str, Any]] = None
    boundary_source: Optional[str] = None
    land_use_category: Optional[str] = None
    soil_type: Optional[str] = None
    slope_pct: Optional[float] = None
    is_active: Optional[bool] = None
    properties: Optional[Dict[str, Any]] = None

    @field_validator("boundary_geojson")
    @classmethod
    def validate_boundary(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if v is not None:
            is_valid, err = validate_geojson_polygon(v)
            if not is_valid:
                raise ValueError(f"Invalid land unit boundary GeoJSON: {err}")
        return v


class LandUnitResponse(LandUnitBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    project_id: uuid.UUID
    parent_id: Optional[uuid.UUID] = None
    area_ha: float
    perimeter_m: Optional[float] = None
    centroid_lat: Optional[float] = None
    centroid_lon: Optional[float] = None
    created_at: datetime
    updated_at: datetime


# ─── Soil Sample Schemas ───

class SoilSampleBase(BaseModel):
    sample_code: str = Field(..., min_length=1, max_length=50)
    sampling_date: date
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    depth_upper_cm: float = Field(default=0.0, ge=0.0)
    depth_lower_cm: float = Field(..., gt=0.0)
    bulk_density_g_cm3: Optional[float] = Field(None, gt=0.0, le=3.0)
    soc_stock_pct: float = Field(..., ge=0.0, le=100.0)
    total_organic_carbon_g_kg: Optional[float] = None
    coarse_fragments_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    ph: Optional[float] = Field(None, ge=1.0, le=14.0)
    electrical_conductivity_ds_m: Optional[float] = None
    texture_class: Optional[str] = None
    lab_method: str = Field(default="DRY_COMBUSTION")
    lab_name: Optional[str] = None
    lab_accreditation: Optional[str] = None
    is_model_calibration_source: bool = False
    is_model_validation_source: bool = False

    @field_validator("depth_lower_cm")
    @classmethod
    def validate_depth_order(cls, v: float, info) -> float:
        upper = info.data.get("depth_upper_cm", 0.0)
        if v <= upper:
            raise ValueError(f"depth_lower_cm ({v}) must be greater than depth_upper_cm ({upper})")
        return v


class SoilSampleCreate(SoilSampleBase):
    project_id: uuid.UUID
    land_unit_id: Optional[uuid.UUID] = None
    evidence_id: Optional[uuid.UUID] = None


class SoilSampleUpdate(BaseModel):
    sample_code: Optional[str] = None
    sampling_date: Optional[date] = None
    bulk_density_g_cm3: Optional[float] = None
    soc_stock_pct: Optional[float] = None
    coarse_fragments_pct: Optional[float] = None
    ph: Optional[float] = None
    electrical_conductivity_ds_m: Optional[float] = None
    texture_class: Optional[str] = None
    lab_method: Optional[str] = None
    lab_name: Optional[str] = None
    lab_accreditation: Optional[str] = None
    qa_status: Optional[str] = None


class SoilSampleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    project_id: uuid.UUID
    land_unit_id: Optional[uuid.UUID] = None
    sample_code: str
    sampling_date: date
    latitude: float
    longitude: float
    depth_upper_cm: float
    depth_lower_cm: float
    bulk_density_g_cm3: Optional[float] = None
    soc_stock_pct: float
    total_organic_carbon_g_kg: Optional[float] = None
    computed_soc_stock_t_c_ha: Optional[float] = None
    coarse_fragments_pct: float
    ph: Optional[float] = None
    electrical_conductivity_ds_m: Optional[float] = None
    texture_class: Optional[str] = None
    lab_method: str
    lab_name: Optional[str] = None
    lab_accreditation: Optional[str] = None
    qa_status: str
    compliance_classification: str
    compliance_notes: Optional[str] = None
    evidence_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime


# ─── Tree Observation Schemas ───

class TreeObservationBase(BaseModel):
    sampling_approach: str = Field(default="AREA_BASED")
    tag_number: Optional[str] = None
    species_scientific: str = Field(..., min_length=1, max_length=100)
    species_common: Optional[str] = None
    dbh_cm: float = Field(..., gt=0.0)
    height_m: Optional[float] = Field(None, gt=0.0)
    crown_diameter_m: Optional[float] = Field(None, gt=0.0)
    health_status: str = Field(default="HEALTHY")
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    measurement_date: date
    allometric_equation_id: Optional[str] = "CHAVE_2014_PANTROPICAL"
    wood_density_g_cm3: float = Field(default=0.60, gt=0.0)


class TreeObservationCreate(TreeObservationBase):
    project_id: uuid.UUID
    land_unit_id: uuid.UUID
    evidence_photo_hash: Optional[str] = None


class TreeObservationBatchCreate(BaseModel):
    project_id: uuid.UUID
    land_unit_id: uuid.UUID
    observations: List[TreeObservationBase]


class TreeObservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    project_id: uuid.UUID
    land_unit_id: uuid.UUID
    sampling_approach: str
    tag_number: Optional[str] = None
    species_scientific: str
    species_common: Optional[str] = None
    dbh_cm: float
    height_m: Optional[float] = None
    crown_diameter_m: Optional[float] = None
    health_status: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    measurement_date: date
    allometric_equation_id: Optional[str] = None
    derived_aboveground_biomass_kg: Optional[float] = None
    derived_belowground_biomass_kg: Optional[float] = None
    derived_carbon_stock_t_co2e: Optional[float] = None
    calculation_run_id: Optional[uuid.UUID] = None
    evidence_photo_hash: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ─── Satellite Observation Schemas ───

class SatelliteObservationCreate(BaseModel):
    project_id: uuid.UUID
    land_unit_id: Optional[uuid.UUID] = None
    provider: str
    scene_id: str
    acquisition_timestamp: datetime
    cloud_coverage_pct: Optional[float] = None
    spatial_resolution_m: float
    observation_type: str
    raw_band_uris: Dict[str, str] = Field(default_factory=dict)
    derived_indices: Dict[str, float] = Field(default_factory=dict)
    processing_level: str = "L2A"
    bounding_box: List[float]
    lineage_manifest: Dict[str, Any] = Field(default_factory=dict)


class SatelliteObservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    project_id: uuid.UUID
    land_unit_id: Optional[uuid.UUID] = None
    provider: str
    scene_id: str
    acquisition_timestamp: datetime
    cloud_coverage_pct: Optional[float] = None
    spatial_resolution_m: float
    observation_type: str
    raw_band_uris: Dict[str, Any]
    derived_indices: Dict[str, Any]
    provenance_hash: str
    processing_level: str
    lineage_manifest: Dict[str, Any]
    created_at: datetime


# ─── Model Run Schemas ───

class VT0014ModelRunRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    project_id: uuid.UUID
    covariate_features: List[str] = Field(default_factory=lambda: ["ndvi", "elevation", "slope"])
    prediction_grid_sample_size: int = Field(default=20, ge=5, le=100)
    model_algorithm: str = "RIDGE_REGRESSION"


class ModelRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: uuid.UUID
    organization_id: uuid.UUID
    project_id: uuid.UUID
    model_name: str
    model_type: str
    version: str
    run_timestamp: datetime
    status: str
    input_parameters: Dict[str, Any]
    input_dataset_hashes: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    uncertainty_metrics: Dict[str, Any]
    output_manifest: Dict[str, Any]
    provenance_hash: str
    created_at: datetime


# ─── Verification Dossier Schemas ───

class VerificationDossierResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    project_id: uuid.UUID
    project_name: str
    project_code: Optional[str]
    sector_code: str
    methodology_code: str
    methodology_version: str
    methodology_version_snapshot: Dict[str, Any]
    dossier_timestamp: datetime
    land_units_summary: Dict[str, Any]
    soil_inventory_summary: Dict[str, Any]
    tree_inventory_summary: Dict[str, Any]
    earth_observation_scenes: List[Dict[str, Any]]
    model_runs_summary: List[Dict[str, Any]]
    quantification_manifest: Dict[str, Any]
    manifest_sha256: str
    ledger_seal_status: str
    ledger_signature_id: Optional[str] = None


# ─── Agricultural Activity Data Schemas ───

class PlantingActivityPayload(BaseModel):
    crop_species: str
    crop_variety: Optional[str] = None
    seed_rate_kg_ha: Optional[float] = None
    planting_method: str = "DIRECT_SEEDING"
    is_cover_crop: bool = False


class HarvestActivityPayload(BaseModel):
    crop_species: str
    harvest_yield_t_ha: float
    residue_management: str = "RETAINED_ON_FIELD"  # RETAINED_ON_FIELD, REMOVED, BURNED
    residue_fraction_retained: float = Field(default=1.0, ge=0.0, le=1.0)


class FertilizerActivityPayload(BaseModel):
    fertilizer_type: str  # SYNTHETIC_NITROGEN, ORGANIC_MANURE, COMPOST
    product_name: Optional[str] = None
    nitrogen_content_pct: float = Field(..., ge=0.0, le=100.0)
    application_rate_kg_ha: float = Field(..., gt=0.0)
    application_method: str = "INCORPORATED"  # BROADCAST, INCORPORATED, DEEP_PLACEMENT, DRIP_FERTIGATION
    total_n_applied_kg: float


class IrrigationActivityPayload(BaseModel):
    irrigation_method: str  # DRIP, SPRINKLER, FLOOD, AWD_ALTERNATE_WET_DRY
    volume_m3_ha: Optional[float] = None
    water_table_depth_cm: Optional[float] = None
    field_drainage_duration_days: Optional[int] = None
