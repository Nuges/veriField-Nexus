import uuid
from datetime import date, datetime, timezone

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


class FeedstockSource(Base):
    """
    Biochar Feedstock Source entity.
    Identifies origin of biomass, supplier, category, baseline fate, and optional link to an Agriculture LandUnit.
    """
    __tablename__ = "biochar_feedstock_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)

    source_code = Column(String(50), nullable=False, unique=True, index=True)
    source_name = Column(String(255), nullable=False)
    source_type = Column(String(50), nullable=False)  # AGRICULTURAL_RESIDUE, FORESTRY_RESIDUE, MUNICIPAL_BIOMASS, INDUSTRIAL_BIOGENIC
    biomass_type = Column(String(100), nullable=False)  # CROP_RESIDUE, PRUNINGS, WOOD_CHIPS, HUSKS, BAGASSE
    origin_location = Column(String(255), nullable=True)

    # Cross-sector link to Agriculture LandUnit (typed, non-merging)
    source_land_unit_id = Column(UUID(as_uuid=True), ForeignKey("land_units.id", ondelete="SET NULL"), nullable=True, index=True)

    supplier_name = Column(String(255), nullable=True)
    waste_status = Column(String(50), nullable=False, default="CONFIRMED_WASTE_BIOMASS")  # CONFIRMED_WASTE_BIOMASS, RESIDUE, PURPOSE_GROWN
    baseline_fate = Column(String(50), nullable=False, default="OPEN_BURNING")  # DECAY, OPEN_BURNING, DISPOSAL, ENERGY_USE, MATERIAL_USE
    sustainability_status = Column(String(50), nullable=False, default="LOW_RISK")  # VERIFIED_SUSTAINABLE, LOW_RISK, REQUIRES_AUDIT

    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), onupdate=func.now())

    # Relationships
    organization = relationship("Organization")
    project = relationship("Project")
    lots = relationship("FeedstockLot", back_populates="source", cascade="all, delete-orphan")


class FeedstockLot(Base):
    """
    Biochar Feedstock Lot.
    Physical delivery of raw biomass with gross mass, moisture, derived dry mass, and allocation tracking.
    """
    __tablename__ = "biochar_feedstock_lots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    source_id = Column(UUID(as_uuid=True), ForeignKey("biochar_feedstock_sources.id", ondelete="CASCADE"), nullable=False, index=True)

    lot_number = Column(String(50), nullable=False, unique=True, index=True)
    feedstock_type = Column(String(100), nullable=False)
    mass_received_tonnes = Column(Numeric(18, 6), nullable=False)
    moisture_content_pct = Column(Numeric(6, 2), nullable=False)
    dry_mass_tonnes = Column(Numeric(18, 6), nullable=False)
    allocated_mass_tonnes = Column(Numeric(18, 6), nullable=False, default=0.0)
    dry_basis_derivation_method = Column(String(100), nullable=False, default="OVEN_DRY_BASIS_ASTM_D4442")

    receipt_date = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), server_default=func.now())
    storage_location = Column(String(255), nullable=True)
    chain_of_custody_ref = Column(String(100), nullable=True)
    evidence_hash = Column(String(64), nullable=True)

    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())

    # Relationships
    organization = relationship("Organization")
    project = relationship("Project")
    source = relationship("FeedstockSource", back_populates="lots")
    allocations = relationship("FeedstockRunAllocation", back_populates="lot", cascade="all, delete-orphan")


class ProductionFacility(Base):
    """
    Biochar Production Facility.
    Thermal conversion plant, operating status, technology type, commissioning and permits.
    """
    __tablename__ = "biochar_production_facilities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)

    facility_code = Column(String(50), nullable=False, unique=True, index=True)
    facility_name = Column(String(255), nullable=False)
    location = Column(String(255), nullable=True)

    commissioning_date = Column(Date, nullable=True)
    first_biochar_production_date = Column(Date, nullable=True)
    project_start_date = Column(Date, nullable=True)
    facility_status = Column(String(50), nullable=False, default="NEW_OPERATIONAL")  # PLANNED, UNDER_CONSTRUCTION, NEW_OPERATIONAL, EXISTING_OPERATIONAL, DECOMMISSIONED

    operator_name = Column(String(255), nullable=True)
    technology_type = Column(String(100), nullable=False, default="SLOW_PYROLYSIS")  # SLOW_PYROLYSIS, GASIFICATION, RETORT, ROTARY_KILN
    production_capacity_tpy = Column(Float, nullable=True)

    permits_json = Column(JSON, default=dict)
    emissions_controls_json = Column(JSON, default=dict)
    energy_recovery_json = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)

    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())

    # Relationships
    organization = relationship("Organization")
    project = relationship("Project")
    reactors = relationship("FacilityReactor", back_populates="facility", cascade="all, delete-orphan")
    runs = relationship("ProductionRun", back_populates="facility")


