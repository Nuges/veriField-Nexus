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
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
    model_config = ConfigDict(protected_namespaces=())

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
    model_represents_30cm: bool = False
    extrapolation_method: Optional[str] = None

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
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

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
    model_represents_30cm: bool = False
    extrapolation_method: Optional[str] = None
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
    allometric_model_id: str = Field(default="CHAVE_2014_PANTROPICAL_AGB")
    allometric_equation_id: Optional[str] = None
    belowground_model_id: Optional[str] = None
    wood_density_g_cm3: float = Field(default=0.60, gt=0.0)
    wood_density_source: str = Field(default="Global Wood Density Database (Zanne et al. 2009)")


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
    belowground_model_id: Optional[str] = None
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


# ─── Stratum Schemas ───

VALID_STRATUM_TYPES = {
    "MANAGEMENT_PRACTICE",
    "SOIL_TYPE",
    "SOIL_TEXTURE",
    "AGRO_CLIMATIC_ZONE",
    "CROPPING_SYSTEM",
    "TOPOGRAPHY",
    "COMBINED",
}


class StratumBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = None
    stratum_type: str = Field(
        default="MANAGEMENT_PRACTICE",
        description="Analytical stratification dimension (MANAGEMENT_PRACTICE, SOIL_TYPE, SOIL_TEXTURE, AGRO_CLIMATIC_ZONE, CROPPING_SYSTEM, TOPOGRAPHY, COMBINED)",
    )
    area_ha: float = Field(default=0.0, ge=0.0)
    is_active: bool = True
    properties: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("stratum_type")
    @classmethod
    def validate_stratum_type(cls, v: str) -> str:
        if v.upper() not in VALID_STRATUM_TYPES:
            raise ValueError(f"Invalid stratum_type '{v}'. Permitted: {sorted(VALID_STRATUM_TYPES)}")
        return v.upper()


class StratumCreate(StratumBase):
    project_id: Optional[uuid.UUID] = None


class StratumUpdate(BaseModel):
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = None
    stratum_type: Optional[str] = None
    area_ha: Optional[float] = Field(None, ge=0.0)
    is_active: Optional[bool] = None
    properties: Optional[Dict[str, Any]] = None

    @field_validator("stratum_type")
    @classmethod
    def validate_stratum_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if v.upper() not in VALID_STRATUM_TYPES:
                raise ValueError(f"Invalid stratum_type '{v}'. Permitted: {sorted(VALID_STRATUM_TYPES)}")
            return v.upper()
        return v


class StratumMembershipItem(BaseModel):
    land_unit_id: uuid.UUID
    valid_from: date
    valid_to: Optional[date] = None
    status: str = Field(default="ACTIVE")
    properties: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_membership_dates(self) -> "StratumMembershipItem":
        if self.valid_to and self.valid_to < self.valid_from:
            raise ValueError(f"valid_to '{self.valid_to}' cannot precede valid_from '{self.valid_from}'.")
        return self


class StratumMembershipAddRequest(BaseModel):
    memberships: List[StratumMembershipItem]


class StratumResponse(StratumBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    project_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    member_count: int = 0
    land_unit_ids: List[uuid.UUID] = Field(default_factory=list)


# ─── Agriculture Management Record Schemas ───

class ManagementRecordBase(BaseModel):
    record_type: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="The management activity/practice (TILLAGE, FERTILIZER_SYNTHETIC, FERTILIZER_ORGANIC, CROP_ROTATION, COVER_CROP, IRRIGATION, RESIDUE_BURNING, GRAZING, OTHER)",
    )
    practice_category: str = Field(
        default="BASELINE",
        description="Temporal/crediting classification: BASELINE (historical pre-project practices) or PROJECT_ACTIVITY (crediting period project activities)",
    )
    event_date: date = Field(..., description="Date when management event occurred or began")
    end_date: Optional[date] = Field(None, description="Optional conclusion date for multi-day/ongoing events")
    data_source: str = Field(
        default="REPORTED",
        description="Provenance source (REPORTED, FIELD_INTERVIEW, DOCUMENT, FIELD_OBSERVATION, REMOTE_SENSING_CORROBORATED). REMOTE_SENSING_CORROBORATED is corroborative context only, not standalone algorithmic carbon/practice proof.",
    )
    details: Dict[str, Any] = Field(default_factory=dict)
    land_unit_id: Optional[uuid.UUID] = None
    evidence_id: Optional[uuid.UUID] = None
    corroboration: str = Field(
        default="NONE",
        description="Corroboration source (NONE, REMOTE_SENSING, TELEMETRY, DOCUMENTARY, FIELD_REOBSERVATION, OTHER). Remote sensing is corroborative context only.",
    )
    qa_status: str = Field(default="PENDING")

    @field_validator("record_type")
    @classmethod
    def validate_record_type(cls, v: str) -> str:
        valid_types = {
            "TILLAGE",
            "FERTILIZER_SYNTHETIC",
            "FERTILIZER_ORGANIC",
            "CROP_ROTATION",
            "COVER_CROP",
            "IRRIGATION",
            "RESIDUE_BURNING",
            "GRAZING",
            "OTHER",
        }
        if v.upper() not in valid_types:
            raise ValueError(f"Invalid record_type '{v}'. Permitted: {sorted(valid_types)}")
        return v.upper()

    @field_validator("practice_category")
    @classmethod
    def validate_practice_category(cls, v: str) -> str:
        valid_cats = {"BASELINE", "PROJECT_ACTIVITY"}
        if v.upper() not in valid_cats:
            raise ValueError(f"Invalid practice_category '{v}'. Permitted: {sorted(valid_cats)}")
        return v.upper()

    @field_validator("data_source")
    @classmethod
    def validate_data_source(cls, v: str) -> str:
        valid_sources = {
            "REPORTED",
            "FIELD_INTERVIEW",
            "DOCUMENT",
            "FIELD_OBSERVATION",
            "REMOTE_SENSING_CORROBORATED",
        }
        if v.upper() not in valid_sources:
            raise ValueError(f"Invalid data_source '{v}'. Permitted: {sorted(valid_sources)}")
        return v.upper()

    @field_validator("corroboration")
    @classmethod
    def validate_corroboration(cls, v: str) -> str:
        valid_corroborations = {
            "NONE",
            "REMOTE_SENSING",
            "TELEMETRY",
            "DOCUMENTARY",
            "FIELD_REOBSERVATION",
            "OTHER",
        }
        if v.upper() not in valid_corroborations:
            raise ValueError(f"Invalid corroboration '{v}'. Permitted: {sorted(valid_corroborations)}")
        return v.upper()

    @field_validator("qa_status")
    @classmethod
    def validate_qa_status(cls, v: str) -> str:
        valid_statuses = {"PENDING", "VERIFIED", "REJECTED"}
        if v.upper() not in valid_statuses:
            raise ValueError(f"Invalid qa_status '{v}'. Permitted: {sorted(valid_statuses)}")
        return v.upper()

    @field_validator("event_date")
    @classmethod
    def validate_event_date(cls, v: date) -> date:
        if v > date.today():
            raise ValueError(f"Management record event_date '{v}' cannot be in the future (today is {date.today()}).")
        return v

    @model_validator(mode="after")
    def validate_dates_order(self) -> "ManagementRecordBase":
        if self.end_date and self.end_date < self.event_date:
            raise ValueError(f"end_date '{self.end_date}' cannot precede event_date '{self.event_date}'.")
        return self


class ManagementRecordCreate(ManagementRecordBase):
    project_id: Optional[uuid.UUID] = None


