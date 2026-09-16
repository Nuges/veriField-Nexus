import uuid
from datetime import date, datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class PuroMethodologyVersion(Base):
    """
    Puro.earth Methodology Version locking entity.
    Maintains immutable rule references for Edition 2025 V2.
    """
    __tablename__ = "puro_methodology_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), nullable=False, unique=True, index=True)  # PURO_BIOCHAR_2025_V2
    name = Column(String(255), nullable=False)
    edition = Column(String(50), nullable=False, default="Edition 2025 v2")
    approval_date = Column(Date, nullable=False, default=date(2025, 11, 27))
    effective_date = Column(Date, nullable=False, default=date(2025, 11, 27))
    status = Column(String(50), nullable=False, default="ACTIVE")  # ACTIVE, SUPERSEDED, RETIRED
    source_url = Column(String(500), nullable=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())

    # Relationships
    rules = relationship("PuroRuleDefinition", back_populates="methodology_version", cascade="all, delete-orphan")


class PuroRuleDefinition(Base):
    """
    Methodology Rule Definition for Puro.earth Biochar Edition 2025 V2.
    Defines section-by-section requirements across all 11 methodology chapters.
    """
    __tablename__ = "puro_rule_definitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    methodology_version_id = Column(UUID(as_uuid=True), ForeignKey("puro_methodology_versions.id", ondelete="CASCADE"), nullable=False, index=True)

    section_number = Column(Integer, nullable=False)
    section_title = Column(String(255), nullable=False)
    rule_number = Column(String(50), nullable=False, unique=True, index=True)  # e.g., "PURO-BIOCHAR-3.1"
    rule_title = Column(String(255), nullable=False)
    applicability_condition = Column(String(255), nullable=True)
    requirement_type = Column(String(100), nullable=False)  # ELIGIBILITY, QUANTIFICATION, MONITORING, AUDIT, SAFEGUARDS
    implementation_handler = Column(String(100), nullable=False)  # System handler or manual check
    required_evidence_types = Column(JSON, default=list)
    is_blocking = Column(Boolean, nullable=False, default=True)

    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())

    # Relationships
    methodology_version = relationship("PuroMethodologyVersion", back_populates="rules")
    evaluations = relationship("PuroComplianceEvaluation", back_populates="rule_definition", cascade="all, delete-orphan")


class PuroNormativeDependency(Base):
    """
    External Puro.earth Normative Document Dependency.
    Tracks required external specifications (General Rules, Biomass Sourcing Criteria, etc.).
    """
    __tablename__ = "puro_normative_dependencies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), nullable=False, unique=True, index=True)  # e.g. "PURO_GENERAL_RULES_V4"
    title = Column(String(255), nullable=False)
    version = Column(String(50), nullable=False)
    document_type = Column(String(100), nullable=False)  # NORMATIVE_STANDARD, CRITERIA, QUESTIONNAIRE, TEMPLATE
    status = Column(String(50), nullable=False, default="ACTIVE")
    effective_date = Column(Date, nullable=False)
    source_reference = Column(String(500), nullable=True)
    required_by_rules = Column(JSON, default=list)  # List of rule numbers
    implementation_state = Column(String(50), nullable=False, default="DEPENDENCY_REQUIRED")  # DEPENDENCY_REQUIRED, VERIFIED
    checksum_hash = Column(String(64), nullable=True)
    last_reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())


class PuroSupplierProfile(Base):
    """
    Puro.earth CO2 Removal Supplier concept.
    Captures legal entity identity, supplier role, exclusive claim rights, and prevents double claims.
    """
    __tablename__ = "puro_supplier_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    facility_id = Column(UUID(as_uuid=True), ForeignKey("biochar_production_facilities.id", ondelete="CASCADE"), nullable=False, index=True)

    supplier_legal_name = Column(String(255), nullable=False)
    registration_number = Column(String(100), nullable=True)
    jurisdiction_country = Column(String(100), nullable=False)
    supplier_role = Column(String(50), nullable=False, default="PRODUCER")  # PRODUCER, PARENT_COMPANY, AGENT, AGGREGATOR, PROJECT_DEVELOPER, OTHER_AUTHORIZED_REPRESENTATIVE

    claim_rights_status = Column(String(50), nullable=False, default="PENDING_AUTHORIZATION")  # EXCLUSIVE_CLAIM_RIGHTS_ESTABLISHED, NON_EXCLUSIVE, PENDING_AUTHORIZATION, BLOCKED_DOUBLE_CLAIM
    authorization_agreement_ref = Column(String(255), nullable=True)
    rights_declaration_doc_hash = Column(String(64), nullable=True)
    contract_effective_date = Column(Date, nullable=True)
    contract_expiry_date = Column(Date, nullable=True)
    validation_state = Column(String(50), nullable=False, default="PENDING_AUDIT")  # PENDING_AUDIT, VALIDATED, REJECTED

    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), onupdate=func.now())

    # Relationships
    organization = relationship("Organization")
    project = relationship("Project")
    facility = relationship("ProductionFacility")


