from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Feedstock Schemas
# ---------------------------------------------------------------------------

class FeedstockSourceCreate(BaseModel):
    project_id: Optional[UUID] = None
    source_code: str = Field(..., max_length=50)
    source_name: str = Field(..., max_length=255)
    source_type: str = Field("AGRICULTURAL_RESIDUE", description="AGRICULTURAL_RESIDUE, FORESTRY_RESIDUE, MUNICIPAL_BIOMASS, INDUSTRIAL_BIOGENIC")
    biomass_type: str = Field(..., max_length=100)
    origin_location: Optional[str] = None
    source_land_unit_id: Optional[UUID] = None
    supplier_name: Optional[str] = None
    waste_status: str = Field("CONFIRMED_WASTE_BIOMASS")
    baseline_fate: str = Field("OPEN_BURNING")
    sustainability_status: str = Field("LOW_RISK")
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class FeedstockSourceResponse(BaseModel):
    id: UUID
    organization_id: UUID
    project_id: Optional[UUID] = None
    source_code: str
    source_name: str
    source_type: str
    biomass_type: str
    origin_location: Optional[str] = None
    source_land_unit_id: Optional[UUID] = None
    supplier_name: Optional[str] = None
    waste_status: str
    baseline_fate: str
    sustainability_status: str
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class FeedstockLotCreate(BaseModel):
    project_id: Optional[UUID] = None
    source_id: UUID
    lot_number: str = Field(..., max_length=50)
    feedstock_type: str = Field(..., max_length=100)
    mass_received_tonnes: float = Field(..., gt=0)
    moisture_content_pct: float = Field(..., ge=0, le=100)
    receipt_date: Optional[datetime] = None
    storage_location: Optional[str] = None
    chain_of_custody_ref: Optional[str] = None
    evidence_hash: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class FeedstockLotResponse(BaseModel):
    id: UUID
    organization_id: UUID
    project_id: Optional[UUID] = None
    source_id: UUID
    lot_number: str
    feedstock_type: str
    mass_received_tonnes: float
    moisture_content_pct: float
    dry_mass_tonnes: float
    allocated_mass_tonnes: float
    available_mass_tonnes: Optional[float] = None
    receipt_date: datetime
    storage_location: Optional[str] = None
    chain_of_custody_ref: Optional[str] = None
    evidence_hash: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FeedstockAllocationRequest(BaseModel):
    lot_id: UUID
    production_run_id: UUID
    allocated_wet_mass_tonnes: float = Field(..., gt=0)


class FeedstockAllocationResponse(BaseModel):
    id: UUID
    lot_id: UUID
    production_run_id: UUID
    allocated_wet_mass_tonnes: float
    allocated_dry_mass_tonnes: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Facility & Reactor Schemas
# ---------------------------------------------------------------------------

class ProductionFacilityCreate(BaseModel):
    project_id: Optional[UUID] = None
    facility_code: str = Field(..., max_length=50)
    facility_name: str = Field(..., max_length=255)
    location: Optional[str] = None
    commissioning_date: Optional[date] = None
    first_biochar_production_date: Optional[date] = None
    project_start_date: Optional[date] = None
    facility_status: str = Field("NEW_OPERATIONAL", description="PLANNED, UNDER_CONSTRUCTION, NEW_OPERATIONAL, EXISTING_OPERATIONAL, DECOMMISSIONED")
    operator_name: Optional[str] = None
    technology_type: str = Field("SLOW_PYROLYSIS")
    production_capacity_tpy: Optional[float] = None
    permits_json: Dict[str, Any] = Field(default_factory=dict)
    emissions_controls_json: Dict[str, Any] = Field(default_factory=dict)
    energy_recovery_json: Dict[str, Any] = Field(default_factory=dict)
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class ProductionFacilityResponse(BaseModel):
    id: UUID
    organization_id: UUID
    project_id: Optional[UUID] = None
    facility_code: str
    facility_name: str
    location: Optional[str] = None
    commissioning_date: Optional[date] = None
    first_biochar_production_date: Optional[date] = None
    project_start_date: Optional[date] = None
    facility_status: str
    operator_name: Optional[str] = None
    technology_type: str
    production_capacity_tpy: Optional[float] = None
    is_active: bool
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FacilityReactorCreate(BaseModel):
    reactor_code: str = Field(..., max_length=50)
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    technology_type: str = Field("SLOW_PYROLYSIS")
    design_capacity_kg_h: Optional[float] = None
    operating_temp_min_c: float = Field(450.0, ge=200, le=1200)
    operating_temp_max_c: float = Field(700.0, ge=200, le=1200)
    residence_time_min_minutes: float = Field(20.0, gt=0)
    residence_time_max_minutes: float = Field(60.0, gt=0)
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class FacilityReactorResponse(BaseModel):
    id: UUID
    facility_id: UUID
    reactor_code: str
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    technology_type: str
    design_capacity_kg_h: Optional[float] = None
    operating_temp_min_c: float
    operating_temp_max_c: float
    residence_time_min_minutes: float
    residence_time_max_minutes: float
    is_active: bool
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Production Run Schemas
# ---------------------------------------------------------------------------