class FacilityReactor(Base):
    """
    Biochar Reactor / Production Line.
    Specific kiln, retort, or pyrolyzer equipment within a production facility.
    """
    __tablename__ = "biochar_facility_reactors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    facility_id = Column(UUID(as_uuid=True), ForeignKey("biochar_production_facilities.id", ondelete="CASCADE"), nullable=False, index=True)

    reactor_code = Column(String(50), nullable=False)
    manufacturer = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    technology_type = Column(String(100), nullable=False, default="SLOW_PYROLYSIS")

    design_capacity_kg_h = Column(Float, nullable=True)
    operating_temp_min_c = Column(Float, nullable=True, default=450.0)
    operating_temp_max_c = Column(Float, nullable=True, default=700.0)
    residence_time_min_minutes = Column(Float, nullable=True, default=20.0)
    residence_time_max_minutes = Column(Float, nullable=True, default=60.0)

    is_active = Column(Boolean, default=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())

    # Relationships
    facility = relationship("ProductionFacility", back_populates="reactors")
    runs = relationship("ProductionRun", back_populates="reactor")


class ProductionRun(Base):
    """
    Biochar Production Run.
    A discrete thermochemical operating event consuming feedstock lots and producing biochar mass.
    """
    __tablename__ = "biochar_production_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    facility_id = Column(UUID(as_uuid=True), ForeignKey("biochar_production_facilities.id", ondelete="CASCADE"), nullable=False, index=True)
    reactor_id = Column(UUID(as_uuid=True), ForeignKey("biochar_facility_reactors.id", ondelete="SET NULL"), nullable=True, index=True)

    run_number = Column(String(50), nullable=False, unique=True, index=True)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)

    total_feedstock_input_tonnes = Column(Numeric(18, 6), nullable=False, default=0.0)
    total_feedstock_dry_tonnes = Column(Numeric(18, 6), nullable=False, default=0.0)

    avg_pyrolysis_temp_celsius = Column(Float, nullable=False)
    max_pyrolysis_temp_celsius = Column(Float, nullable=True)
    residence_time_minutes = Column(Float, nullable=False)

    electricity_kwh = Column(Float, nullable=False, default=0.0)
    fuel_liters = Column(Float, nullable=False, default=0.0)
    heat_recovered_mj = Column(Float, nullable=False, default=0.0)

    output_biochar_mass_tonnes = Column(Numeric(18, 6), nullable=False, default=0.0)
    co_products_json = Column(JSON, default=dict)
    operator_id = Column(UUID(as_uuid=True), nullable=True)
    qa_status = Column(String(50), nullable=False, default="LOGGED")  # LOGGED, QA_PASSED, FLAGGED

    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())

    # Relationships
    facility = relationship("ProductionFacility", back_populates="runs")
    reactor = relationship("FacilityReactor", back_populates="runs")
    allocations = relationship("FeedstockRunAllocation", back_populates="run", cascade="all, delete-orphan")
    batches = relationship("BiocharBatch", back_populates="production_run")


class FeedstockRunAllocation(Base):
    """
    Allocation junction table linking Feedstock Lots to Production Runs.
    Enforces atomic allocation checks so sum(allocations) <= lot.mass_received_tonnes.
    """
    __tablename__ = "biochar_feedstock_run_allocations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lot_id = Column(UUID(as_uuid=True), ForeignKey("biochar_feedstock_lots.id", ondelete="CASCADE"), nullable=False, index=True)
    production_run_id = Column(UUID(as_uuid=True), ForeignKey("biochar_production_runs.id", ondelete="CASCADE"), nullable=False, index=True)

    allocated_wet_mass_tonnes = Column(Numeric(18, 6), nullable=False)
    allocated_dry_mass_tonnes = Column(Numeric(18, 6), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())

    # Relationships
    lot = relationship("FeedstockLot", back_populates="allocations")
    run = relationship("ProductionRun", back_populates="allocations")