class PuroFacilityProfile(Base):
    """
    Puro Facility Classification (Stationary vs Mobile).
    Stationary: Fixed location and conversion plant.
    Mobile: Fleet of mobile reactors, host country boundary containment, registered operational sites.
    """
    __tablename__ = "puro_facility_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    facility_id = Column(UUID(as_uuid=True), ForeignKey("biochar_production_facilities.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    facility_classification = Column(String(50), nullable=False, default="STATIONARY")  # STATIONARY, MOBILE
    host_country = Column(String(100), nullable=False)
    reference_coordinates = Column(String(100), nullable=True)
    spatial_extent_geojson = Column(JSON, nullable=True)  # Bounding geometry (mandatory for Mobile fleet)

    # Stationary-specific attributes
    receiving_location = Column(String(255), nullable=True)
    pretreatment_location = Column(String(255), nullable=True)
    conversion_location = Column(String(255), nullable=True)
    packaging_location = Column(String(255), nullable=True)
    technology_similarity_verified = Column(Boolean, default=True)

    commissioned_status = Column(String(50), nullable=False, default="COMMISSIONED")  # COMMISSIONED, UNDER_CONSTRUCTION
    operating_status = Column(String(50), nullable=False, default="ACTIVE")  # ACTIVE, IDLE, DECOMMISSIONED

    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())

    # Relationships
    organization = relationship("Organization")
    facility = relationship("ProductionFacility")
    mobile_sites = relationship("PuroMobileProductionSite", back_populates="facility_profile", cascade="all, delete-orphan")


class PuroMobileProductionSite(Base):
    """
    Operating site registered under a Mobile Puro Facility Profile.
    Enforces host country containment and registered operating date windows.
    """
    __tablename__ = "puro_mobile_production_sites"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    facility_profile_id = Column(UUID(as_uuid=True), ForeignKey("puro_facility_profiles.id", ondelete="CASCADE"), nullable=False, index=True)

    site_code = Column(String(50), nullable=False, index=True)
    site_name = Column(String(255), nullable=False)
    coordinates = Column(String(100), nullable=False)  # "lat,lon"
    owner_operator = Column(String(255), nullable=True)

    date_range_start = Column(Date, nullable=False)
    date_range_end = Column(Date, nullable=True)
    regulatory_permit_ref = Column(String(255), nullable=True)
    stakeholder_evidence_ref = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())

    # Relationships
    facility_profile = relationship("PuroFacilityProfile", back_populates="mobile_sites")


class PuroCreditingPeriod(Base):
    """
    Puro.earth Crediting Period.
    10-year initial crediting period. Maximum 2 renewals (up to 30 years total).
    Requires a Production Facility Audit for each renewal.
    """
    __tablename__ = "puro_crediting_periods"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    facility_id = Column(UUID(as_uuid=True), ForeignKey("biochar_production_facilities.id", ondelete="CASCADE"), nullable=False, index=True)

    sequence_number = Column(Integer, nullable=False, default=1)  # 1 (Initial 10y), 2 (First renewal), 3 (Second renewal)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    crediting_duration_years = Column(Integer, nullable=False, default=10)

    methodology_version_id = Column(UUID(as_uuid=True), ForeignKey("puro_methodology_versions.id", ondelete="SET NULL"), nullable=True)
    facility_audit_id = Column(UUID(as_uuid=True), nullable=True)  # Link to PuroAuditWorkflow

    status = Column(String(50), nullable=False, default="ACTIVE")  # PLANNED, ACTIVE, EXPIRED, RENEWAL_DUE, RENEWAL_PENDING_AUDIT, RENEWED, CLOSED
    renewal_type = Column(String(50), nullable=True)  # INITIAL_PERIOD, RENEWAL_1, RENEWAL_2
    renewal_eligibility = Column(Boolean, nullable=False, default=True)
    previous_period_id = Column(UUID(as_uuid=True), ForeignKey("puro_crediting_periods.id", ondelete="SET NULL"), nullable=True)

    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())

    # Relationships
    organization = relationship("Organization")
    facility = relationship("ProductionFacility")


class PuroBaselineAssessment(Base):
    """
    Puro Baseline Scenario determination.
    Scenarios: NEW_FACILITY, RETROFIT_FACILITY, CHARCOAL_REPURPOSE, UNFORESEEN_CASE_REQUIRING_ISSUING_BODY_REVIEW.
    Locked for initial Facility Audit throughout crediting period.
    """
    __tablename__ = "puro_baseline_assessments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    facility_id = Column(UUID(as_uuid=True), ForeignKey("biochar_production_facilities.id", ondelete="CASCADE"), nullable=False, index=True)

    scenario = Column(String(50), nullable=False)  # NEW_FACILITY, RETROFIT_FACILITY, CHARCOAL_REPURPOSE, UNFORESEEN_CASE_REQUIRING_ISSUING_BODY_REVIEW
    is_locked = Column(Boolean, nullable=False, default=True)

    historical_char_production_tpy = Column(Numeric(18, 6), nullable=False, default=0.0)
    baseline_removal_tco2e_per_year = Column(Numeric(18, 6), nullable=False, default=0.0)
    historical_products_description = Column(Text, nullable=True)
    prior_use_fate = Column(String(255), nullable=True)
    baseline_land_use_evidence_type = Column(String(100), nullable=True)  # SATELLITE_IMAGERY, LAND_REGISTRY, PRE_CONSTRUCTION_AUDIT
    land_use_evidence_ref = Column(String(255), nullable=True)

    assessment_status = Column(String(50), nullable=False, default="LOCKED_VALIDATED")  # DATA_REQUIRED, EVIDENCE_REQUIRED, LOCKED_VALIDATED
    reviewed_by = Column(String(255), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())

    # Relationships
    organization = relationship("Organization")
    project = relationship("Project")
    facility = relationship("ProductionFacility")