class ProductionRunCreate(BaseModel):
    project_id: Optional[UUID] = None
    facility_id: UUID
    reactor_id: Optional[UUID] = None
    run_number: str = Field(..., max_length=50)
    start_time: datetime
    end_time: Optional[datetime] = None
    avg_pyrolysis_temp_celsius: float = Field(..., ge=300, le=1200)
    max_pyrolysis_temp_celsius: Optional[float] = None
    residence_time_minutes: float = Field(..., gt=0)
    electricity_kwh: float = Field(0.0, ge=0)
    fuel_liters: float = Field(0.0, ge=0)
    heat_recovered_mj: float = Field(0.0, ge=0)
    output_biochar_mass_tonnes: float = Field(..., gt=0)
    co_products_json: Dict[str, Any] = Field(default_factory=dict)
    operator_id: Optional[UUID] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class ProductionRunResponse(BaseModel):
    id: UUID
    organization_id: UUID
    project_id: Optional[UUID] = None
    facility_id: UUID
    reactor_id: Optional[UUID] = None
    run_number: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_feedstock_input_tonnes: float
    total_feedstock_dry_tonnes: float
    avg_pyrolysis_temp_celsius: float
    max_pyrolysis_temp_celsius: Optional[float] = None
    residence_time_minutes: float
    electricity_kwh: float
    fuel_liters: float
    heat_recovered_mj: float
    output_biochar_mass_tonnes: float
    qa_status: str
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Batch Schemas (Backward compatible)
# ---------------------------------------------------------------------------

class BiocharBatchCreate(BaseModel):
    project_id: UUID
    batch_number: str
    facility_name: str
    kiln_id: str
    production_run_id: Optional[UUID] = None
    feedstock_type: str
    feedstock_weight_tonnes: float = Field(..., gt=0)
    moisture_content_pct: float = Field(..., ge=0, le=100)
    origin_location: Optional[str] = None
    pyrolysis_temp_celsius: float = Field(..., ge=300, le=1200)
    residence_time_minutes: float = Field(..., gt=0)
    biochar_yield_tonnes: float = Field(..., gt=0)
    dry_mass_tonnes: Optional[float] = None
    fixed_carbon_pct: float = Field(75.0, ge=0, le=100)
    ash_content_pct: float = Field(5.0, ge=0, le=100)
    molar_h_c_ratio: float = Field(0.4, ge=0, le=1.0)
    carbon_claim_project_id: Optional[UUID] = None
    carbon_claim_registry: Optional[str] = None
    carbon_claim_methodology: Optional[str] = None
    lab_report_number: Optional[str] = None
    lab_document_url: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class BiocharBatchResponse(BaseModel):
    id: UUID
    organization_id: Optional[UUID] = None
    project_id: UUID
    batch_number: str
    facility_name: str
    kiln_id: str
    production_run_id: Optional[UUID] = None
    feedstock_type: str
    feedstock_weight_tonnes: float
    biochar_yield_tonnes: float
    dry_mass_tonnes: Optional[float] = None
    fixed_carbon_pct: float
    molar_h_c_ratio: float
    carbon_permanence_factor: float
    net_co2e_removed_tonnes: float
    quality_grade: str
    status: str
    has_anomaly: bool
    anomaly_reason: Optional[str] = None
    carbon_claim_project_id: Optional[UUID] = None
    carbon_claim_registry: Optional[str] = None
    carbon_claim_methodology: Optional[str] = None
    mass_balance_allocated_tonnes: float = 0.0
    mass_balance_status: str = "IN_BALANCE"
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Lab Analysis Schemas
# ---------------------------------------------------------------------------

