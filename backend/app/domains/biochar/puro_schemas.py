import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class PuroRuleDefinitionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    section_number: int
    section_title: str
    rule_number: str
    rule_title: str
    applicability_condition: Optional[str] = None
    requirement_type: str
    implementation_handler: str
    required_evidence_types: List[str] = []
    is_blocking: bool = True


class PuroNormativeDependencySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    title: str
    version: str
    document_type: str
    status: str
    effective_date: date
    source_reference: Optional[str] = None
    required_by_rules: List[str] = []
    implementation_state: str  # DEPENDENCY_REQUIRED, VERIFIED
    checksum_hash: Optional[str] = None
    last_reviewed_at: Optional[datetime] = None


class PuroSupplierProfileCreate(BaseModel):
    facility_id: uuid.UUID
    supplier_legal_name: str
    registration_number: Optional[str] = None
    jurisdiction_country: str
    supplier_role: str = "PRODUCER"
    claim_rights_status: str = "EXCLUSIVE_CLAIM_RIGHTS_ESTABLISHED"
    authorization_agreement_ref: Optional[str] = None
    rights_declaration_doc_hash: Optional[str] = None
    contract_effective_date: Optional[date] = None
    contract_expiry_date: Optional[date] = None


class PuroSupplierProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    project_id: uuid.UUID
    facility_id: uuid.UUID
    supplier_legal_name: str
    registration_number: Optional[str] = None
    jurisdiction_country: str
    supplier_role: str
    claim_rights_status: str
    authorization_agreement_ref: Optional[str] = None
    rights_declaration_doc_hash: Optional[str] = None
    contract_effective_date: Optional[date] = None
    contract_expiry_date: Optional[date] = None
    validation_state: str
    created_at: datetime


class PuroFacilityProfileCreate(BaseModel):
    facility_id: uuid.UUID
    facility_classification: str = "STATIONARY"  # STATIONARY, MOBILE
    host_country: str
    reference_coordinates: Optional[str] = None
    spatial_extent_geojson: Optional[Dict[str, Any]] = None
    receiving_location: Optional[str] = None
    pretreatment_location: Optional[str] = None
    conversion_location: Optional[str] = None
    packaging_location: Optional[str] = None
    technology_similarity_verified: bool = True
    commissioned_status: str = "COMMISSIONED"
    operating_status: str = "ACTIVE"


class PuroFacilityProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    facility_id: uuid.UUID
    facility_classification: str
    host_country: str
    reference_coordinates: Optional[str] = None
    spatial_extent_geojson: Optional[Dict[str, Any]] = None
    receiving_location: Optional[str] = None
    pretreatment_location: Optional[str] = None
    conversion_location: Optional[str] = None
    packaging_location: Optional[str] = None
    technology_similarity_verified: bool
    commissioned_status: str
    operating_status: str
    created_at: datetime


class PuroMobileSiteCreate(BaseModel):
    site_code: str
    site_name: str
    coordinates: str
    owner_operator: Optional[str] = None
    date_range_start: date
    date_range_end: Optional[date] = None
    regulatory_permit_ref: Optional[str] = None
    stakeholder_evidence_ref: Optional[str] = None


class PuroMobileSiteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    facility_profile_id: uuid.UUID
    site_code: str
    site_name: str
    coordinates: str
    owner_operator: Optional[str] = None
    date_range_start: date
    date_range_end: Optional[date] = None
    regulatory_permit_ref: Optional[str] = None
    stakeholder_evidence_ref: Optional[str] = None
    is_active: bool
    created_at: datetime


class PuroCreditingPeriodCreate(BaseModel):
    facility_id: uuid.UUID
    sequence_number: int = 1
    start_date: date
    end_date: date
    crediting_duration_years: int = 10
    renewal_type: Optional[str] = "INITIAL_PERIOD"


class PuroCreditingPeriodResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    facility_id: uuid.UUID
    sequence_number: int
    start_date: date
    end_date: date
    crediting_duration_years: int
    status: str
    renewal_type: Optional[str] = None
    renewal_eligibility: bool
    previous_period_id: Optional[uuid.UUID] = None
    created_at: datetime