class PuroAdditionalityAssessment(Base):
    """
    Puro Additionality Assessment:
    1. Carbon additionality (non-baseline decay/burning)
    2. Regulatory additionality (exceeds statutory mandate)
    3. Financial additionality (dependent on CORC revenue)
    """
    __tablename__ = "puro_additionality_assessments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    facility_id = Column(UUID(as_uuid=True), ForeignKey("biochar_production_facilities.id", ondelete="CASCADE"), nullable=False, index=True)

    carbon_additionality_status = Column(String(50), nullable=False, default="PASS")  # PASS, FAIL, DATA_REQUIRED
    regulatory_additionality_status = Column(String(50), nullable=False, default="PASS")  # PASS, FAIL, DATA_REQUIRED
    financial_additionality_status = Column(String(50), nullable=False, default="PASS")  # PASS, FAIL, DATA_REQUIRED
    overall_status = Column(String(50), nullable=False, default="PASS")  # NOT_ASSESSED, DATA_REQUIRED, EVIDENCE_REQUIRED, PASS, FAIL, MANUAL_REVIEW_REQUIRED

    opex_per_tonne = Column(Numeric(14, 2), nullable=True)
    capex_investment = Column(Numeric(14, 2), nullable=True)
    biomass_cost_per_tonne = Column(Numeric(14, 2), nullable=True)
    biochar_market_price_per_tonne = Column(Numeric(14, 2), nullable=True)
    carbon_finance_dependency_pct = Column(Numeric(6, 2), nullable=True)

    legal_mandate_evidence_ref = Column(String(255), nullable=True)
    financial_model_evidence_hash = Column(String(64), nullable=True)

    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())

    # Relationships
    organization = relationship("Organization")
    project = relationship("Project")
    facility = relationship("ProductionFacility")


class PuroBiomassSourceDeclaration(Base):
    """
    Declared Biomass Source registry entry according to Puro Biomass Sourcing Criteria.
    """
    __tablename__ = "puro_biomass_source_declarations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    feedstock_source_id = Column(UUID(as_uuid=True), ForeignKey("biochar_feedstock_sources.id", ondelete="CASCADE"), nullable=False, index=True)

    source_declaration_code = Column(String(50), nullable=False, unique=True, index=True)
    declared_validity_start = Column(Date, nullable=False)
    declared_validity_end = Column(Date, nullable=False)
    puro_category_ref = Column(String(100), nullable=False)  # AGRICULTURAL_RESIDUE, FORESTRY_RESIDUE, BIOGENIC_WASTE
    risk_classification = Column(String(50), nullable=False, default="LOW_RISK")  # LOW_RISK, REQUIRES_AUDIT
    sustainability_certification_scheme = Column(String(100), nullable=True)  # FSC, PEFC, RED_II, SBP
    sustainability_certificate_ref = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)

    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())


class PuroBiomassStorageMonitoring(Base):
    """
    Biomass Stockpiling & Methane Risk Monitoring.
    If storage conditions do not demonstrate negligible methane, routes to project emissions.
    """
    __tablename__ = "puro_biomass_storage_monitoring"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    feedstock_lot_id = Column(UUID(as_uuid=True), ForeignKey("biochar_feedstock_lots.id", ondelete="CASCADE"), nullable=False, index=True)

    storage_start_date = Column(DateTime(timezone=True), nullable=False)
    storage_end_date = Column(DateTime(timezone=True), nullable=True)
    storage_method = Column(String(100), nullable=False, default="AERATED_COVERED_PILE")  # AERATED_COVERED_PILE, UNCOVERED_STATIC_PILE, ENCLOSED_SILO
    turning_frequency_days = Column(Integer, nullable=True)
    moisture_collected_pct = Column(Float, nullable=True)
    pile_temp_celsius = Column(Float, nullable=True)

    methane_risk_status = Column(String(100), nullable=False, default="NEGLIGIBLE_METHANE_DEMONSTRATED")  # NEGLIGIBLE_METHANE_DEMONSTRATED, METHANE_RISK_REQUIRES_QUANTIFICATION
    quantified_methane_emissions_tco2e = Column(Numeric(18, 6), nullable=False, default=0.0)

    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())


class PuroFacilityChangeLog(Base):
    """
    Facility Equipment / Capacity Expansion change log.
    Tracks material equipment alterations, before/after config, notification deadlines, and audit triggers.
    """
    __tablename__ = "puro_facility_change_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    facility_id = Column(UUID(as_uuid=True), ForeignKey("biochar_production_facilities.id", ondelete="CASCADE"), nullable=False, index=True)

    change_type = Column(String(50), nullable=False)  # CAPACITY_EXPANSION, REACTOR_ADDITION, EQUIPMENT_MODIFICATION, PROCESS_PARAMETER_CHANGE
    change_date = Column(Date, nullable=False)
    notification_due_date = Column(Date, nullable=True)
    notification_submitted_date = Column(Date, nullable=True)

    before_configuration_json = Column(JSON, default=dict)
    after_configuration_json = Column(JSON, default=dict)
    output_audit_required = Column(Boolean, nullable=False, default=True)
    issuance_eligibility_date = Column(Date, nullable=True)
    evidence_ref = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())