class ManagementRecordUpdate(BaseModel):
    record_type: Optional[str] = None
    practice_category: Optional[str] = None
    event_date: Optional[date] = None
    end_date: Optional[date] = None
    data_source: Optional[str] = None
    corroboration: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    land_unit_id: Optional[uuid.UUID] = None
    evidence_id: Optional[uuid.UUID] = None
    qa_status: Optional[str] = None

    @field_validator("record_type")
    @classmethod
    def validate_record_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            valid_types = {
                "TILLAGE",
                "FERTILIZER_SYNTHETIC",
                "FERTILIZER_ORGANIC",
                "CROP_ROTATION",
                "COVER_CROP",
                "IRRIGATION",
                "RESIDUE_BURNING",
                "GRAZING",
                "OTHER",
            }
            if v.upper() not in valid_types:
                raise ValueError(f"Invalid record_type '{v}'. Permitted: {sorted(valid_types)}")
            return v.upper()
        return v

    @field_validator("practice_category")
    @classmethod
    def validate_practice_category(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            valid_cats = {"BASELINE", "PROJECT_ACTIVITY"}
            if v.upper() not in valid_cats:
                raise ValueError(f"Invalid practice_category '{v}'. Permitted: {sorted(valid_cats)}")
            return v.upper()
        return v

    @field_validator("data_source")
    @classmethod
    def validate_data_source(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            valid_sources = {
                "REPORTED",
                "FIELD_INTERVIEW",
                "DOCUMENT",
                "FIELD_OBSERVATION",
                "REMOTE_SENSING_CORROBORATED",
            }
            if v.upper() not in valid_sources:
                raise ValueError(f"Invalid data_source '{v}'. Permitted: {sorted(valid_sources)}")
            return v.upper()
        return v

    @field_validator("corroboration")
    @classmethod
    def validate_corroboration(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            valid_corroborations = {
                "NONE",
                "REMOTE_SENSING",
                "TELEMETRY",
                "DOCUMENTARY",
                "FIELD_REOBSERVATION",
                "OTHER",
            }
            if v.upper() not in valid_corroborations:
                raise ValueError(f"Invalid corroboration '{v}'. Permitted: {sorted(valid_corroborations)}")
            return v.upper()
        return v

    @field_validator("qa_status")
    @classmethod
    def validate_qa_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            valid_statuses = {"PENDING", "VERIFIED", "REJECTED"}
            if v.upper() not in valid_statuses:
                raise ValueError(f"Invalid qa_status '{v}'. Permitted: {sorted(valid_statuses)}")
            return v.upper()
        return v

    @field_validator("event_date")
    @classmethod
    def validate_event_date(cls, v: Optional[date]) -> Optional[date]:
        if v is not None and v > date.today():
            raise ValueError(f"Management record event_date '{v}' cannot be in the future (today is {date.today()}).")
        return v

    @model_validator(mode="after")
    def validate_dates_order(self) -> "ManagementRecordUpdate":
        if self.event_date and self.end_date and self.end_date < self.event_date:
            raise ValueError(f"end_date '{self.end_date}' cannot precede event_date '{self.event_date}'.")
        return self


class ManagementRecordResponse(ManagementRecordBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    project_id: uuid.UUID
    entered_by_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime


# ─── Project Foundation & Readiness Schemas ───

class LockMethodologyRequest(BaseModel):
    methodology_id: Optional[uuid.UUID] = None
    methodology_version_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None


class LinkBoundaryRequest(BaseModel):
    boundary_geojson: Dict[str, Any]
    source: str = Field(default="DECLARED")
    effective_date: Optional[date] = None
    reason: Optional[str] = "Initial Project Boundary"

    @field_validator("boundary_geojson")
    @classmethod
    def validate_boundary(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        is_valid, err = validate_geojson_polygon(v)
        if not is_valid:
            raise ValueError(f"Invalid boundary GeoJSON: {err}")
        return v


class ProjectFoundationResponse(BaseModel):
    project_id: uuid.UUID
    project_name: str
    project_code: Optional[str]
    sector: Dict[str, Any]
    methodology: Dict[str, Any]
    methodology_lock_status: str
    locked_methodology_snapshot: Optional[Dict[str, Any]] = None
    crediting_period: Dict[str, Any]
    baseline_parameters: Dict[str, Any]
    authoritative_boundary: Optional[Dict[str, Any]] = None
    land_units_count: int
    strata_count: int
    management_records_count: int


class ComponentReadinessDetail(BaseModel):
    status: str  # COMPLETE, INCOMPLETE, NEEDS_REVIEW, NOT_CONFIGURED
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class FoundationReadinessResponse(BaseModel):
    project_id: uuid.UUID
    overall_status: str  # COMPLETE, INCOMPLETE, NEEDS_REVIEW, NOT_CONFIGURED
    components: Dict[str, ComponentReadinessDetail]
    evaluated_at: datetime


# ─── Phase 2 Ground Sampling & Evidence Schemas ───

VALID_CAMPAIGN_PURPOSES = {
    "BASELINE_SOC_DETERMINATION",
    "MONITORING_ROUND",
    "STRATUM_VERIFICATION",
    "RESEARCH",
}

VALID_CAMPAIGN_STATUSES = {
    "DRAFT",
    "PLANNED",
    "LOCKED",
    "IN_FIELD",
    "COLLECTION_COMPLETE",
    "LAB_IN_PROGRESS",
    "QA_REVIEW",
    "COMPLETE",
    "CANCELLED",
}

VALID_DESIGN_METHODS = {
    "SIMPLE_RANDOM",
    "STRATIFIED_RANDOM",
    "SYSTEMATIC_GRID",
    "PURPOSIVE",
    "EXTERNAL_DESIGN",
    "MANUAL",
}

VALID_DESIGN_PROVENANCES = {
    "MANUAL",
    "IMPORTED",
    "EXTERNAL_DESIGN",
    "CONFIGURED_METHOD",
    "SYSTEM_GENERATED",
}

VALID_SAMPLE_STATUSES = {
    "PLANNED",
    "COLLECTED",
    "SEALED",
    "IN_TRANSIT",
    "RECEIVED_BY_LAB",
    "REJECTED_BY_LAB",
    "ANALYSIS_IN_PROGRESS",
    "ANALYZED",
    "QA_ACCEPTED",
    "QA_REJECTED",
    "ARCHIVED",
    "DISPOSED",
}

VALID_CUSTODY_EVENT_TYPES = {
    "COLLECTION",
    "SEALING",
    "TRANSFER",
    "TRANSPORT_DISPATCH",
    "CARRIER_PICKUP",
    "LAB_RECEIPT",
    "LAB_PROCESSING",
    "QA_REVIEW",
    "DISPOSAL",
}

VALID_LAB_METHODS = {
    "DRY_COMBUSTION",
    "WALKLEY_BLACK",
    "ELEMENTAL_ANALYZER_CN",
    "CORE_BULK_DENSITY",
    "HYDROMETER_TEXTURE",
    "PIPETTE_TEXTURE",
    "OTHER",
}

VALID_ANALYTES = {
    "SOC_CONCENTRATION",          # Canonical: Soil Organic Carbon concentration (mass fraction)
    "SOC_STOCK_PCT",              # Backward-compatible alias
    "TOTAL_ORGANIC_CARBON_G_KG",  # Backward-compatible alias
    "SOC_PCT",                    # Alias for SOC concentration
    "BULK_DENSITY_G_CM3",
    "COARSE_FRAGMENTS_PCT",
    "PH",
    "ELECTRICAL_CONDUCTIVITY_DS_M",
    "SAND_PCT",
    "SILT_PCT",
    "CLAY_PCT",
    "MOISTURE_PCT",
    "OTHER",
}


class SamplingCampaignCreate(BaseModel):
    campaign_code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=150)
    purpose: str = Field(default="BASELINE_SOC_DETERMINATION")
    baseline_or_monitoring_context: str = Field(default="BASELINE")
    planned_start_date: date
    planned_end_date: Optional[date] = None
    project_boundary_version_id: Optional[uuid.UUID] = None

    @field_validator("purpose")
    @classmethod
    def validate_purpose(cls, v: str) -> str:
        if v.upper() not in VALID_CAMPAIGN_PURPOSES:
            raise ValueError(f"Invalid campaign purpose '{v}'. Permitted: {sorted(VALID_CAMPAIGN_PURPOSES)}")
        return v.upper()

    @field_validator("baseline_or_monitoring_context")
    @classmethod
    def validate_context(cls, v: str) -> str:
        valid_contexts = {"BASELINE", "MONITORING"}
        if v.upper() not in valid_contexts:
            raise ValueError(f"Invalid context '{v}'. Permitted: {sorted(valid_contexts)}")
        return v.upper()

    @model_validator(mode="after")
    def validate_dates(self) -> "SamplingCampaignCreate":
        if self.planned_end_date and self.planned_end_date < self.planned_start_date:
            raise ValueError(f"planned_end_date '{self.planned_end_date}' cannot precede planned_start_date '{self.planned_start_date}'.")
        return self


class SamplingCampaignUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    purpose: Optional[str] = None
    baseline_or_monitoring_context: Optional[str] = None
    planned_start_date: Optional[date] = None
    planned_end_date: Optional[date] = None
    status: Optional[str] = None
    project_boundary_version_id: Optional[uuid.UUID] = None

    @field_validator("purpose")
    @classmethod
    def validate_purpose(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.upper() not in VALID_CAMPAIGN_PURPOSES:
            raise ValueError(f"Invalid campaign purpose '{v}'. Permitted: {sorted(VALID_CAMPAIGN_PURPOSES)}")
        return v.upper() if v else None

    @field_validator("baseline_or_monitoring_context")
    @classmethod
    def validate_context(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            valid_contexts = {"BASELINE", "MONITORING"}
            if v.upper() not in valid_contexts:
                raise ValueError(f"Invalid context '{v}'. Permitted: {sorted(valid_contexts)}")
            return v.upper()
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.upper() not in VALID_CAMPAIGN_STATUSES:
            raise ValueError(f"Invalid status '{v}'. Permitted: {sorted(VALID_CAMPAIGN_STATUSES)}")
        return v.upper() if v else None

    @model_validator(mode="after")
    def validate_dates(self) -> "SamplingCampaignUpdate":
        if self.planned_start_date and self.planned_end_date and self.planned_end_date < self.planned_start_date:
            raise ValueError("planned_end_date cannot precede planned_start_date.")
        return self


class SamplingCampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    project_id: uuid.UUID
    campaign_code: str
    name: str
    purpose: str
    baseline_or_monitoring_context: str
    planned_start_date: date
    planned_end_date: Optional[date] = None
    status: str
    methodology_lock_snapshot: Dict[str, Any] = Field(default_factory=dict)
    project_boundary_version_id: Optional[uuid.UUID] = None
    created_by_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime
    plan_versions_count: int = 0
    points_count: int = 0
    samples_count: int = 0


class SamplingPlanVersionCreate(BaseModel):
    effective_as_of_date: date
    sampling_design_method: str = Field(default="STRATIFIED_RANDOM")
    design_provenance: str = Field(default="MANUAL")
    notes: Optional[str] = None

    @field_validator("sampling_design_method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        if v.upper() not in VALID_DESIGN_METHODS:
            raise ValueError(f"Invalid sampling_design_method '{v}'. Permitted: {sorted(VALID_DESIGN_METHODS)}")
        return v.upper()

    @field_validator("design_provenance")
    @classmethod
    def validate_provenance(cls, v: str) -> str:
        if v.upper() not in VALID_DESIGN_PROVENANCES:
            raise ValueError(f"Invalid design_provenance '{v}'. Permitted: {sorted(VALID_DESIGN_PROVENANCES)}")
        return v.upper()


class SamplingPlanLockRequest(BaseModel):
    notes: Optional[str] = None


class SamplingPlanVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    project_id: uuid.UUID
    campaign_id: uuid.UUID
    version_number: int
    status: str
    effective_as_of_date: date
    stratum_membership_snapshot: Dict[str, Any] = Field(default_factory=dict)
    sampling_design_method: str
    design_provenance: str
    is_locked: bool
    locked_at: Optional[datetime] = None
    locked_by_id: Optional[uuid.UUID] = None
    plan_lock_snapshot: Dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = None
    created_by_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime
    points_count: int = 0


class SamplingPointCreate(BaseModel):
    point_code: str = Field(..., min_length=1, max_length=50)
    planned_lat: float = Field(..., ge=-90.0, le=90.0)
    planned_lon: float = Field(..., ge=-180.0, le=180.0)
    land_unit_id: uuid.UUID
    stratum_id: Optional[uuid.UUID] = None
    depth_from_cm: float = Field(default=0.0, ge=0.0)
    depth_to_cm: float = Field(default=30.0, gt=0.0)
    depth_class_label: Optional[str] = None
    sampling_purpose: str = Field(default="SOC_STOCK")
    replicate_group: Optional[str] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_depths(self) -> "SamplingPointCreate":
        if self.depth_to_cm <= self.depth_from_cm:
            raise ValueError(f"depth_to_cm '{self.depth_to_cm}' must be strictly greater than depth_from_cm '{self.depth_from_cm}'.")
        return self


class SamplingPointBatchCreate(BaseModel):
    points: List[SamplingPointCreate]


class SamplingPointResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    project_id: uuid.UUID
    campaign_id: uuid.UUID
    plan_version_id: uuid.UUID
    land_unit_id: uuid.UUID
    stratum_id: Optional[uuid.UUID] = None
    point_code: str
    planned_lat: float
    planned_lon: float
    depth_from_cm: float
    depth_to_cm: float
    depth_class_label: Optional[str] = None
    sampling_purpose: str
    replicate_group: Optional[str] = None
    status: str
    notes: Optional[str] = None
    created_at: datetime
    sample_id: Optional[uuid.UUID] = None
    sample_code: Optional[str] = None
    sample_status: Optional[str] = None


class SampleCollectionCreate(BaseModel):
    actual_lat: float = Field(..., ge=-90.0, le=90.0)
    actual_lon: float = Field(..., ge=-180.0, le=180.0)
    actual_depth_from_cm: float = Field(default=0.0, ge=0.0)
    actual_depth_to_cm: float = Field(default=30.0, gt=0.0)
    collection_timestamp: datetime
    collector_name: str = Field(..., min_length=1, max_length=100)
    sample_condition: str = Field(default="GOOD")
    deviation_reason: Optional[str] = None
    notes: Optional[str] = None
    photo_evidence_id: Optional[uuid.UUID] = None
    photo_hash: Optional[str] = None
    device_metadata: Dict[str, Any] = Field(default_factory=dict)
    idempotency_key: Optional[str] = None

    @field_validator("collection_timestamp")
    @classmethod
    def validate_collection_timestamp(cls, v: datetime) -> datetime:
        from datetime import timezone
        now = datetime.now(timezone.utc)
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        if v > now:
            raise ValueError("collection_timestamp cannot be in the future.")
        return v

    @model_validator(mode="after")
    def validate_depths(self) -> "SampleCollectionCreate":
        if self.actual_depth_to_cm <= self.actual_depth_from_cm:
            raise ValueError(f"actual_depth_to_cm '{self.actual_depth_to_cm}' must be strictly greater than actual_depth_from_cm '{self.actual_depth_from_cm}'.")
        return self


class SampleCollectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    physical_sample_id: uuid.UUID
    sampling_point_id: uuid.UUID
    actual_lat: float
    actual_lon: float
    deviation_distance_m: float
    deviation_reason: Optional[str] = None
    collection_timestamp: datetime
    collector_id: Optional[uuid.UUID] = None
    collector_name: str
    actual_depth_from_cm: float
    actual_depth_to_cm: float
    sample_condition: str
    notes: Optional[str] = None
    photo_evidence_id: Optional[uuid.UUID] = None
    photo_hash: Optional[str] = None
    device_metadata: Dict[str, Any] = Field(default_factory=dict)
    idempotency_key: Optional[str] = None
    sync_timestamp: Optional[datetime] = None
    server_received_at: Optional[datetime] = None
    created_at: datetime


class CustodyEventCreate(BaseModel):
    event_type: str = Field(..., min_length=1, max_length=50)
    event_timestamp: datetime
    custodian_name: str = Field(..., min_length=1, max_length=100)
    custodian_organization: str = Field(..., min_length=1, max_length=150)
    from_location: Optional[str] = None
    to_location: Optional[str] = None
    condition: str = Field(default="INTACT")
    seal_intact: bool = True
    seal_identifier: Optional[str] = None
    notes: Optional[str] = None
    evidence_id: Optional[uuid.UUID] = None

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        if v.upper() not in VALID_CUSTODY_EVENT_TYPES:
            raise ValueError(f"Invalid custody event_type '{v}'. Permitted: {sorted(VALID_CUSTODY_EVENT_TYPES)}")
        return v.upper()


class CustodyEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    physical_sample_id: uuid.UUID
    event_type: str
    event_timestamp: datetime
    custodian_id: Optional[uuid.UUID] = None
    custodian_name: str
    custodian_organization: str
    from_location: Optional[str] = None
    to_location: Optional[str] = None
    condition: str
    seal_intact: bool
    seal_identifier: Optional[str] = None
    notes: Optional[str] = None
    evidence_id: Optional[uuid.UUID] = None
    created_at: datetime


class LabReceiptCreate(BaseModel):
    laboratory_name: str = Field(..., min_length=1, max_length=150)
    laboratory_id_ref: Optional[str] = None
    received_at: datetime
    received_by_name: str = Field(..., min_length=1, max_length=100)
    condition_on_receipt: str = Field(default="ACCEPTABLE")
    seal_status: str = Field(default="SEALED_INTACT")
    intake_status: str = Field(default="ACCEPTED")
    rejection_reason: Optional[str] = None
    receipt_evidence_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None

    @field_validator("intake_status")
    @classmethod
    def validate_intake_status(cls, v: str) -> str:
        valid_intakes = {"ACCEPTED", "REJECTED"}
        if v.upper() not in valid_intakes:
            raise ValueError(f"Invalid intake_status '{v}'. Permitted: {sorted(valid_intakes)}")
        return v.upper()

    @model_validator(mode="after")
    def validate_rejection_reason(self) -> "LabReceiptCreate":
        if self.intake_status == "REJECTED" and not self.rejection_reason:
            raise ValueError("rejection_reason is required when intake_status is REJECTED.")
        return self


class LabReceiptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    physical_sample_id: uuid.UUID
    laboratory_name: str
    laboratory_id_ref: Optional[str] = None
    received_at: datetime
    received_by_name: str
    condition_on_receipt: str
    seal_status: str
    intake_status: str
    rejection_reason: Optional[str] = None
    receipt_evidence_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    created_at: datetime


class LabResultCreate(BaseModel):
    analyte: str = Field(..., min_length=1, max_length=50)
    raw_value: Decimal = Field(...)
    raw_unit: str = Field(..., min_length=1, max_length=30)
    normalized_value: Optional[Decimal] = None
    normalized_unit: Optional[str] = None
    normalization_method: Optional[str] = None
    normalization_version: Optional[str] = None
    detection_limit: Optional[Decimal] = None
    quantification_limit: Optional[Decimal] = None
    uncertainty_pct: Optional[Decimal] = None
    qualifier: str = Field(default="=")

    @field_validator("analyte")
    @classmethod
    def validate_analyte(cls, v: str) -> str:
        if v.upper() not in VALID_ANALYTES:
            raise ValueError(f"Invalid analyte '{v}'. Permitted: {sorted(VALID_ANALYTES)}")
        return v.upper()


class LabResultRevisionCreate(BaseModel):
    new_raw_value: Decimal = Field(...)
    new_raw_unit: str = Field(..., min_length=1, max_length=30)
    new_normalized_value: Optional[Decimal] = None
    new_normalized_unit: Optional[str] = None
    normalization_method: Optional[str] = None
    normalization_version: Optional[str] = None
    revision_reason: str = Field(..., min_length=5)
    detection_limit: Optional[Decimal] = None
    quantification_limit: Optional[Decimal] = None
    uncertainty_pct: Optional[Decimal] = None
    qualifier: str = Field(default="=")


class LabResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    analysis_id: uuid.UUID
    physical_sample_id: uuid.UUID
    analyte: str
    raw_value: Decimal
    raw_unit: str
    normalized_value: Optional[Decimal] = None
    normalized_unit: Optional[str] = None
    normalization_method: Optional[str] = None
    normalization_version: Optional[str] = None
    detection_limit: Optional[Decimal] = None
    quantification_limit: Optional[Decimal] = None
    uncertainty_pct: Optional[Decimal] = None
    qualifier: str
    is_superseded: bool
    superseded_by_id: Optional[uuid.UUID] = None
    supersedes_id: Optional[uuid.UUID] = None
    revision_reason: Optional[str] = None
    created_at: datetime


class LabAnalysisCreate(BaseModel):
    laboratory_name: str = Field(..., min_length=1, max_length=150)
    laboratory_accreditation: Optional[str] = None
    accreditation_status: str = Field(default="UNVERIFIED")
    accreditation_evidence_id: Optional[uuid.UUID] = None
    analysis_batch_id: Optional[str] = None
    analytical_method: str = Field(default="DRY_COMBUSTION")
    method_standard_code: Optional[str] = None
    analysis_date: date
    report_reference_number: Optional[str] = None
    analyst_name: Optional[str] = None
    evidence_id: Optional[uuid.UUID] = None
    results: List[LabResultCreate] = Field(default_factory=list)

    @field_validator("analytical_method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        if v.upper() not in VALID_LAB_METHODS:
            raise ValueError(f"Invalid analytical_method '{v}'. Permitted: {sorted(VALID_LAB_METHODS)}")
        return v.upper()

    @field_validator("accreditation_status")
    @classmethod
    def validate_accreditation(cls, v: str) -> str:
        valid_statuses = {"NOT_PROVIDED", "UNVERIFIED", "VERIFIED", "EXPIRED"}
        if v.upper() not in valid_statuses:
            raise ValueError(f"Invalid accreditation_status '{v}'. Permitted: {sorted(valid_statuses)}")
        return v.upper()


class LabAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    physical_sample_id: uuid.UUID
    laboratory_name: str
    laboratory_accreditation: Optional[str] = None
    accreditation_status: str = "UNVERIFIED"
    accreditation_evidence_id: Optional[uuid.UUID] = None
    analysis_batch_id: Optional[str] = None
    analytical_method: str
    method_standard_code: Optional[str] = None
    analysis_date: date
    report_reference_number: Optional[str] = None
    analyst_name: Optional[str] = None
    qa_status: str
    evidence_id: Optional[uuid.UUID] = None
    created_at: datetime
    results: List[LabResultResponse] = Field(default_factory=list)


class SampleQAReviewCreate(BaseModel):
    reviewer_name: str = Field(..., min_length=1, max_length=100)
    review_date: Optional[datetime] = None
    overall_qa_status: str = Field(default="ACCEPTED")
    location_verified: bool = True
    deviation_acceptable: bool = True
    depth_valid: bool = True
    custody_complete: bool = True
    lab_receipt_verified: bool = True
    required_assays_present: bool = True
    notes: Optional[str] = None

    @field_validator("overall_qa_status")
    @classmethod
    def validate_qa_status(cls, v: str) -> str:
        valid_statuses = {"PENDING", "ACCEPTED", "REJECTED", "FLAGGED"}
        if v.upper() not in valid_statuses:
            raise ValueError(f"Invalid overall_qa_status '{v}'. Permitted: {sorted(valid_statuses)}")
        return v.upper()


class SampleQAReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    physical_sample_id: uuid.UUID
    reviewer_id: Optional[uuid.UUID] = None
    reviewer_name: str
    review_date: datetime
    overall_qa_status: str
    location_verified: bool
    deviation_acceptable: bool
    depth_valid: bool
    custody_complete: bool
    lab_receipt_verified: bool
    required_assays_present: bool
    notes: Optional[str] = None
    created_at: datetime


class PhysicalSampleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    project_id: uuid.UUID
    campaign_id: uuid.UUID
    plan_version_id: Optional[uuid.UUID] = None
    sampling_point_id: uuid.UUID
    land_unit_id: uuid.UUID
    stratum_id: Optional[uuid.UUID] = None
    sample_code: str
    status: str
    qr_barcode_code: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    point_code: Optional[str] = None
    planned_lat: Optional[float] = None
    planned_lon: Optional[float] = None
    collection_event: Optional[SampleCollectionResponse] = None
    custody_events: List[CustodyEventResponse] = Field(default_factory=list)
    laboratory_receipt: Optional[LabReceiptResponse] = None
    laboratory_analyses: List[LabAnalysisResponse] = Field(default_factory=list)
    qa_review: Optional[SampleQAReviewResponse] = None


class GroundEvidenceComponentDetail(BaseModel):
    status: str  # COMPLETE, INCOMPLETE, NEEDS_REVIEW, NOT_CONFIGURED
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class GroundEvidenceReadinessResponse(BaseModel):
    project_id: uuid.UUID
    overall_status: str  # COMPLETE, INCOMPLETE, NEEDS_REVIEW, NOT_CONFIGURED
    components: Dict[str, GroundEvidenceComponentDetail]
    evaluated_at: datetime


# ─── Phase 3A: Quantification Readiness & Calculation Input Contract Schemas ───

class ExclusionReasonCode(str, Enum):
    QA_NOT_ACCEPTED = "QA_NOT_ACCEPTED"
    LAB_RESULT_SUPERSEDED = "LAB_RESULT_SUPERSEDED"
    MISSING_BULK_DENSITY = "MISSING_BULK_DENSITY"
    MISSING_COARSE_FRAGMENT_DATA = "MISSING_COARSE_FRAGMENT_DATA"
    DEPTH_MISMATCH = "DEPTH_MISMATCH"
    BROKEN_CUSTODY = "BROKEN_CUSTODY"
    OUTSIDE_MONITORING_PERIOD = "OUTSIDE_MONITORING_PERIOD"
    WRONG_LAND_UNIT = "WRONG_LAND_UNIT"
    WRONG_METHODOLOGY_CONTEXT = "WRONG_METHODOLOGY_CONTEXT"
    PLAN_NOT_LOCKED = "PLAN_NOT_LOCKED"
    UNCONVERTIBLE_UNIT = "UNCONVERTIBLE_UNIT"
    SAMPLE_NOT_COLLECTED = "SAMPLE_NOT_COLLECTED"
    RECEIPT_REJECTED = "RECEIPT_REJECTED"


class DepthAlignmentStatus(str, Enum):
    MATCH = "MATCH"
    PARTIAL_COVERAGE = "PARTIAL_COVERAGE"
    OVERLAPPING_INTERVAL = "OVERLAPPING_INTERVAL"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class QuantificationMeasurementItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organization_id: uuid.UUID
    project_id: uuid.UUID
    methodology_id: Optional[uuid.UUID] = None
    methodology_version_id: Optional[uuid.UUID] = None
    methodology_code: str
    methodology_version: str
    rule_set_version: str
    monitoring_context: str  # BASELINE or MONITORING
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    project_boundary_version_id: Optional[uuid.UUID] = None

    land_unit_id: uuid.UUID
    land_unit_code: str
    stratum_id: Optional[uuid.UUID] = None
    stratum_code: Optional[str] = None
    stratum_membership_as_of: Optional[date] = None

    sampling_campaign_id: uuid.UUID
    sampling_campaign_code: str
    sampling_plan_version_id: Optional[uuid.UUID] = None
    sampling_plan_version: Optional[int] = None
    sampling_plan_locked: bool

    physical_sample_id: uuid.UUID
    sample_code: str
    sampling_date: date
    actual_depth_from_cm: float
    actual_depth_to_cm: float
    depth_alignment_status: str  # MATCH, PARTIAL_COVERAGE, OVERLAPPING_INTERVAL, OUT_OF_SCOPE, NEEDS_REVIEW
    sample_qa_status: str        # ACCEPTED

    laboratory_analysis_id: uuid.UUID
    laboratory_name: str
    analytical_method: str
    analysis_qa_status: str      # VERIFIED
    analysis_date: date

    laboratory_result_id: uuid.UUID
    analyte: str                 # SOC_CONCENTRATION
    raw_value: float
    raw_unit: str
    normalized_value: float
    normalized_unit: str         # g/kg
    normalization_method: str
    normalization_version: str
    provenance_class: str = "MEASURED"

    bulk_density_result_id: Optional[uuid.UUID] = None
    bulk_density_raw_value: Optional[float] = None
    bulk_density_raw_unit: Optional[str] = None
    bulk_density_normalized_value: Optional[float] = None
    bulk_density_normalized_unit: Optional[str] = None
    bulk_density_status: str     # PRESENT, MISSING, NOT_APPLICABLE

    coarse_fragments_result_id: Optional[uuid.UUID] = None
    coarse_fragments_pct: Optional[float] = None
    coarse_fragments_status: str # MEASURED_ZERO, MEASURED, NOT_MEASURED, NOT_APPLICABLE

    uncertainty_pct: Optional[float] = None
    uncertainty_inputs: Dict[str, Any] = Field(default_factory=dict)
    evidence_ids: List[uuid.UUID] = Field(default_factory=list)


class ExcludedMeasurementItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    physical_sample_id: uuid.UUID
    sample_code: str
    land_unit_id: Optional[uuid.UUID] = None
    land_unit_code: Optional[str] = None
    stratum_id: Optional[uuid.UUID] = None
    stratum_code: Optional[str] = None
    sampling_date: Optional[date] = None
    actual_depth_from_cm: Optional[float] = None
    actual_depth_to_cm: Optional[float] = None
    analyte: Optional[str] = None
    raw_value: Optional[float] = None
    raw_unit: Optional[str] = None
    exclusion_reasons: List[str]
    exclusion_details: Dict[str, Any] = Field(default_factory=dict)


class EligibleMeasurementSetResponse(BaseModel):
    project_id: uuid.UUID
    quantification_approach: str = "DIRECT_MEASUREMENT"
    total_candidates: int
    total_eligible: int
    total_excluded: int
    baseline_measurements: List[QuantificationMeasurementItem]
    project_measurements: List[QuantificationMeasurementItem]
    excluded_measurements: List[ExcludedMeasurementItem]


class QuantificationReadinessDimension(BaseModel):
    status: str  # COMPLETE, INCOMPLETE, NEEDS_REVIEW, NOT_CONFIGURED, NOT_APPLICABLE
    requirement: str = "REQUIRED"  # REQUIRED, OPTIONAL, NOT_APPLICABLE
    blocking: bool = True
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class QuantificationReadinessResponse(BaseModel):
    project_id: uuid.UUID
    overall_status: str  # COMPLETE, INCOMPLETE, NEEDS_REVIEW, NOT_CONFIGURED
    quantification_approach: str = "DIRECT_MEASUREMENT"
    methodology_code: str
    methodology_version: str
    dimensions: Dict[str, QuantificationReadinessDimension]
    total_eligible_measurements: int
    total_excluded_measurements: int
    evaluated_at: str


class QuantificationInputSnapshotCreate(BaseModel):
    context: str = Field(default="MONITORING")  # BASELINE, MONITORING, COMBINED
    sampling_campaign_id: Optional[uuid.UUID] = None
    status: Optional[str] = Field(default="LOCKED")  # PREVIEW, LOCKED
    source_evidence_ids: Optional[List[uuid.UUID]] = None
    notes: Optional[str] = None


class QuantificationInputSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    project_id: uuid.UUID
    snapshot_code: str
    status: str
    context: str
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    methodology_code: str
    methodology_version: str
    rule_set_version: str
    project_boundary_version_id: Optional[uuid.UUID] = None
    sampling_campaign_id: Optional[uuid.UUID] = None
    snapshot_hash: str
    is_locked: bool
    locked_at: Optional[datetime] = None
    locked_by_id: Optional[uuid.UUID] = None
    created_by_id: Optional[uuid.UUID] = None
    total_eligible_measurements: int
    total_excluded_measurements: int
    readiness_summary: Dict[str, Any]
    input_package: Dict[str, Any]
    source_evidence_ids: List[Any]
    notes: Optional[str] = None
    created_at: datetime


# =============================================================================
# LABORATORY BULK DATA IMPORT SCHEMAS
# =============================================================================

class ColumnMappingConfig(BaseModel):
    sample_code_column: str = "sample_code"
    analyte_column: Optional[str] = "analyte"
    analyte_constant: Optional[str] = None
    value_column: str = "raw_value"
    unit_column: Optional[str] = "raw_unit"
    unit_constant: Optional[str] = None
    depth_from_column: Optional[str] = "depth_from_cm"
    depth_to_column: Optional[str] = "depth_to_cm"
    analysis_date_column: Optional[str] = "analysis_date"
    method_column: Optional[str] = "method"
    lab_sample_id_column: Optional[str] = "lab_sample_id"
    notes_column: Optional[str] = "notes"
    sheet_name: Optional[str] = None
    skip_rows: int = 0


class LaboratoryImportValidateRequest(BaseModel):
    mapping_config: Optional[Dict[str, Any]] = None
    laboratory_name: Optional[str] = None
    sampling_campaign_id: Optional[uuid.UUID] = None


class LaboratoryImportCommitRequest(BaseModel):
    import_valid_only: bool = False
    laboratory_name: Optional[str] = None
    notes: Optional[str] = None
    import_as_revision: bool = False
    revision_reason: Optional[str] = None


class LaboratoryImportRowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    import_batch_id: uuid.UUID
    organization_id: uuid.UUID
    project_id: uuid.UUID
    source_sheet_name: Optional[str] = None
    source_row_number: int
    raw_row_payload: Dict[str, Any]
    mapped_payload: Dict[str, Any]
    validation_status: str
    validation_messages: List[Dict[str, Any]]
    matched_sample_id: Optional[uuid.UUID] = None
    matched_sample_code: Optional[str] = None
    canonical_analyte: Optional[str] = None
    raw_value: Optional[float] = None
    raw_unit: Optional[str] = None
    normalized_value: Optional[float] = None
    normalized_unit: Optional[str] = None
    resulting_lab_result_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime


class LaboratoryImportBatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    project_id: uuid.UUID
    sampling_campaign_id: Optional[uuid.UUID] = None
    laboratory_name: Optional[str] = None
    original_filename: str
    file_type: str
    file_size_bytes: int
    file_sha256: str
    evidence_id: Optional[uuid.UUID] = None
    status: str
    source_type: str
    uploaded_by: Optional[uuid.UUID] = None
    uploaded_at: datetime
    mapping_version: str
    mapping_config: Dict[str, Any]
    total_rows: int
    valid_rows: int
    warning_rows: int
    error_rows: int
    imported_rows: int
    skipped_rows: int
    error_summary: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class LaboratoryImportValidationResponse(BaseModel):
    batch_id: uuid.UUID
    status: str
    total_rows: int
    valid_rows: int
    warning_rows: int
    error_rows: int
    can_commit: bool
    preview_rows: List[LaboratoryImportRowResponse]
    error_summary: List[Dict[str, Any]]


class LaboratoryImportCommitResponse(BaseModel):
    batch_id: uuid.UUID
    status: str
    imported_rows: int
    skipped_rows: int
    analyses_created: int
    results_created: int
    samples_analyzed: int
    message: str


# =============================================================================
# PHASE 3B-0: METHODOLOGY PREREQUISITE SCHEMAS
# =============================================================================

class PrerequisiteDimensionDetail(BaseModel):
    status: str
    requirement: str
    blocking: bool
    finding_type: str
    reason_code: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class PrerequisiteEvaluationResponse(BaseModel):
    project_id: uuid.UUID
    overall_status: str
    methodology_code: str
    methodology_version: str
    corrections_clarifications_version: str
    rule_set_version: str
    vcs_standard_version: str
    governing_vcs_standard: Optional[str] = None
    v5_template_variant: Optional[str] = None
    project_description_template: Optional[str] = None
    dimensions: Dict[str, PrerequisiteDimensionDetail]
    blocking_reasons: List[str]
    advisory_notes: List[str]
    total_dimensions: int
    evaluated_at: str
    evaluation_hash: str


class PrerequisiteEvaluateRequest(BaseModel):
    snapshot_id: Optional[uuid.UUID] = None
    project_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    run_power_analysis: bool = False
    target_mdd: Optional[float] = None
    submission_date: Optional[Union[date, str]] = None
    early_adoption_mode: Optional[str] = None
    as_of_date: Optional[Union[date, str]] = None


class PrerequisiteLockRequest(BaseModel):
    snapshot_id: Optional[uuid.UUID] = None
    project_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    run_power_analysis: bool = False
    target_mdd: Optional[float] = None
    submission_date: Optional[Union[date, str]] = None
    early_adoption_mode: Optional[str] = None
    as_of_date: Optional[Union[date, str]] = None


class AgriculturePrerequisiteAssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    project_id: uuid.UUID
    snapshot_id: Optional[uuid.UUID] = None
    assessment_code: str
    version: int
    status: str
    overall_readiness: str
    methodology_code: str
    methodology_version: str
    corrections_clarifications_version: str
    rule_set_version: str
    vcs_standard_version: str
    governing_vcs_standard: Optional[str] = None
    v5_template_variant: Optional[str] = None
    project_description_template: Optional[str] = None
    vcs_resolution_metadata: Dict[str, Any]
    quantification_route_map: Dict[str, Any]
    esm_input_dossier: Dict[str, Any]
    sampling_design_assessment: Dict[str, Any]
    uncertainty_input_readiness: Dict[str, Any]
    baseline_monitoring_pairing: Dict[str, Any]
    dimensions: Dict[str, Any]
    blocking_reasons: List[str]
    advisory_notes: List[str]
    assessment_hash: str
    is_locked: bool
    locked_at: Optional[datetime] = None
    locked_by_id: Optional[uuid.UUID] = None
    created_by_id: Optional[uuid.UUID] = None
    superseded_by_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# =============================================================================
# PHASE 3B-1: SOC STOCK & EQUIVALENT SOIL MASS SCHEMAS
# =============================================================================

class AgricultureSOCLayerResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    stock_result_id: uuid.UUID
    sample_id: Optional[uuid.UUID] = None
    layer_index: int
    depth_upper_cm: Decimal
    depth_lower_cm: Decimal
    layer_thickness_cm: Decimal
    bulk_density_g_cm3: Optional[Decimal] = None
    bulk_density_provenance: str
    coarse_fragment_fraction: Optional[Decimal] = None
    coarse_fragment_provenance: str
    soc_concentration_g_kg: Decimal
    laboratory_result_id: Optional[uuid.UUID] = None
    layer_soil_mass_t_ha: Decimal
    layer_soc_mass_t_c_ha: Decimal
    cumulative_soil_mass_t_ha: Decimal
    cumulative_soc_mass_t_c_ha: Decimal
    fraction_in_reference_mass: Optional[Decimal] = None
    included_soil_mass_t_ha: Optional[Decimal] = None
    included_soc_mass_t_c_ha: Optional[Decimal] = None
    created_at: datetime


class AgricultureSOCStockResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    project_id: uuid.UUID
    quantification_unit_id: Optional[uuid.UUID] = None
    stratum_id: Optional[uuid.UUID] = None
    sampling_point_id: Optional[uuid.UUID] = None
    campaign_id: Optional[uuid.UUID] = None
    prerequisite_assessment_id: uuid.UUID
    input_snapshot_id: Optional[uuid.UUID] = None
    stock_snapshot_id: Optional[uuid.UUID] = None
    result_code: str
    measurement_period_type: str
    aggregation_level: str
    methodology_version: str
    corrections_clarifications_version: str
    calculation_engine_version: str
    esm_algorithm: str
    reference_soil_mass_t_ha: Decimal
    reference_depth_cm: Decimal
    equivalent_depth_cm: Optional[Decimal] = None
    total_sampled_soil_mass_t_ha: Optional[Decimal] = None
    max_sampled_depth_cm: Optional[Decimal] = None
    soc_stock_t_c_per_ha: Decimal
    unadjusted_stock_t_c_per_ha: Optional[Decimal] = None
    shallow_soil_exception_applied: bool
    depth_sufficiency_status: str
    area_ha: Optional[Decimal] = None
    sample_count: int
    strata_weights: Dict[str, Any] = Field(default_factory=dict)
    component_breakdown: Dict[str, Any] = Field(default_factory=dict)
    result_status: str
    calculation_hash: str
    input_snapshot_hash: str
    created_by_id: Optional[uuid.UUID] = None
    superseded_by_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    layers: List[AgricultureSOCLayerResultResponse] = Field(default_factory=list)


class AgricultureSOCStockSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    project_id: uuid.UUID
    prerequisite_assessment_id: uuid.UUID
    snapshot_code: str
    measurement_period_type: str
    snapshot_payload: Dict[str, Any]
    snapshot_hash: str
    created_at: datetime


class SOCStockEvaluateRequest(BaseModel):
    prerequisite_assessment_id: Optional[uuid.UUID] = None
    snapshot_id: Optional[uuid.UUID] = None
    measurement_period_type: Optional[str] = "MONITORING"
    reference_depth_cm: Optional[Decimal] = Decimal("30.00")
    reference_soil_mass_t_ha: Optional[Decimal] = None
    esm_algorithm: Optional[str] = "LAYER_MASS_PROPORTIONING"
    notes: Optional[str] = None


class SOCStockCalculateRequest(BaseModel):
    prerequisite_assessment_id: uuid.UUID
    snapshot_id: Optional[uuid.UUID] = None
    measurement_period_type: str = "MONITORING"
    reference_depth_cm: Decimal = Decimal("30.00")
    reference_soil_mass_t_ha: Optional[Decimal] = None
    esm_algorithm: str = "LAYER_MASS_PROPORTIONING"
    notes: Optional[str] = None


class SOCStockEvaluationResponse(BaseModel):
    project_id: uuid.UUID
    prerequisite_assessment_id: uuid.UUID
    measurement_period_type: str
    status: str  # EVALUATED, BLOCKED
    esm_algorithm: str
    reference_soil_mass_t_ha: Decimal
    reference_depth_cm: Decimal
    sample_point_results: List[Dict[str, Any]]
    stratum_results: List[Dict[str, Any]]
    project_soc_stock_t_c_per_ha: Optional[Decimal] = None
    total_area_ha: Optional[Decimal] = None
    blocking_reasons: List[str] = Field(default_factory=list)
    advisory_notes: List[str] = Field(default_factory=list)
    evaluation_hash: str


# =============================================================================
# PHASE 3B-2: SOC STOCK CHANGE & UNCERTAINTY QUANTIFICATION SCHEMAS
# =============================================================================

class AgricultureSOCChangeResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    project_id: uuid.UUID
    baseline_stock_result_id: uuid.UUID
    monitoring_stock_result_id: uuid.UUID
    prerequisite_assessment_id: uuid.UUID
    result_code: str
    methodology_version: str
    corrections_clarifications_version: str
    calculation_engine_version: str
    quantification_approach: str
    t_start: datetime
    t_final: datetime
    elapsed_years: Decimal
    esm_algorithm: str
    reference_soil_mass_t_ha: Decimal
    reference_depth_cm: Decimal
    total_project_area_ha: Decimal
    baseline_mean_soc_t_c_per_ha: Decimal
    monitoring_mean_soc_t_c_per_ha: Decimal
    delta_soc_project_t_c_ha_yr: Decimal
    delta_soc_baseline_t_c_ha_yr: Decimal
    delta_soc_net_t_c_ha_yr: Decimal
    delta_co2_project_tco2e_ha_yr: Decimal
    delta_co2_baseline_tco2e_ha_yr: Decimal
    delta_co2_net_tco2e_ha_yr: Decimal
    total_project_delta_co2_tco2e_yr: Decimal
    total_baseline_delta_co2_tco2e_yr: Decimal
    total_net_delta_co2_tco2e_yr: Decimal
    baseline_soc_change_tco2e_yr: Decimal
    project_soc_change_tco2e_yr: Decimal
    qa2_net_soc_effect_tco2e_yr: Decimal
    uncertainty_adjusted_soc_effect_tco2e_yr: Decimal
    sign_indicator: int
    eq44_eq45_status: str
    df_estimator: str
    co2_to_c_ratio: Decimal
    variance_delta_soc_project: Decimal
    variance_delta_soc_baseline: Decimal
    total_variance_delta_soc: Decimal
    standard_error_delta_soc_t_c_ha_yr: Decimal
    standard_error_tco2e_yr: Decimal
    degrees_of_freedom: int
    student_t_value_0667: Decimal
    relative_uncertainty_pct: Decimal
    allowable_uncertainty_pct: Decimal
    uncertainty_deduction_pct: Decimal
    uncertainty_deduction_fraction: Decimal
    adjusted_net_delta_co2_tco2e_yr: Decimal
    measurement_error_status: str
    measurement_error_router: str
    strata_results: List[Dict[str, Any]] = Field(default_factory=list)
    component_breakdown: Dict[str, Any] = Field(default_factory=dict)
    carbon_accounting_status: str
    ledger_status: str
    result_status: str
    calculation_hash: str
    input_snapshot_hash: str
    created_by_id: Optional[uuid.UUID] = None
    superseded_by_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class SOCChangeEvaluateRequest(BaseModel):
    baseline_stock_result_id: uuid.UUID
    monitoring_stock_result_id: uuid.UUID
    prerequisite_assessment_id: Optional[uuid.UUID] = None
    laboratory_method: Optional[str] = "DRY_COMBUSTION"
    lab_qa_verified: Optional[bool] = True
    active_lab_proficiency: Optional[bool] = True
    notes: Optional[str] = None


class SOCChangeFinalizeRequest(BaseModel):
    baseline_stock_result_id: uuid.UUID
    monitoring_stock_result_id: uuid.UUID
    prerequisite_assessment_id: uuid.UUID
    laboratory_method: Optional[str] = "DRY_COMBUSTION"
    lab_qa_verified: Optional[bool] = True
    active_lab_proficiency: Optional[bool] = True
    notes: Optional[str] = None


class SOCChangeEvaluationResponse(BaseModel):
    project_id: uuid.UUID
    status: str  # EVALUATED, BLOCKED
    baseline_stock_result_id: uuid.UUID
    monitoring_stock_result_id: uuid.UUID
    elapsed_years: Decimal
    t_start: datetime
    t_final: datetime
    total_project_area_ha: Decimal
    delta_soc_project_t_c_ha_yr: Decimal
    delta_soc_baseline_t_c_ha_yr: Decimal
    delta_soc_net_t_c_ha_yr: Decimal
    delta_co2_net_tco2e_ha_yr: Decimal
    total_net_delta_co2_tco2e_yr: Decimal
    baseline_soc_change_tco2e_yr: Optional[Decimal] = None
    project_soc_change_tco2e_yr: Optional[Decimal] = None
    qa2_net_soc_effect_tco2e_yr: Optional[Decimal] = None
    uncertainty_adjusted_soc_effect_tco2e_yr: Optional[Decimal] = None
    sign_indicator: Optional[int] = 1
    eq44_eq45_status: Optional[str] = "PARTIALLY_CONFIGURED_SOC_ONLY"
    df_estimator: Optional[str] = "DEFAULT_STRATIFIED_RANDOM_DF_ESTIMATOR"
    adjusted_net_delta_co2_tco2e_yr: Decimal
    degrees_of_freedom: int
    student_t_value_0667: Decimal
    relative_uncertainty_pct: Decimal
    uncertainty_deduction_pct: Decimal
    uncertainty_deduction_fraction: Decimal
    uncertainty_status: str
    measurement_error_status: str
    strata_results: List[Dict[str, Any]]
    blocking_reasons: List[str] = Field(default_factory=list)
    evaluation_hash: str


# =============================================================================
# PHASE 3B-3: NET GHG REDUCTIONS & REMOVALS + VCU READINESS SCHEMAS
# =============================================================================

class AgricultureVintageGHGResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    net_ghg_result_id: uuid.UUID
    vintage_year: int
    total_baseline_emissions_tco2e: Decimal
    total_project_emissions_tco2e: Decimal
    total_emission_reductions_from_sources_tco2e: Decimal
    eq44_baseline_total_carbon_stock_change_tco2e: Decimal
    eq45_project_total_carbon_stock_change_tco2e: Decimal
    gross_reductions_er_tco2e: Decimal
    gross_removals_cr_tco2e: Decimal
    total_leakage_tco2e: Decimal
    leakage_allocation_er_lker_tco2e: Decimal
    leakage_allocation_cr_lkcr_tco2e: Decimal
    net_reductions_ernet_tco2e: Decimal
    net_removals_crnet_tco2e: Decimal
    total_net_ghg_errnet_tco2e: Decimal
    buffer_deduction_reductions_tco2e: Optional[Decimal] = None
    buffer_deduction_removals_tco2e: Optional[Decimal] = None
    total_buffer_deduction_tco2e: Optional[Decimal] = None
    internal_vcu_eligible_reductions_tco2e: Optional[Decimal] = None
    internal_vcu_eligible_removals_tco2e: Optional[Decimal] = None
    internal_vcu_eligible_total_tco2e: Optional[Decimal] = None
    vintage_details: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class AgricultureNetGHGResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    project_id: uuid.UUID
    soc_change_result_id: Optional[uuid.UUID] = None
    prerequisite_assessment_id: uuid.UUID
    result_code: str
    methodology_version: str
    corrections_clarifications_version: str
    calculation_engine_version: str
    ruleset_version: str
    verification_period_start: datetime
    verification_period_end: datetime
    elapsed_years: Decimal
    applicability_matrix: Dict[str, Any] = Field(default_factory=dict)
    total_baseline_emissions_tco2e: Decimal
    total_project_emissions_tco2e: Decimal
    total_emission_reductions_from_sources_tco2e: Decimal
    eq44_baseline_total_carbon_stock_change_tco2e: Decimal
    eq45_project_total_carbon_stock_change_tco2e: Decimal
    eq44_eq45_status: str
    gross_reductions_er_tco2e: Decimal
    gross_removals_cr_tco2e: Decimal
    total_leakage_tco2e: Decimal
    leakage_allocation_er_lker_tco2e: Decimal
    leakage_allocation_cr_lkcr_tco2e: Decimal
    net_reductions_ernet_tco2e: Decimal
    net_removals_crnet_tco2e: Decimal
    total_net_ghg_errnet_tco2e: Decimal
    npr_rating_pct: Optional[Decimal] = None
    risk_assessment_id: Optional[str] = None
    buffer_deduction_reductions_tco2e: Optional[Decimal] = None
    buffer_deduction_removals_tco2e: Optional[Decimal] = None
    total_buffer_deduction_tco2e: Optional[Decimal] = None
    internal_vcu_eligible_reductions_tco2e: Optional[Decimal] = None
    internal_vcu_eligible_removals_tco2e: Optional[Decimal] = None
    internal_vcu_eligible_total_tco2e: Optional[Decimal] = None
    vcu_readiness_status: str
    internal_mrv_status: str
    vvb_status: str
    registry_status: str
    ledger_status: str
    result_status: str
    calculation_hash: str
    input_snapshot_hash: str
    created_by_id: Optional[uuid.UUID] = None
    superseded_by_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    component_breakdown: Dict[str, Any] = Field(default_factory=dict)
    vintages: List[AgricultureVintageGHGResultResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class NetGHGEvaluateRequest(BaseModel):
    soc_change_result_id: Optional[uuid.UUID] = None
    prerequisite_assessment_id: Optional[uuid.UUID] = None
    verification_period_start: Optional[date] = None
    verification_period_end: Optional[date] = None
    applicability_overrides: Optional[List[Dict[str, Any]]] = None
    fossil_fuel_activities_bsl: Optional[List[Dict[str, Any]]] = None
    fossil_fuel_activities_wp: Optional[List[Dict[str, Any]]] = None
    liming_activity_bsl: Optional[Dict[str, Any]] = None
    liming_activity_wp: Optional[Dict[str, Any]] = None
    fertilizer_activities_bsl: Optional[List[Dict[str, Any]]] = None
    fertilizer_activities_wp: Optional[List[Dict[str, Any]]] = None
    nfixing_activities_bsl: Optional[List[Dict[str, Any]]] = None
    nfixing_activities_wp: Optional[List[Dict[str, Any]]] = None
    manure_activities_bsl: Optional[List[Dict[str, Any]]] = None
    manure_activities_wp: Optional[List[Dict[str, Any]]] = None
    enteric_activities_bsl: Optional[List[Dict[str, Any]]] = None
    enteric_activities_wp: Optional[List[Dict[str, Any]]] = None
    burning_activities_bsl: Optional[List[Dict[str, Any]]] = None
    burning_activities_wp: Optional[List[Dict[str, Any]]] = None
    methanogenesis_bsl: Optional[Dict[str, Any]] = None
    methanogenesis_wp: Optional[Dict[str, Any]] = None
    woody_pool_data: Optional[Dict[str, Any]] = None
    leakage_data: Optional[Dict[str, Any]] = None
    npr_rating_pct: Optional[Decimal] = None
    risk_assessment_id: Optional[uuid.UUID] = None
    annual_vintages_input: Optional[List[Dict[str, Any]]] = None
    notes: Optional[str] = None


class NetGHGFinalizeRequest(BaseModel):
    soc_change_result_id: Optional[uuid.UUID] = None
    prerequisite_assessment_id: uuid.UUID
    verification_period_start: Optional[date] = None
    verification_period_end: Optional[date] = None
    applicability_overrides: Optional[List[Dict[str, Any]]] = None
    fossil_fuel_activities_bsl: Optional[List[Dict[str, Any]]] = None
    fossil_fuel_activities_wp: Optional[List[Dict[str, Any]]] = None
    liming_activity_bsl: Optional[Dict[str, Any]] = None
    liming_activity_wp: Optional[Dict[str, Any]] = None
    fertilizer_activities_bsl: Optional[List[Dict[str, Any]]] = None
    fertilizer_activities_wp: Optional[List[Dict[str, Any]]] = None
    nfixing_activities_bsl: Optional[List[Dict[str, Any]]] = None
    nfixing_activities_wp: Optional[List[Dict[str, Any]]] = None
    manure_activities_bsl: Optional[List[Dict[str, Any]]] = None
    manure_activities_wp: Optional[List[Dict[str, Any]]] = None
    enteric_activities_bsl: Optional[List[Dict[str, Any]]] = None
    enteric_activities_wp: Optional[List[Dict[str, Any]]] = None
    burning_activities_bsl: Optional[List[Dict[str, Any]]] = None
    burning_activities_wp: Optional[List[Dict[str, Any]]] = None
    methanogenesis_bsl: Optional[Dict[str, Any]] = None
    methanogenesis_wp: Optional[Dict[str, Any]] = None
    woody_pool_data: Optional[Dict[str, Any]] = None
    leakage_data: Optional[Dict[str, Any]] = None
    npr_rating_pct: Optional[Decimal] = None
    risk_assessment_id: Optional[uuid.UUID] = None
    annual_vintages_input: Optional[List[Dict[str, Any]]] = None
    notes: Optional[str] = None


class NetGHGEvaluationResponse(BaseModel):
    project_id: uuid.UUID
    status: str  # EVALUATED, BLOCKED
    verification_period_start: date
    verification_period_end: date
    elapsed_years: Decimal
    applicability_matrix: Dict[str, Any]
    total_baseline_emissions_tco2e: Decimal
    total_project_emissions_tco2e: Decimal
    total_emission_reductions_from_sources_tco2e: Decimal
    eq44_baseline_total_carbon_stock_change_tco2e: Decimal
    eq45_project_total_carbon_stock_change_tco2e: Decimal
    gross_reductions_er_tco2e: Decimal
    gross_removals_cr_tco2e: Decimal
    total_leakage_tco2e: Decimal
    leakage_allocation_er_lker_tco2e: Decimal
    leakage_allocation_cr_lkcr_tco2e: Decimal
    net_reductions_ernet_tco2e: Decimal
    net_removals_crnet_tco2e: Decimal
    total_net_ghg_errnet_tco2e: Decimal
    npr_rating_pct: Optional[Decimal] = None
    buffer_deduction_reductions_tco2e: Optional[Decimal] = None
    buffer_deduction_removals_tco2e: Optional[Decimal] = None
    total_buffer_deduction_tco2e: Optional[Decimal] = None
    internal_vcu_eligible_reductions_tco2e: Optional[Decimal] = None
    internal_vcu_eligible_removals_tco2e: Optional[Decimal] = None
    internal_vcu_eligible_total_tco2e: Optional[Decimal] = None
    vcu_readiness_status: str
    vintages: List[Dict[str, Any]]
    blocking_reasons: List[str] = Field(default_factory=list)
    evaluation_hash: str
    component_breakdown: Dict[str, Any] = Field(default_factory=dict)