class BiocharLabAnalysisCreate(BaseModel):
    batch_id: UUID
    project_id: Optional[UUID] = None
    sample_id: str = Field(..., max_length=100)
    sampling_date: datetime
    testing_date: Optional[datetime] = None
    laboratory_name: str = Field(..., max_length=255)
    accreditation_standard: Optional[str] = Field("ISO_17025")
    test_method: Optional[str] = Field("DIN_51732")
    molar_h_c_ratio: float = Field(..., ge=0.0, le=2.0)
    organic_carbon_pct: float = Field(..., ge=0, le=100)
    fixed_carbon_pct: float = Field(..., ge=0, le=100)
    moisture_pct: float = Field(..., ge=0, le=100)
    ash_pct: float = Field(..., ge=0, le=100)
    volatile_matter_pct: Optional[float] = None
    heavy_metals_pass: bool = True
    pah_content_mg_kg: Optional[float] = None
    lab_report_hash: Optional[str] = None
    lab_report_uri: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class BiocharLabAnalysisResponse(BaseModel):
    id: UUID
    organization_id: UUID
    project_id: Optional[UUID] = None
    batch_id: UUID
    sample_id: str
    sampling_date: datetime
    testing_date: Optional[datetime] = None
    laboratory_name: str
    accreditation_standard: Optional[str] = None
    test_method: Optional[str] = None
    molar_h_c_ratio: float
    organic_carbon_pct: float
    fixed_carbon_pct: float
    moisture_pct: float
    ash_pct: float
    volatile_matter_pct: Optional[float] = None
    heavy_metals_pass: bool
    pah_content_mg_kg: Optional[float] = None
    qa_status: str
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Material Transaction Schemas
# ---------------------------------------------------------------------------

class BiocharMaterialTransactionResponse(BaseModel):
    id: UUID
    organization_id: UUID
    batch_id: UUID
    transaction_type: str
    quantity_tonnes: float
    from_location: Optional[str] = None
    to_location: Optional[str] = None
    event_time: datetime
    source_event_id: Optional[UUID] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Transport & Storage Schemas
# ---------------------------------------------------------------------------

class BiocharTransportEventCreate(BaseModel):
    project_id: Optional[UUID] = None
    material_type: str = Field("BIOCHAR_BATCH", description="FEEDSTOCK_LOT, BIOCHAR_BATCH")
    reference_id: UUID
    origin_address: str
    destination_address: str
    mass_transported_tonnes: float = Field(..., gt=0)
    distance_km: float = Field(..., gt=0)
    distance_source: str = Field("VERIFIED_ODOMETER_LOGISTICS")
    transport_mode: str = Field("ROAD_DIESEL_TRUCK")
    carrier_name: Optional[str] = None
    departure_date: datetime
    delivery_date: Optional[datetime] = None
    proof_of_delivery_ref: Optional[str] = None
    pod_document_hash: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class BiocharTransportEventResponse(BaseModel):
    id: UUID
    organization_id: UUID
    project_id: Optional[UUID] = None
    material_type: str
    reference_id: UUID
    origin_address: str
    destination_address: str
    mass_transported_tonnes: float
    distance_km: float
    distance_source: str
    transport_mode: str
    carrier_name: Optional[str] = None
    departure_date: datetime
    delivery_date: Optional[datetime] = None
    proof_of_delivery_ref: Optional[str] = None
    status: str
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BiocharStorageEventCreate(BaseModel):
    batch_id: UUID
    storage_facility_name: str
    storage_location: str
    start_date: datetime
    end_date: Optional[datetime] = None
    quantity_stored_tonnes: float = Field(..., ge=0)
    loss_or_damage_tonnes: float = Field(0.0, ge=0)
    storage_conditions: str = Field("COVERED_DRY_VENTILATED")
    notes: Optional[str] = None