class PuroCoProductRecord(Base):
    """
    Co-product generation, storage, and emissions impact tracking (pyrolysis gas, bio-oil, bioenergy).
    """
    __tablename__ = "puro_co_product_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    production_run_id = Column(UUID(as_uuid=True), ForeignKey("biochar_production_runs.id", ondelete="CASCADE"), nullable=False, index=True)

    co_product_type = Column(String(50), nullable=False)  # PYROLYSIS_GAS, TAR, BIO_OIL, WOOD_VINEGAR, BIOENERGY, BIOMATERIAL
    quantity = Column(Numeric(18, 6), nullable=False)
    unit = Column(String(20), nullable=False, default="MJ")  # MJ, LITERS, TONNES
    disposition_fate = Column(String(50), nullable=False, default="ENERGY_RECOVERY")  # ENERGY_RECOVERY, ON_SITE_COMBUSTION, OFF_SITE_SALE, HAZARDOUS_DISPOSAL, STORAGE
    emissions_impact_tco2e = Column(Numeric(18, 6), nullable=False, default=0.0)

    storage_containment_details = Column(String(255), nullable=True)
    overflow_control_verified = Column(Boolean, default=True)
    authorization_permit_ref = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())


class PuroSamplingPlan(Base):
    """
    Representative Sampling Plan according to Puro sampling procedures.
    """
    __tablename__ = "puro_sampling_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    facility_id = Column(UUID(as_uuid=True), ForeignKey("biochar_production_facilities.id", ondelete="CASCADE"), nullable=False, index=True)

    plan_code = Column(String(50), nullable=False, unique=True, index=True)
    plan_version = Column(String(20), nullable=False, default="1.0")
    material_type = Column(String(50), nullable=False, default="BIOCHAR_OUTPUT")
    procedure_standard_ref = Column(String(100), nullable=False, default="ISO_18135_COMPOSITE")
    sample_frequency = Column(String(50), nullable=False, default="PER_50_TONNES_OR_BATCH")
    composite_sample_count = Column(Integer, nullable=False, default=5)
    sampling_role = Column(String(100), nullable=False, default="QA_OFFICER")
    laboratory_destination = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="ACTIVE")  # DRAFT, ACTIVE, REVISION_REQUIRED, SUPERSEDED

    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())

    # Relationships
    events = relationship("PuroSamplingEvent", back_populates="plan", cascade="all, delete-orphan")


class PuroSamplingEvent(Base):
    """
    Concrete sampling event linking a physical batch to lab dispatch.
    """
    __tablename__ = "puro_sampling_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("puro_sampling_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("biochar_batches.id", ondelete="CASCADE"), nullable=False, index=True)

    event_code = Column(String(50), nullable=False, unique=True, index=True)
    sampling_date = Column(DateTime(timezone=True), nullable=False)
    sample_collector_name = Column(String(255), nullable=False)
    composite_increments_count = Column(Integer, nullable=False, default=5)
    sample_weight_kg = Column(Float, nullable=False, default=1.0)
    sample_container_id = Column(String(50), nullable=False)
    chain_of_custody_hash = Column(String(64), nullable=True)
    certificate_ref = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())

    # Relationships
    plan = relationship("PuroSamplingPlan", back_populates="events")


class PuroEndUseCategory(Base):
    """
    Official Puro.earth Table 3.2 End-Use Category.
    Categorizes all 28 Table 3.2 codes (AF1-AF5, AH1-AH3, WM1-WM2, EM1-EM2, BE1-BE4, NE1-NE2, R1-R4, IMF1-IMF3, GEO1-GEO3).
    """
    __tablename__ = "puro_end_use_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_code = Column(String(20), nullable=False, unique=True, index=True)  # AF1, BE1, etc.
    category_name = Column(String(255), nullable=False)
    sector = Column(String(100), nullable=False)
    product_type = Column(String(100), nullable=False)
    application_type = Column(String(50), nullable=True)  # SOIL, NON_SOIL
    pure_or_mixed = Column(String(20), nullable=False, default="PURE")  # PURE, MIXED, EITHER
    min_environmental_quality = Column(String(50), nullable=True)  # HIGH, MEDIUM, ANY
    is_corc_eligible = Column(Boolean, nullable=False, default=True)
    default_durability_years = Column(Integer, nullable=False, default=200)
    persistence_factor_non_soil = Column(Float, nullable=True)
    reversal_rules = Column(JSON, default=dict)
    cascading_conditions = Column(JSON, default=dict)
    reversal_discount_factor_required = Column(Boolean, default=False)
    required_evidence_types = Column(JSON, default=list)
    rule_references = Column(JSON, default=list)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())