class PuroBaselineAssessmentCreate(BaseModel):
    facility_id: uuid.UUID
    scenario: str  # NEW_FACILITY, RETROFIT_FACILITY, CHARCOAL_REPURPOSE, UNFORESEEN_CASE_REQUIRING_ISSUING_BODY_REVIEW
    historical_char_production_tpy: float = 0.0
    baseline_removal_tco2e_per_year: float = 0.0
    historical_products_description: Optional[str] = None
    prior_use_fate: Optional[str] = None
    baseline_land_use_evidence_type: Optional[str] = None
    land_use_evidence_ref: Optional[str] = None


class PuroBaselineAssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    project_id: uuid.UUID
    facility_id: uuid.UUID
    scenario: str
    is_locked: bool
    historical_char_production_tpy: float
    baseline_removal_tco2e_per_year: float
    historical_products_description: Optional[str] = None
    prior_use_fate: Optional[str] = None
    baseline_land_use_evidence_type: Optional[str] = None
    land_use_evidence_ref: Optional[str] = None
    assessment_status: str
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime


class PuroAdditionalityAssessmentCreate(BaseModel):
    facility_id: uuid.UUID
    carbon_additionality_status: str = "PASS"
    regulatory_additionality_status: str = "PASS"
    financial_additionality_status: str = "PASS"
    opex_per_tonne: Optional[float] = None
    capex_investment: Optional[float] = None
    biomass_cost_per_tonne: Optional[float] = None
    biochar_market_price_per_tonne: Optional[float] = None
    carbon_finance_dependency_pct: Optional[float] = None
    legal_mandate_evidence_ref: Optional[str] = None
    financial_model_evidence_hash: Optional[str] = None


class PuroAdditionalityAssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    project_id: uuid.UUID
    facility_id: uuid.UUID
    carbon_additionality_status: str
    regulatory_additionality_status: str
    financial_additionality_status: str
    overall_status: str
    opex_per_tonne: Optional[float] = None
    capex_investment: Optional[float] = None
    biomass_cost_per_tonne: Optional[float] = None
    biochar_market_price_per_tonne: Optional[float] = None
    carbon_finance_dependency_pct: Optional[float] = None
    legal_mandate_evidence_ref: Optional[str] = None
    financial_model_evidence_hash: Optional[str] = None
    created_at: datetime


class PuroEndUseCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category_code: str  # AF1, BE1, etc.
    category_name: str
    sector: str
    product_type: str
    application_type: Optional[str] = None
    pure_or_mixed: str
    min_environmental_quality: Optional[str] = None
    is_corc_eligible: bool
    default_durability_years: int
    persistence_factor_non_soil: Optional[float] = None
    reversal_rules: Dict[str, Any] = {}
    cascading_conditions: Dict[str, Any] = {}
    reversal_discount_factor_required: bool = False
    required_evidence_types: List[str] = []
    rule_references: List[str] = []


class PuroEndUseRecordLinkCreate(BaseModel):
    batch_id: uuid.UUID
    end_use_record_id: uuid.UUID
    category_id: uuid.UUID
    is_pure_biochar: bool = True
    formulation_biochar_pct: float = 100.0
    manufacturer_name: Optional[str] = None
    intermediary_entity_name: Optional[str] = None
    intermediary_agreement_ref: Optional[str] = None
    cascade_stage: str = "SINGLE_USE"
    final_durable_fate_verified: bool = True
    proof_of_delivery_ref: Optional[str] = None
    application_attestation_ref: Optional[str] = None
    gps_verified: bool = True
    geotagged_photos_verified: bool = True


class PuroEndUseRecordLinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    batch_id: uuid.UUID
    end_use_record_id: uuid.UUID
    category_id: uuid.UUID
    is_pure_biochar: bool
    formulation_biochar_pct: float
    manufacturer_name: Optional[str] = None
    intermediary_entity_name: Optional[str] = None
    cascade_stage: str
    final_durable_fate_verified: bool
    proof_of_delivery_ref: Optional[str] = None
    application_attestation_ref: Optional[str] = None
    gps_verified: bool
    geotagged_photos_verified: bool
    corc_point_reached: str
    created_at: datetime