class BiocharBatch(Base):
    """
    Biochar Batch (Layer 2 MRV Entity).
    First-class traceability and custody object representing pyrolyzed output.
    Maintains complete backward compatibility with existing columns.
    """
    __tablename__ = "biochar_batches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)

    batch_number = Column(String(50), nullable=False, unique=True, index=True)
    facility_name = Column(String(100), nullable=False)
    kiln_id = Column(String(50), nullable=False)

    # Production run linkage
    production_run_id = Column(UUID(as_uuid=True), ForeignKey("biochar_production_runs.id", ondelete="SET NULL"), nullable=True, index=True)

    # Feedstock tracking
    feedstock_type = Column(String(100), nullable=False)
    feedstock_weight_tonnes = Column(Numeric(18, 6), nullable=False)
    moisture_content_pct = Column(Numeric(6, 2), nullable=False)
    origin_location = Column(String(255), nullable=True)

    # Kiln Operations
    pyrolysis_temp_celsius = Column(Float, nullable=False)
    residence_time_minutes = Column(Float, nullable=False)
    kiln_operator_id = Column(UUID(as_uuid=True), nullable=True)

    # Yield & Production
    biochar_yield_tonnes = Column(Numeric(18, 6), nullable=False)
    dry_mass_tonnes = Column(Numeric(18, 6), nullable=True)
    fixed_carbon_pct = Column(Float, nullable=False, default=75.0)
    ash_content_pct = Column(Float, nullable=False, default=5.0)
    molar_h_c_ratio = Column(Float, nullable=False, default=0.4)

    # Permanence & Carbon Removal
    carbon_permanence_factor = Column(Float, nullable=False, default=0.85)
    net_co2e_removed_tonnes = Column(Numeric(18, 6), nullable=False, default=0.0)

    # Quality & Lab Report
    lab_report_number = Column(String(100), nullable=True)
    lab_sample_id = Column(String(100), nullable=True)
    quality_grade = Column(String(20), nullable=False, default="GRADE_A")
    lab_document_url = Column(Text, nullable=True)

    # Status & Anomaly Flags
    status = Column(String(30), nullable=False, default="PRODUCED")  # PRODUCED, LAB_TESTED, IN_STORAGE, AWAITING_END_USE, VERIFIED, CERTIFIED
    has_anomaly = Column(Boolean, default=False)
    anomaly_reason = Column(Text, nullable=True)

    # Carbon Claim Ownership (prevents multi-project double claiming)
    carbon_claim_project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    carbon_claim_registry = Column(String(50), nullable=True)  # VERRA, PURO_STANDARD
    carbon_claim_methodology = Column(String(50), nullable=True)  # VM0044, PURO_BIOCHAR_2025

    # Mass balance tracking
    mass_balance_allocated_tonnes = Column(Numeric(18, 6), nullable=False, default=0.0)
    mass_balance_status = Column(String(50), nullable=False, default="IN_BALANCE")  # IN_BALANCE, OVER_ALLOCATED, FULLY_ALLOCATED
    batch_digest_hash = Column(String(64), nullable=True)

    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), onupdate=func.now())

    # Relationships
    organization = relationship("Organization")
    project = relationship("Project", foreign_keys=[project_id])
    production_run = relationship("ProductionRun", back_populates="batches")
    lab_analyses = relationship("BiocharLabAnalysis", back_populates="batch", cascade="all, delete-orphan")
    material_transactions = relationship("BiocharMaterialTransaction", back_populates="batch", cascade="all, delete-orphan")
    end_uses = relationship("BiocharEndUseRecord", back_populates="batch", cascade="all, delete-orphan")
    storage_events = relationship("BiocharStorageEvent", back_populates="batch", cascade="all, delete-orphan")
    product_allocations = relationship("BiocharIngredientAllocation", back_populates="biochar_batch", cascade="all, delete-orphan")


class BiocharInventory(Base):
    """
    Biochar Inventory (Legacy & simple location snapshot).
    """
    __tablename__ = "biochar_inventories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("biochar_batches.id", ondelete="CASCADE"), nullable=False)
    storage_location = Column(String(200), nullable=False)
    current_stock_tonnes = Column(Float, nullable=False)
    application_soil_type = Column(String(100), nullable=True)
    application_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())