class PuroEndUseRecordLink(Base):
    """
    Link between physical BiocharEndUseRecord and Puro Table 3.2 Category.
    Validates delivery, application, pure/mixed formulations, cascade stages, and intermediaries.
    """
    __tablename__ = "puro_end_use_record_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("biochar_batches.id", ondelete="CASCADE"), nullable=False, index=True)
    end_use_record_id = Column(UUID(as_uuid=True), ForeignKey("biochar_end_use_records.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("puro_end_use_categories.id", ondelete="CASCADE"), nullable=False, index=True)

    is_pure_biochar = Column(Boolean, nullable=False, default=True)
    formulation_biochar_pct = Column(Float, nullable=False, default=100.0)
    manufacturer_name = Column(String(255), nullable=True)
    intermediary_entity_name = Column(String(255), nullable=True)
    intermediary_agreement_ref = Column(String(255), nullable=True)

    cascade_stage = Column(String(50), nullable=False, default="SINGLE_USE")  # SINGLE_USE, CASCADE_FIRST_USE, CASCADE_SECOND_USE, CASCADE_FINAL_USE
    final_durable_fate_verified = Column(Boolean, nullable=False, default=True)

    proof_of_delivery_ref = Column(String(255), nullable=True)
    application_attestation_ref = Column(String(255), nullable=True)
    gps_verified = Column(Boolean, nullable=False, default=True)
    geotagged_photos_verified = Column(Boolean, nullable=False, default=True)

    corc_point_reached = Column(String(50), nullable=False, default="CORC_POINT_ELIGIBLE")  # CORC_POINT_NOT_REACHED, CORC_POINT_EVIDENCE_PENDING, CORC_POINT_ELIGIBLE, CORC_POINT_INELIGIBLE

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())


class PuroReversalRiskAssessment(Base):
    """
    Reversal Risk Assessment.
    Tracks EXPECTED_STORAGE_LOSS, PRE_ISSUANCE_REEMISSION_RISK, POST_ISSUANCE_REVERSAL.
    """
    __tablename__ = "puro_reversal_risk_assessments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("biochar_batches.id", ondelete="CASCADE"), nullable=False, index=True)

    risk_type = Column(String(50), nullable=False)  # EXPECTED_STORAGE_LOSS, PRE_ISSUANCE_REEMISSION_RISK, POST_ISSUANCE_REVERSAL
    likelihood = Column(String(20), nullable=False, default="LOW")
    potential_impact_tco2e = Column(Numeric(18, 6), nullable=False, default=0.0)
    mitigation_measures = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="ASSESSED")

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())


class PuroReversalEvent(Base):
    """
    Post-Issuance or In-Transit Reversal Event.
    Workflow entity requiring issuing body notification and corrective action.
    """
    __tablename__ = "puro_reversal_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("biochar_batches.id", ondelete="CASCADE"), nullable=False, index=True)

    detection_date = Column(DateTime(timezone=True), nullable=False)
    notification_date = Column(DateTime(timezone=True), nullable=True)
    reversed_quantity_tco2e = Column(Numeric(18, 6), nullable=False)
    root_cause = Column(Text, nullable=False)
    corrective_action_id = Column(UUID(as_uuid=True), nullable=True)
    compensation_status = Column(String(50), nullable=False, default="COMPENSATION_PENDING")  # COMPENSATION_PENDING, BUFFER_RETIRED, RESOLVED

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())


class PuroSafeguardsAssessment(Base):
    """
    Environmental & Social Safeguards status and compliance records.
    """
    __tablename__ = "puro_safeguards_assessments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    facility_id = Column(UUID(as_uuid=True), ForeignKey("biochar_production_facilities.id", ondelete="CASCADE"), nullable=False, index=True)

    permit_status = Column(String(50), nullable=False, default="VERIFIED_CURRENT")  # VERIFIED_CURRENT, EXPIRED, PENDING
    eia_status = Column(String(50), nullable=False, default="EXEMPT_OR_APPROVED")
    worker_safety_status = Column(String(50), nullable=False, default="COMPLIANT")
    stakeholder_grievances_open_count = Column(Integer, nullable=False, default=0)
    local_authority_compliance = Column(Boolean, nullable=False, default=True)
    overall_safeguards_status = Column(String(50), nullable=False, default="COMPLIANT")  # COMPLIANT, FINDINGS_OPEN, ACTION_REQUIRED

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())


class PuroMonitoringPlan(Base):
    """
    Puro Monitoring Plan.
    Versioned operational monitoring practices and parameter collection procedures.
    """
    __tablename__ = "puro_monitoring_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    facility_id = Column(UUID(as_uuid=True), ForeignKey("biochar_production_facilities.id", ondelete="CASCADE"), nullable=False, index=True)

    plan_version = Column(String(20), nullable=False, default="1.0")
    monitoring_parameters_json = Column(JSON, default=dict)
    responsible_roles_json = Column(JSON, default=dict)
    monitoring_frequencies_json = Column(JSON, default=dict)  # MONTHLY, QUARTERLY, etc.
    calibration_schedule_json = Column(JSON, default=dict)
    status = Column(String(50), nullable=False, default="VALIDATED")  # DRAFT, READY_FOR_REVIEW, SUBMITTED, VALIDATED, REVISION_REQUIRED, SUPERSEDED
    validated_at = Column(DateTime(timezone=True), nullable=True)
    auditor_id = Column(UUID(as_uuid=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())


class PuroQualityControlPlan(Base):
    """
    Puro Quality Control Plan.
    Governs data quality checks, emission factor validations, and instrument calibrations.
    """
    __tablename__ = "puro_quality_control_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    facility_id = Column(UUID(as_uuid=True), ForeignKey("biochar_production_facilities.id", ondelete="CASCADE"), nullable=False, index=True)

    qc_plan_code = Column(String(50), nullable=False, unique=True, index=True)
    qc_procedures_json = Column(JSON, default=dict)
    data_quality_thresholds_json = Column(JSON, default=dict)
    check_frequency = Column(String(50), nullable=False, default="PER_BATCH")
    responsible_party = Column(String(100), nullable=False, default="QA_OFFICER")

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())