class PuroQuantificationRequest(BaseModel):
    batch_id: uuid.UUID
    soil_temperature_celsius: float = 15.0  # Mean annual soil temperature (Celsius)
    dry_mass_override_tonnes: Optional[float] = None
    impurity_pct: float = 0.0  # Dry-basis impurities percentage
    eligible_feedstock_fraction: float = 1.0  # Fraction of biomass compliant with sourcing rules
    e_project_transport_tco2e: float = 0.0
    e_project_processing_tco2e: float = 0.0
    e_project_application_tco2e: float = 0.0
    e_project_auxiliary_fuel_tco2e: float = 0.0
    e_project_methane_storage_tco2e: float = 0.0
    e_leakage_tco2e: float = 0.0
    dry_mass_determination_method: str = "LABORATORY_MOISTURE_ASTM_D4442"  # Supported method


class PuroSimulationRequest(BaseModel):
    batch_id: Optional[uuid.UUID] = None
    dry_mass_tonnes: float = 100.0
    c_org_pct: float = 80.0
    molar_h_c: float = 0.35
    soil_temperature_celsius: float = 15.0
    baseline_scenario: str = "NEW_FACILITY"
    historical_baseline_tco2e: float = 0.0
    end_use_category_code: str = "AF1"
    reversal_discount_factor: Optional[float] = None
    is_non_soil_durable: bool = False
    # LCA operational & embodied emissions
    e_biomass: float = 2.5
    e_production: float = 1.0
    e_use: float = 0.5
    e_infra: float = 5.0
    e_dluc: float = 0.0
    crediting_years: int = 10
    # Leakage
    is_leakage_mitigated: bool = True
    ecological_leakage_tco2e: float = 0.0
    market_activity_shifting_tco2e: float = 0.0
    iluc_feedstock_category: Optional[str] = None
    feedstock_quantity_dry_tonnes: float = 0.0


class PuroAuthoritativeRequest(BaseModel):
    batch_id: uuid.UUID


class PuroQuantificationBreakdown(BaseModel):
    eligible_dry_biochar_mass_tonnes: float
    organic_carbon_pct: float
    molar_h_c: float
    soil_temperature_celsius: float
    persistence_fraction_pf: float
    regression_m: Optional[float] = None
    regression_a: Optional[float] = None
    durability_class: str  # CORC200+, INELIGIBLE

    c_stored_tco2e: float
    c_baseline_tco2e: float
    c_loss_tco2e: float
    e_project_tco2e: float
    e_ops_biomass_tco2e: float = 0.0
    e_ops_production_tco2e: float = 0.0
    e_ops_use_tco2e: float = 0.0
    e_ops_total_tco2e: float = 0.0
    e_emb_infra_tco2e: float = 0.0
    e_emb_dluc_tco2e: float = 0.0
    e_emb_annualized_tco2e: float = 0.0

    leakage_eco_tco2e: float = 0.0
    leakage_ma_tco2e: float = 0.0
    leakage_iluc_tco2e: float = 0.0
    e_leakage_tco2e: float

    net_corcs_calculated: float
    combined_uncertainty_pct: float
    deductible_uncertainty_pct: float = 0.0
    final_corcs_issuable: float
    reported_uncertainty_text: Optional[str] = None

    calculation_mode: str = "AUTHORITATIVE"  # AUTHORITATIVE, SIMULATION
    calculation_status: str  # SUCCESS, FAIL_CLOSED, DATA_REQUIRED
    corc_point_status: str  # CORC_POINT_ELIGIBLE, CORC_POINT_NOT_REACHED, etc.
    calculation_hash: str
    methodology_version: str
    coefficient_version: str
    engine_version: str
    timestamp: datetime
    execution_id: Optional[str] = None
    rule_references: List[str] = []
    warnings: List[str] = []
    notes: Optional[str] = None


class PuroCharStreamRecordCreate(BaseModel):
    facility_id: uuid.UUID
    stream_code: str
    stream_name: str
    feedstock_type: str
    pyrolyzer_unit: str
    operating_temperature_celsius: float
    residence_time_minutes: Optional[float] = None
    is_active: bool = True


class PuroCharStreamRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    facility_id: uuid.UUID
    stream_code: str
    stream_name: str
    feedstock_type: str
    pyrolyzer_unit: str
    operating_temperature_celsius: float
    residence_time_minutes: Optional[float] = None
    is_active: bool
    created_at: datetime


class PuroLCAModelCreate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    facility_id: uuid.UUID
    model_name: str
    system_boundary: str = "CRADLE_TO_GATE_PLUS_DISPOSITION"
    crediting_years: int = 10
    allocation_method: str = "ENERGY_LHV"


class PuroLCAModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: uuid.UUID
    organization_id: uuid.UUID
    facility_id: uuid.UUID
    model_name: str
    system_boundary: str
    crediting_years: int
    allocation_method: str
    status: str
    created_at: datetime


class PuroLCIEntryCreate(BaseModel):
    lca_model_id: uuid.UUID
    category: str  # OPERATIONAL_BIOMASS, OPERATIONAL_PRODUCTION, OPERATIONAL_USE, EMBODIED_INFRASTRUCTURE, EMBODIED_DLUC
    item_name: str
    quantity: float
    unit: str
    emission_factor: float
    ef_unit: str
    ef_source: str
    ghg_emissions_tco2e: float
    notes: Optional[str] = None


class PuroLCIEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    lca_model_id: uuid.UUID
    category: str
    item_name: str
    quantity: float
    unit: str
    emission_factor: float
    ef_unit: str
    ef_source: str
    ghg_emissions_tco2e: float
    notes: Optional[str] = None
    created_at: datetime


class PuroCutoffDecisionCreate(BaseModel):
    lca_model_id: uuid.UUID
    input_material_stream: str
    mass_energy_contribution_pct: float
    justified_reason: str
    auditor_approved: bool = False


class PuroCutoffDecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    lca_model_id: uuid.UUID
    input_material_stream: str
    mass_energy_contribution_pct: float
    justified_reason: str
    auditor_approved: bool
    created_at: datetime


class PuroCoProductAllocationCreate(BaseModel):
    production_run_id: uuid.UUID
    co_product_record_id: uuid.UUID
    allocation_basis: str = "ENERGY_LHV"
    biochar_lhv_mj_kg: float
    coproduct_lhv_mj_kg: float
    biochar_allocation_share_pct: float
    coproduct_allocation_share_pct: float
    allocated_emissions_tco2e: float
    justification: Optional[str] = None


class PuroCoProductAllocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    production_run_id: uuid.UUID
    co_product_record_id: uuid.UUID
    allocation_basis: str
    biochar_lhv_mj_kg: float
    coproduct_lhv_mj_kg: float
    biochar_allocation_share_pct: float
    coproduct_allocation_share_pct: float
    allocated_emissions_tco2e: float
    justification: Optional[str] = None
    created_at: datetime


class PuroAuditWorkflowCreate(BaseModel):
    facility_id: uuid.UUID
    audit_type: str  # PRODUCTION_FACILITY_AUDIT, PURO_OUTPUT_AUDIT
    auditor_organization: str
    lead_auditor_name: Optional[str] = None
    scheduled_date: Optional[date] = None
    monitoring_period_id: Optional[str] = None


class PuroAuditWorkflowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    facility_id: uuid.UUID
    monitoring_period_id: Optional[str] = None
    audit_type: str
    auditor_organization: str
    lead_auditor_name: Optional[str] = None
    audit_status: str
    scheduled_date: Optional[date] = None
    completion_date: Optional[date] = None
    audit_dossier_hash: Optional[str] = None
    certificate_number: Optional[str] = None
    created_at: datetime


class PuroOutputReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    facility_id: uuid.UUID
    monitoring_period_id: str
    report_number: str
    report_version: int
    report_status: str
    total_eligible_biochar_mass_tonnes: float
    total_net_corcs: float
    manifest_hash: str
    ledger_signature_id: Optional[uuid.UUID] = None
    generated_at: datetime


class PuroRegistryReadinessResponse(BaseModel):
    project_id: uuid.UUID
    facility_id: Optional[uuid.UUID] = None
    methodology_code: str = "PURO_BIOCHAR_2025_V2"
    readiness_state: str  # NOT_STARTED, IN_PROGRESS, BLOCKED, READY_FOR_AUDIT, AUDIT_COMPLETE, READY_FOR_REGISTRY_SUBMISSION
    overall_capability_status: str  # PRODUCTION_READY_WITH_LIMITATION, BLOCKED, etc.
    active_blockers: List[str] = []
    unresolved_dependencies: List[str] = []
    audit_readiness_status: str
    quantification_status: str
    issuance_status: str = "NOT_ISSUED"
    corc_point_verified_batches_count: int = 0
    total_eligible_batches_count: int = 0
    evaluated_at: datetime