class BiocharStorageEventResponse(BaseModel):
    id: UUID
    organization_id: UUID
    batch_id: UUID
    storage_facility_name: str
    storage_location: str
    start_date: datetime
    end_date: Optional[datetime] = None
    quantity_stored_tonnes: float
    loss_or_damage_tonnes: float
    storage_conditions: str
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# End-Use Schemas
# ---------------------------------------------------------------------------

class BiocharEndUseRecordCreate(BaseModel):
    project_id: Optional[UUID] = None
    batch_id: UUID
    end_use_type: str = Field(..., description="SOIL_APPLICATION, NON_SOIL_APPLICATION")
    applied_quantity_tonnes: float = Field(..., gt=0)
    event_date: datetime
    # Soil fields
    source_land_unit_id: Optional[UUID] = None
    application_rate_tonnes_per_ha: Optional[float] = None
    area_hectares: Optional[float] = None
    application_method: Optional[str] = None
    gps_coordinates: Optional[str] = None
    wetland_exclusion_screened: bool = True
    crop_type: Optional[str] = None
    # Non-Soil fields
    product_category: Optional[str] = None
    recipient_organization: Optional[str] = None
    durability_classification: Optional[str] = None
    proof_photos_json: List[str] = Field(default_factory=list)
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class BiocharEndUseRecordResponse(BaseModel):
    id: UUID
    organization_id: UUID
    project_id: Optional[UUID] = None
    batch_id: UUID
    end_use_type: str
    applied_quantity_tonnes: float
    event_date: datetime
    source_land_unit_id: Optional[UUID] = None
    application_rate_tonnes_per_ha: Optional[float] = None
    area_hectares: Optional[float] = None
    application_method: Optional[str] = None
    gps_coordinates: Optional[str] = None
    wetland_exclusion_screened: bool
    crop_type: Optional[str] = None
    product_category: Optional[str] = None
    recipient_organization: Optional[str] = None
    durability_classification: Optional[str] = None
    verification_status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Mass Balance & Conflict & Lineage Responses
# ---------------------------------------------------------------------------

class MassBalanceReconciliationResponse(BaseModel):
    batch_id: UUID
    batch_number: str
    original_produced_mass_tonnes: float
    current_inventory_tonnes: float
    terminal_end_use_tonnes: float
    product_allocations_tonnes: float = 0.0
    documented_losses_tonnes: float
    rejected_tonnes: float
    total_reconciled_tonnes: float
    discrepancy_tonnes: float
    status: str  # RECONCILED, OVER_ALLOCATED, UNRECONCILED
    is_valid: bool
    tolerated_variance: float
    notes: Optional[str] = None


class MethodologyConflictResponse(BaseModel):
    has_conflict: bool
    conflict_code: Optional[str] = None
    severity: Optional[str] = None  # BLOCKING, WARNING
    biochar_project_id: Optional[UUID] = None
    agriculture_project_id: Optional[UUID] = None
    affected_land_unit_id: Optional[UUID] = None
    affected_land_unit_name: Optional[str] = None
    biochar_methodology: Optional[str] = None
    agriculture_methodology: Optional[str] = None
    carbon_pool: Optional[str] = None
    spatial_overlap_hectares: Optional[float] = None
    time_overlap_detected: bool = False
    message: Optional[str] = None
    resolution_requirement: Optional[str] = None
    accounting_blocked: bool = False


class BiocharEligibilityResponse(BaseModel):
    project_id: UUID
    target_standard: str
    target_methodology: str
    methodology_version: str
    eligibility_status: str  # POTENTIALLY_ELIGIBLE, REQUIRES_EVIDENCE, EXPERT_REVIEW_REQUIRED, INELIGIBLE, NOT_SUPPORTED
    facility_criteria_met: bool
    feedstock_criteria_met: bool
    additionality_status: str
    requirements_complete: List[str]
    requirements_missing: List[str]
    blocking_findings: List[str]
    review_findings: List[str]
    source_references: List[str]
    evaluated_at: datetime