class PuroQualityControlCheck(Base):
    """
    Execution record of a Quality Control Check on a specific biochar batch or dataset.
    """
    __tablename__ = "puro_quality_control_checks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    qc_plan_id = Column(UUID(as_uuid=True), ForeignKey("puro_quality_control_plans.id", ondelete="CASCADE"), nullable=False, index=True)

    check_date = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    target_entity_type = Column(String(50), nullable=False)  # BATCH, LAB_ANALYSIS, MASS_BALANCE
    target_entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    check_type = Column(String(100), nullable=False)
    passed = Column(Boolean, nullable=False, default=True)
    findings_notes = Column(Text, nullable=True)
    conducted_by = Column(String(255), nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())


class PuroCalculationExecution(Base):
    """
    Persisted, reproducible record of a Puro CORC Quantification execution.
    Stores normalized input manifest, exact calculation breakdown, and canonical SHA-256 hash.
    Supports both AUTHORITATIVE and SIMULATION execution modes.
    """
    __tablename__ = "puro_calculation_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    facility_id = Column(UUID(as_uuid=True), ForeignKey("biochar_production_facilities.id", ondelete="CASCADE"), nullable=False, index=True)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("biochar_batches.id", ondelete="CASCADE"), nullable=False, index=True)
    monitoring_period_id = Column(String(100), nullable=True)

    calculation_mode = Column(String(50), nullable=False, default="AUTHORITATIVE")  # AUTHORITATIVE, SIMULATION
    calculation_timestamp = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    methodology_version = Column(String(50), nullable=False, default="PURO_BIOCHAR_2025_V2")
    coefficient_version = Column(String(50), nullable=False, default="PURO_2025_V2_PERSISTENCE_MATRIX")
    calculation_status = Column(String(50), nullable=False, default="SUCCESS")  # SUCCESS, FAIL_CLOSED, DATA_REQUIRED

    # Core Quantities (tCO2e / Decimal precision)
    eligible_dry_biochar_mass_tonnes = Column(Numeric(18, 6), nullable=False)
    c_org_pct = Column(Float, nullable=False)
    molar_h_c = Column(Float, nullable=False)
    soil_temperature_celsius = Column(Float, nullable=False, default=15.0)

    # Persistence Parameters from Table 6.1 (continuous equation PF = M - a * H/C_org)
    persistence_fraction_pf = Column(Float, nullable=False, default=0.0)  # PF %
    persistence_m_param = Column(Float, nullable=True)  # M from Table 6.1
    persistence_a_param = Column(Float, nullable=True)  # a from Table 6.1
    durability_class = Column(String(50), nullable=False, default="CORC200+")

    c_stored_tco2e = Column(Numeric(18, 6), nullable=False)
    c_baseline_tco2e = Column(Numeric(18, 6), nullable=False, default=0.0)
    c_loss_tco2e = Column(Numeric(18, 6), nullable=False)

    # Project LCA Emissions Breakdown (Section 7)
    e_ops_biomass_tco2e = Column(Numeric(18, 6), nullable=False, default=0.0)
    e_ops_production_tco2e = Column(Numeric(18, 6), nullable=False, default=0.0)
    e_ops_use_tco2e = Column(Numeric(18, 6), nullable=False, default=0.0)
    e_ops_total_tco2e = Column(Numeric(18, 6), nullable=False, default=0.0)
    e_emb_infra_tco2e = Column(Numeric(18, 6), nullable=False, default=0.0)
    e_emb_dluc_tco2e = Column(Numeric(18, 6), nullable=False, default=0.0)
    e_emb_annualized_tco2e = Column(Numeric(18, 6), nullable=False, default=0.0)
    e_project_tco2e = Column(Numeric(18, 6), nullable=False)

    # Leakage Breakdown (Section 8)
    leakage_eco_tco2e = Column(Numeric(18, 6), nullable=False, default=0.0)
    leakage_ma_tco2e = Column(Numeric(18, 6), nullable=False, default=0.0)
    leakage_iluc_tco2e = Column(Numeric(18, 6), nullable=False, default=0.0)
    e_leakage_tco2e = Column(Numeric(18, 6), nullable=False, default=0.0)

    # CORC Quantification & Uncertainty
    net_corcs_calculated = Column(Numeric(18, 6), nullable=False)
    combined_uncertainty_pct = Column(Float, nullable=False, default=5.0)
    deductible_uncertainty_pct = Column(Float, nullable=False, default=0.0)
    final_corcs_issuable = Column(Numeric(18, 6), nullable=False)
    reported_uncertainty_text = Column(String(100), nullable=True)

    input_manifest_json = Column(JSON, nullable=False)
    calculation_hash = Column(String(64), nullable=False, index=True)
    engine_version = Column(String(50), nullable=False, default="2.0.0")

    # Invalidation / Replacement tracking
    superseded_at = Column(DateTime(timezone=True), nullable=True)
    superseded_reason = Column(String(255), nullable=True)
    replacement_engine_version = Column(String(50), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())

    # Relationships
    organization = relationship("Organization")
    project = relationship("Project")
    facility = relationship("ProductionFacility")
    batch = relationship("BiocharBatch")