class BiocharLabAnalysis(Base):
    """
    Raw Laboratory Evidence for Biochar Batches.
    Empirical measurements: molar H/C, organic carbon (C_org), ash, moisture, heavy metals, PAHs.
    """
    __tablename__ = "biochar_lab_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("biochar_batches.id", ondelete="CASCADE"), nullable=False, index=True)

    sample_id = Column(String(100), nullable=False)
    sampling_date = Column(DateTime(timezone=True), nullable=False)
    testing_date = Column(DateTime(timezone=True), nullable=True)

    laboratory_name = Column(String(255), nullable=False)
    accreditation_standard = Column(String(100), nullable=True)  # ISO_17025, EBC_CERTIFIED, ILAC
    test_method = Column(String(100), nullable=True)  # DIN_51732, ASTM_D5373, EN_15104

    molar_h_c_ratio = Column(Float, nullable=False)
    organic_carbon_pct = Column(Float, nullable=False)  # C_org
    fixed_carbon_pct = Column(Float, nullable=False)
    moisture_pct = Column(Float, nullable=False)
    ash_pct = Column(Float, nullable=False)
    volatile_matter_pct = Column(Float, nullable=True)

    heavy_metals_pass = Column(Boolean, nullable=False, default=True)
    pah_content_mg_kg = Column(Float, nullable=True)

    lab_report_hash = Column(String(64), nullable=True)
    lab_report_uri = Column(String(500), nullable=True)
    qa_status = Column(String(50), nullable=False, default="VERIFIED")  # PENDING, VERIFIED, FLAGGED

    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())

    # Relationships
    batch = relationship("BiocharBatch", back_populates="lab_analyses")


class BiocharMaterialTransaction(Base):
    """
    Authoritative Material Ledger.
    Tracks custody transformations and dispositions without double-counting intermediate states.
    """
    __tablename__ = "biochar_material_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("biochar_batches.id", ondelete="CASCADE"), nullable=False, index=True)

    transaction_type = Column(String(50), nullable=False)  # PRODUCTION, TRANSFER, STORAGE_IN, STORAGE_OUT, SHIPMENT, DELIVERY, END_USE_ALLOCATION, LOSS, REJECTION, CORRECTION
    quantity_tonnes = Column(Numeric(18, 6), nullable=False)

    from_location = Column(String(255), nullable=True)
    to_location = Column(String(255), nullable=True)
    event_time = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), server_default=func.now())

    source_event_id = Column(UUID(as_uuid=True), nullable=True)
    evidence_hash = Column(String(64), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())

    # Relationships
    batch = relationship("BiocharBatch", back_populates="material_transactions")


class BiocharTransportEvent(Base):
    """
    Logistics & Transport Traceability Event.
    Connects Feedstock Lots or Biochar Batches from origin to destination with verified distance and delivery proof.
    """
    __tablename__ = "biochar_transport_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)

    material_type = Column(String(50), nullable=False)  # FEEDSTOCK_LOT, BIOCHAR_BATCH
    reference_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    origin_address = Column(String(255), nullable=False)
    destination_address = Column(String(255), nullable=False)
    mass_transported_tonnes = Column(Numeric(18, 6), nullable=False)
    distance_km = Column(Float, nullable=False)
    distance_source = Column(String(100), nullable=False, default="VERIFIED_ODOMETER_LOGISTICS")

    transport_mode = Column(String(50), nullable=False, default="ROAD_DIESEL_TRUCK")
    carrier_name = Column(String(255), nullable=True)
    departure_date = Column(DateTime(timezone=True), nullable=False)
    delivery_date = Column(DateTime(timezone=True), nullable=True)
    proof_of_delivery_ref = Column(String(100), nullable=True)
    pod_document_hash = Column(String(64), nullable=True)
    status = Column(String(50), nullable=False, default="DELIVERED")  # DISPATCHED, IN_TRANSIT, DELIVERED, INCIDENT

    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())


class BiocharStorageEvent(Base):
    """
    Storage & Custody Event.
    Tracks inventory presence at a warehouse/location and documents losses.
    """
    __tablename__ = "biochar_storage_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("biochar_batches.id", ondelete="CASCADE"), nullable=False, index=True)

    storage_facility_name = Column(String(255), nullable=False)
    storage_location = Column(String(255), nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=True)

    quantity_stored_tonnes = Column(Numeric(18, 6), nullable=False)
    loss_or_damage_tonnes = Column(Numeric(18, 6), nullable=False, default=0.0)
    storage_conditions = Column(String(255), nullable=False, default="COVERED_DRY_VENTILATED")
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())

    # Relationships
    batch = relationship("BiocharBatch", back_populates="storage_events")