class ChainOfCustodyNode(BaseModel):
    node_type: str  # SOURCE, LOT, FACILITY, RUN, BATCH, LAB, STORAGE, TRANSPORT, END_USE
    node_id: str
    title: str
    details: Dict[str, Any]
    hash: Optional[str] = None


class ChainOfCustodyResponse(BaseModel):
    batch_id: UUID
    batch_number: str
    traceability_complete: bool
    nodes: List[ChainOfCustodyNode]
    upstream_chain: List[str]
    downstream_chain: List[str]
    evidence_hashes: List[str]


class BiocharSummaryResponse(BaseModel):
    total_batches: int
    total_feedstock_tonnes: float
    total_biochar_produced_tonnes: float
    total_net_co2e_removed_tonnes: float
    grade_a_percentage: float
    detected_anomalies_count: int


# ---------------------------------------------------------------------------
# Multi-Biomass Feedstock Blend Schemas
# ---------------------------------------------------------------------------

class MultiBiomassBlendComponent(BaseModel):
    source_id: UUID
    source_code: str
    source_name: str
    source_type: str
    biomass_type: str
    baseline_fate: str
    sustainability_status: str
    lot_id: UUID
    lot_number: str
    wet_mass_tonnes: float
    dry_mass_tonnes: float
    wet_mass_pct: float
    dry_mass_pct: float
    moisture_content_pct: float


class MultiBiomassBlendBreakdownResponse(BaseModel):
    production_run_id: UUID
    run_number: str
    total_wet_mass_tonnes: float
    total_dry_mass_tonnes: float
    component_count: int
    components: List[MultiBiomassBlendComponent]


# ---------------------------------------------------------------------------
# Product Formulation & Mixed Product Batch Schemas
# ---------------------------------------------------------------------------

class BiocharProductFormulationCreate(BaseModel):
    product_name: str
    product_code: str
    target_sector: str
    description: Optional[str] = None
    biochar_target_ratio: float = 0.5
    is_active: bool = True
    project_id: Optional[UUID] = None


class BiocharProductFormulationResponse(BaseModel):
    id: UUID
    organization_id: UUID
    project_id: Optional[UUID] = None
    product_name: str
    product_code: str
    target_sector: str
    description: Optional[str] = None
    biochar_target_ratio: float
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BiocharIngredientAllocationInput(BaseModel):
    biochar_batch_id: UUID
    allocated_biochar_mass_tonnes: float


class NonBiocharIngredientInput(BaseModel):
    ingredient_name: str
    ingredient_type: str  # COMPOST, MINERAL_FERTILIZER, SAND, CLAY, CEMENT, BINDER
    mass_tonnes: float
    mass_pct: float
    cas_number: Optional[str] = None
    supplier: Optional[str] = None


class BiocharProductBatchCreate(BaseModel):
    formulation_id: UUID
    batch_number: str
    production_date: datetime
    total_product_mass_tonnes: float
    biochar_mass_tonnes: float
    non_biochar_mass_tonnes: float = 0.0
    packaging_type: Optional[str] = None
    storage_location: Optional[str] = None
    biochar_batch_allocations: List[BiocharIngredientAllocationInput]
    non_biochar_ingredients: List[NonBiocharIngredientInput] = []
    project_id: Optional[UUID] = None


class BiocharProductBatchResponse(BaseModel):
    id: UUID
    organization_id: UUID
    project_id: Optional[UUID] = None
    formulation_id: UUID
    batch_number: str
    production_date: datetime
    total_product_mass_tonnes: float
    biochar_mass_tonnes: float
    non_biochar_mass_tonnes: float
    packaging_type: Optional[str] = None
    storage_location: Optional[str] = None
    qa_status: str
    created_at: datetime
    allocations: List[Dict[str, Any]] = []
    non_biochar_ingredients: List[Dict[str, Any]] = []

    model_config = ConfigDict(from_attributes=True)