class PuroAuditWorkflow(Base):
    """
    Puro Audit Workflow.
    Manages PRODUCTION_FACILITY_AUDIT and PURO_OUTPUT_AUDIT lifecycles.
    """
    __tablename__ = "puro_audit_workflows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    facility_id = Column(UUID(as_uuid=True), ForeignKey("biochar_production_facilities.id", ondelete="CASCADE"), nullable=False, index=True)
    monitoring_period_id = Column(String(100), nullable=True)

    audit_type = Column(String(50), nullable=False)  # PRODUCTION_FACILITY_AUDIT, PURO_OUTPUT_AUDIT
    auditor_organization = Column(String(255), nullable=False)
    lead_auditor_name = Column(String(255), nullable=True)
    audit_status = Column(String(50), nullable=False, default="READY_FOR_AUDIT")
    # Statuses: PREPARATION, DOCUMENTS_INCOMPLETE, READY_FOR_AUDIT, AUDIT_SCHEDULED, AUDIT_IN_PROGRESS, FINDINGS_OPEN, CORRECTIVE_ACTION_REQUIRED, READY_FOR_DECISION, PASSED, FAILED, SUSPENDED

    scheduled_date = Column(Date, nullable=True)
    completion_date = Column(Date, nullable=True)
    audit_dossier_hash = Column(String(64), nullable=True)
    certificate_number = Column(String(100), nullable=True)

    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())

    # Relationships
    organization = relationship("Organization")
    facility = relationship("ProductionFacility")
    findings = relationship("PuroAuditFinding", back_populates="audit", cascade="all, delete-orphan")


class PuroAuditFinding(Base):
    """
    Findings and non-conformities raised during a Puro Facility or Output Audit.
    """
    __tablename__ = "puro_audit_findings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(UUID(as_uuid=True), ForeignKey("puro_audit_workflows.id", ondelete="CASCADE"), nullable=False, index=True)

    rule_ref = Column(String(50), nullable=False)
    finding_type = Column(String(50), nullable=False)  # NON_CONFORMITY_MAJOR, NON_CONFORMITY_MINOR, OBSERVATION
    description = Column(Text, nullable=False)
    evidence_ref = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, default="OPEN")  # OPEN, CORRECTIVE_ACTION_SUBMITTED, CLOSED, REJECTED
    detected_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    response_due_date = Column(Date, nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())

    # Relationships
    audit = relationship("PuroAuditWorkflow", back_populates="findings")


class PuroOutputReport(Base):
    """
    Puro Output Report & CORC Report Package.
    Assembles real records, monitoring periods, calculations, and is sealed in cryptographic ledger.
    """
    __tablename__ = "puro_output_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    facility_id = Column(UUID(as_uuid=True), ForeignKey("biochar_production_facilities.id", ondelete="CASCADE"), nullable=False, index=True)
    crediting_period_id = Column(UUID(as_uuid=True), ForeignKey("puro_crediting_periods.id", ondelete="SET NULL"), nullable=True)
    monitoring_period_id = Column(String(100), nullable=False)

    report_number = Column(String(50), nullable=False, unique=True, index=True)
    report_version = Column(Integer, nullable=False, default=1)
    report_status = Column(String(50), nullable=False, default="DRAFT")  # DRAFT, SUBMITTED_FOR_AUDIT, AUDITED_SEALED, SUPERSEDED

    total_eligible_biochar_mass_tonnes = Column(Numeric(18, 6), nullable=False, default=0.0)
    total_net_corcs = Column(Numeric(18, 6), nullable=False, default=0.0)

    manifest_json = Column(JSON, nullable=False)
    manifest_hash = Column(String(64), nullable=False, index=True)
    ledger_signature_id = Column(UUID(as_uuid=True), nullable=True)

    generated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())


class PuroComplianceEvaluation(Base):
    """
    Evaluated compliance state for an individual Puro rule on a project/facility/batch.
    """
    __tablename__ = "puro_compliance_evaluations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    facility_id = Column(UUID(as_uuid=True), ForeignKey("biochar_production_facilities.id", ondelete="CASCADE"), nullable=False, index=True)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("biochar_batches.id", ondelete="SET NULL"), nullable=True, index=True)
    rule_definition_id = Column(UUID(as_uuid=True), ForeignKey("puro_rule_definitions.id", ondelete="CASCADE"), nullable=False, index=True)

    status = Column(String(50), nullable=False, default="NOT_ASSESSED")
    # Statuses: NOT_APPLICABLE, NOT_ASSESSED, DATA_REQUIRED, EVIDENCE_REQUIRED, COMPLIANT, NON_COMPLIANT, CONDITIONALLY_COMPLIANT, MANUAL_REVIEW_REQUIRED, DEPENDENCY_REQUIRED

    evaluation_timestamp = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    evaluator_type = Column(String(50), nullable=False, default="SYSTEM_RULE_ENGINE")
    supporting_record_ids_json = Column(JSON, default=list)
    blocking = Column(Boolean, nullable=False, default=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())

    # Relationships
    rule_definition = relationship("PuroRuleDefinition", back_populates="evaluations")