class BiocharEndUseRecord(Base):
    """
    Terminal End-Use Record.
    Final disposition where biochar achieves permanent carbon removal:
    - SOIL_APPLICATION: linked to Agriculture LandUnit, application rate, photos, GPS, wetland exclusion.
    - NON_SOIL_APPLICATION: durable product incorporation (concrete, asphalt, building materials).
    """
    __tablename__ = "biochar_end_use_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("biochar_batches.id", ondelete="CASCADE"), nullable=False, index=True)

    end_use_type = Column(String(50), nullable=False)  # SOIL_APPLICATION, NON_SOIL_APPLICATION
    applied_quantity_tonnes = Column(Numeric(18, 6), nullable=False)
    event_date = Column(DateTime(timezone=True), nullable=False)

    # Soil Application Fields
    source_land_unit_id = Column(UUID(as_uuid=True), ForeignKey("land_units.id", ondelete="SET NULL"), nullable=True, index=True)
    application_rate_tonnes_per_ha = Column(Numeric(12, 4), nullable=True)
    area_hectares = Column(Numeric(12, 4), nullable=True)
    application_method = Column(String(100), nullable=True)  # BROADCAST_INCORPORATED, TRENCH_DEPOSIT, SEED_FURROW
    gps_coordinates = Column(String(100), nullable=True)
    wetland_exclusion_screened = Column(Boolean, nullable=False, default=True)
    crop_type = Column(String(100), nullable=True)

    # Non-Soil Application Fields
    product_category = Column(String(100), nullable=True)  # CONCRETE_READYMIX, ASPHALT_ADDITIVE, BUILDING_PANEL, COMPOSITE
    recipient_organization = Column(String(255), nullable=True)
    durability_classification = Column(String(100), nullable=True)  # DURABLE_BUILDING_MATERIAL, INFRASTRUCTURE_ASPHALT

    proof_photos_json = Column(JSON, default=list)
    verification_status = Column(String(50), nullable=False, default="PENDING_VERIFICATION")  # PENDING_VERIFICATION, VERIFIED, REJECTED

    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())

    # Relationships
    organization = relationship("Organization")
    project = relationship("Project")
    batch = relationship("BiocharBatch", back_populates="end_uses")


class BiocharCarbonPoolClaim(Base):
    """
    Explicit Carbon Pool Claim entity.
    Enforces carbon pool claim uniqueness across projects, land units, and crediting/monitoring periods.
    Supports extensible conflict resolution (e.g. VM0044 vs VM0042 for SOIL_ORGANIC_CARBON).
    """
    __tablename__ = "biochar_carbon_pool_claims"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("biochar_batches.id", ondelete="SET NULL"), nullable=True, index=True)
    land_unit_id = Column(UUID(as_uuid=True), ForeignKey("land_units.id", ondelete="SET NULL"), nullable=True, index=True)

    methodology_code = Column(String(50), nullable=False, index=True)
    carbon_pool = Column(String(50), nullable=False, default="SOIL_ORGANIC_CARBON", index=True)
    claim_type = Column(String(50), nullable=False, default="EX_POST")  # EX_ANTE, EX_POST

    period_start_date = Column(Date, nullable=False, index=True)
    period_end_date = Column(Date, nullable=False, index=True)

    claim_status = Column(String(50), nullable=False, default="PROPOSED")  # PROPOSED, ACTIVE, CONFIRMED, BLOCKED_CONFLICT, SUPERSEDED
    conflict_flag = Column(Boolean, default=False)
    conflict_details = Column(JSON, default=dict)

    claimed_tco2e = Column(Numeric(18, 6), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), onupdate=func.now())

    # Relationships
    organization = relationship("Organization")
    project = relationship("Project")


class BiocharProductFormulation(Base):
    """
    Biochar Mixed Product Formulation.
    Defines recipes for blending biochar into end-use products (e.g. soil amendments, compost blends,
    building materials, asphalt/concrete mixes).
    """
    __tablename__ = "biochar_product_formulations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)

    product_name = Column(String(255), nullable=False)
    product_code = Column(String(50), nullable=False, unique=True, index=True)
    target_sector = Column(String(100), nullable=False)  # AGRICULTURE_SOIL_AMENDMENT, URBAN_GREENING, CONSTRUCTION_CONCRETE, WATER_TREATMENT
    description = Column(Text, nullable=True)
    biochar_target_ratio = Column(Float, nullable=False, default=0.5)
    is_active = Column(Boolean, nullable=False, default=True)

    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), onupdate=func.now())

    # Relationships
    organization = relationship("Organization")
    project = relationship("Project")
    batches = relationship("BiocharProductBatch", back_populates="formulation", cascade="all, delete-orphan")


class BiocharProductBatch(Base):
    """
    Manufactured batch of mixed biochar product.
    Contains mass balance accounting for pure biochar fraction and non-biochar ingredients.
    """
    __tablename__ = "biochar_product_batches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    formulation_id = Column(UUID(as_uuid=True), ForeignKey("biochar_product_formulations.id", ondelete="CASCADE"), nullable=False, index=True)

    batch_number = Column(String(50), nullable=False, unique=True, index=True)
    production_date = Column(DateTime(timezone=True), nullable=False)
    total_product_mass_tonnes = Column(Numeric(18, 6), nullable=False)
    biochar_mass_tonnes = Column(Numeric(18, 6), nullable=False)
    non_biochar_mass_tonnes = Column(Numeric(18, 6), nullable=False, default=0.0)
    packaging_type = Column(String(100), nullable=True)
    storage_location = Column(String(255), nullable=True)
    qa_status = Column(String(50), nullable=False, default="APPROVED")

    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())

    # Relationships
    organization = relationship("Organization")
    project = relationship("Project")
    formulation = relationship("BiocharProductFormulation", back_populates="batches")
    ingredient_allocations = relationship("BiocharIngredientAllocation", back_populates="product_batch", cascade="all, delete-orphan")
    non_biochar_ingredients = relationship("BiocharProductNonBiocharIngredient", back_populates="product_batch", cascade="all, delete-orphan")


class BiocharIngredientAllocation(Base):
    """
    Junction entity allocating pure BiocharBatch tonnes into a BiocharProductBatch.
    Guarantees anti-overallocation: sum(allocated_biochar_mass_tonnes) <= biochar_batch.biochar_yield_tonnes.
    """
    __tablename__ = "biochar_product_ingredient_allocations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_batch_id = Column(UUID(as_uuid=True), ForeignKey("biochar_product_batches.id", ondelete="CASCADE"), nullable=False, index=True)
    biochar_batch_id = Column(UUID(as_uuid=True), ForeignKey("biochar_batches.id", ondelete="CASCADE"), nullable=False, index=True)

    allocated_biochar_mass_tonnes = Column(Numeric(18, 6), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())

    # Relationships
    product_batch = relationship("BiocharProductBatch", back_populates="ingredient_allocations")
    biochar_batch = relationship("BiocharBatch", back_populates="product_allocations")


class BiocharProductNonBiocharIngredient(Base):
    """
    Non-biochar ingredients in a mixed product batch (e.g. compost, sand, binder, microbes).
    """
    __tablename__ = "biochar_product_non_biochar_ingredients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_batch_id = Column(UUID(as_uuid=True), ForeignKey("biochar_product_batches.id", ondelete="CASCADE"), nullable=False, index=True)

    ingredient_name = Column(String(255), nullable=False)
    ingredient_type = Column(String(100), nullable=False)  # COMPOST, MINERAL_FERTILIZER, SAND, CLAY, CEMENT, BINDER
    mass_tonnes = Column(Numeric(18, 6), nullable=False)
    mass_pct = Column(Float, nullable=False)
    cas_number = Column(String(50), nullable=True)
    supplier = Column(String(255), nullable=True)

    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())

    # Relationships
    product_batch = relationship("BiocharProductBatch", back_populates="non_biochar_ingredients")


# Re-export Puro.earth Biochar Edition 2025 V2 methodology models
from app.domains.biochar.puro_models import (
    PuroMethodologyVersion,
    PuroRuleDefinition,
    PuroNormativeDependency,
    PuroSupplierProfile,
    PuroFacilityProfile,
    PuroMobileProductionSite,
    PuroCreditingPeriod,
    PuroBaselineAssessment,
    PuroAdditionalityAssessment,
    PuroBiomassSourceDeclaration,
    PuroBiomassStorageMonitoring,
    PuroFacilityChangeLog,
    PuroCoProductRecord,
    PuroSamplingPlan,
    PuroSamplingEvent,
    PuroEndUseCategory,
    PuroEndUseRecordLink,
    PuroReversalRiskAssessment,
    PuroReversalEvent,
    PuroSafeguardsAssessment,
    PuroMonitoringPlan,
    PuroQualityControlPlan,
    PuroQualityControlCheck,
    PuroCalculationExecution,
    PuroAuditWorkflow,
    PuroAuditFinding,
    PuroOutputReport,
    PuroComplianceEvaluation,
    PuroCharStreamRecord,
    PuroLCAModel,
    PuroLCIEntry,
    PuroCutoffDecision,
    PuroCoProductAllocation,
)