class PuroCharStreamRecord(Base):
    """
    Multiple Char Stream Record (Puro Rule 3.5.2).
    For facilities with multiple char streams (different pyrolysis conditions or different feedstocks),
    each stream must be accounted for and tested separately.
    """
    __tablename__ = "puro_char_stream_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    facility_id = Column(UUID(as_uuid=True), ForeignKey("biochar_production_facilities.id", ondelete="CASCADE"), nullable=False, index=True)

    stream_code = Column(String(50), nullable=False, index=True)
    stream_name = Column(String(255), nullable=False)
    feedstock_type = Column(String(100), nullable=False)
    pyrolyzer_unit = Column(String(100), nullable=False)
    operating_temperature_celsius = Column(Float, nullable=False)
    residence_time_minutes = Column(Float, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())


class PuroLCAModel(Base):
    """
    Puro Life Cycle Assessment (LCA) Model (Section 7).
    Defines the system boundary, crediting years for annualized embodied emissions, and allocation method.
    """
    __tablename__ = "puro_lca_models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    facility_id = Column(UUID(as_uuid=True), ForeignKey("biochar_production_facilities.id", ondelete="CASCADE"), nullable=False, index=True)

    model_name = Column(String(255), nullable=False)
    system_boundary = Column(String(100), nullable=False, default="CRADLE_TO_GATE_PLUS_DISPOSITION")  # CRADLE_TO_GRAVE, CRADLE_TO_GATE_PLUS_DISPOSITION
    crediting_years = Column(Integer, nullable=False, default=10)
    allocation_method = Column(String(50), nullable=False, default="ENERGY_LHV")  # ENERGY_LHV, NO_ALLOCATION
    status = Column(String(50), nullable=False, default="ACTIVE")

    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())

    # Relationships
    entries = relationship("PuroLCIEntry", back_populates="lca_model", cascade="all, delete-orphan")
    cutoff_decisions = relationship("PuroCutoffDecision", back_populates="lca_model", cascade="all, delete-orphan")


class PuroLCIEntry(Base):
    """
    Life Cycle Inventory Entry (Section 7).
    Covers operational emissions (E_biomass, E_production, E_use) and embodied emissions (E_infra, E_dLUC).
    """
    __tablename__ = "puro_lci_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    lca_model_id = Column(UUID(as_uuid=True), ForeignKey("puro_lca_models.id", ondelete="CASCADE"), nullable=False, index=True)

    category = Column(String(50), nullable=False)  # OPERATIONAL_BIOMASS, OPERATIONAL_PRODUCTION, OPERATIONAL_USE, EMBODIED_INFRASTRUCTURE, EMBODIED_DLUC
    item_name = Column(String(255), nullable=False)
    quantity = Column(Numeric(18, 6), nullable=False)
    unit = Column(String(50), nullable=False)
    emission_factor = Column(Numeric(18, 6), nullable=False)
    ef_unit = Column(String(50), nullable=False)  # e.g. kgCO2e/unit
    ef_source = Column(String(255), nullable=False)  # e.g. Ecoinvent 3.9, IPCC 2019
    ghg_emissions_tco2e = Column(Numeric(18, 6), nullable=False)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())

    # Relationships
    lca_model = relationship("PuroLCAModel", back_populates="entries")


class PuroCutoffDecision(Base):
    """
    LCA Cut-off Decision Documentation (Section 7.2 / ISO 14044).
    Enforces <1% individual stream, <5% cumulative mass and energy cut-off justification.
    """
    __tablename__ = "puro_cutoff_decisions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    lca_model_id = Column(UUID(as_uuid=True), ForeignKey("puro_lca_models.id", ondelete="CASCADE"), nullable=False, index=True)

    input_material_stream = Column(String(255), nullable=False)
    mass_energy_contribution_pct = Column(Float, nullable=False)
    justified_reason = Column(Text, nullable=False)
    auditor_approved = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())

    # Relationships
    lca_model = relationship("PuroLCAModel", back_populates="cutoff_decisions")


class PuroCoProductAllocation(Base):
    """
    Multi-Output Co-Product Allocation Record (Puro Rule 7.5.2b).
    Strictly mandates allocation based on Lower Heating Value (LHV). Mass allocation is prohibited.
    """
    __tablename__ = "puro_coproduct_allocations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    production_run_id = Column(UUID(as_uuid=True), ForeignKey("biochar_production_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    co_product_record_id = Column(UUID(as_uuid=True), ForeignKey("puro_co_product_records.id", ondelete="CASCADE"), nullable=False, index=True)

    allocation_basis = Column(String(50), nullable=False, default="ENERGY_LHV")  # Must be ENERGY_LHV
    biochar_lhv_mj_kg = Column(Float, nullable=False)
    coproduct_lhv_mj_kg = Column(Float, nullable=False)
    biochar_allocation_share_pct = Column(Float, nullable=False)
    coproduct_allocation_share_pct = Column(Float, nullable=False)
    allocated_emissions_tco2e = Column(Numeric(18, 6), nullable=False)
    justification = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())

