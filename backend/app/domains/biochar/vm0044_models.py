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


class VM0044MethodologyVersion(Base):
    """
    Verra VM0044 Methodology Version Locking Entity.
    Guarantees immutable rule sets and version gating for VM0044 v1.2.
    """
    __tablename__ = "vm0044_methodology_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), nullable=False, default="VM0044", index=True)
    name = Column(String(255), nullable=False, default="Biochar Utilization in Soil and Non-Soil Applications")
    version = Column(String(50), nullable=False, default="1.2", index=True)
    sectoral_scope = Column(String(50), nullable=False, default="13")
    release_date = Column(Date, nullable=False, default=date(2025, 6, 27))
    status = Column(String(50), nullable=False, default="ACTIVE")  # ACTIVE, DRAFT, SUPERSEDED, RETIRED
    mitigation_outcome = Column(String(50), nullable=False, default="REMOVALS")
    ccp_approved = Column(Boolean, nullable=False, default=True)
    source_url = Column(String(500), nullable=False, default="https://verra.org/methodologies/vm0044-biochar-utilization-in-soil-and-non-soil-applications-v1-2/")
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())

    # Relationships
    rules = relationship("VM0044RuleDefinition", back_populates="methodology_version", cascade="all, delete-orphan")
    normative_dependencies = relationship("VM0044NormativeDependency", back_populates="methodology_version", cascade="all, delete-orphan")


class VM0044RuleDefinition(Base):
    """
    Methodology Rule Definition for Verra VM0044 v1.2.
    Defines section-by-section requirements across applicability, additionality, boundary, and equations.
    """
    __tablename__ = "vm0044_rule_definitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    methodology_version_id = Column(UUID(as_uuid=True), ForeignKey("vm0044_methodology_versions.id", ondelete="CASCADE"), nullable=False, index=True)

    rule_id = Column(String(50), nullable=False, unique=True, index=True)  # e.g., "VM0044-AP-01", "VM0044-EQ-15"
    section_number = Column(String(50), nullable=False)  # "4", "7", "8.2.2.1", "8.5"
    rule_title = Column(String(255), nullable=False)
    requirement_type = Column(String(50), nullable=False)  # APPLICABILITY, ADDITIONALITY, QUANTIFICATION, MONITORING, LEAKAGE
    equation_reference = Column(String(50), nullable=True)  # "Equation (15)"
    is_blocking = Column(Boolean, nullable=False, default=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())

    # Relationships
    methodology_version = relationship("VM0044MethodologyVersion", back_populates="rules")


class VM0044NormativeDependency(Base):
    """
    External Normative Document Dependency for VM0044 v1.2.
    Tracks required external specifications (VCS Standard v4.5, VT0008 v1.0, CDM TOOL03, TOOL05, TOOL12, TOOL16, IPCC 2019).
    """
    __tablename__ = "vm0044_normative_dependencies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    methodology_version_id = Column(UUID(as_uuid=True), ForeignKey("vm0044_methodology_versions.id", ondelete="CASCADE"), nullable=False, index=True)

    code = Column(String(50), nullable=False, unique=True, index=True)  # e.g., "VT0008_V1_0"
    title = Column(String(255), nullable=False)
    version = Column(String(50), nullable=False)
    document_type = Column(String(100), nullable=False)  # STANDARD, TOOL, GUIDELINE
    effective_date = Column(Date, nullable=False)
    source_reference = Column(String(500), nullable=True)
    checksum_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())

    # Relationships
    methodology_version = relationship("VM0044MethodologyVersion", back_populates="normative_dependencies")


class VM0044ApplicabilityEvaluation(Base):
    """
    Section 4 Applicability Evaluation Record.
    Evaluates greenfield status, biogenic waste biomass, process technology, and end-use conditions.
    """
    __tablename__ = "vm0044_applicability_evaluations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("biochar_batches.id", ondelete="SET NULL"), nullable=True, index=True)

    evaluation_date = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    facility_greenfield_passed = Column(Boolean, nullable=False, default=False)
    feedstock_biogenic_waste_passed = Column(Boolean, nullable=False, default=False)
    feedstock_geographic_origin_passed = Column(Boolean, nullable=False, default=False)
    process_technology_passed = Column(Boolean, nullable=False, default=False)
    end_use_eligibility_passed = Column(Boolean, nullable=False, default=False)
    wetland_exclusion_passed = Column(Boolean, nullable=False, default=True)
    worker_health_safety_passed = Column(Boolean, nullable=False, default=True)

    overall_applicability_status = Column(String(50), nullable=False, default="INELIGIBLE")  # ELIGIBLE, INELIGIBLE, NEEDS_REVIEW
    findings_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())

    # Relationships
    organization = relationship("Organization")
    project = relationship("Project")
    batch = relationship("BiocharBatch")


class VM0044AdditionalityAssessment(Base):
    """
    Section 7 Additionality Assessment & VT0008 Record.
    Enforces Step 1 (regulatory surplus), Step 2 (positive list applicability), and Step 3 (investment analysis).
    """
    __tablename__ = "vm0044_additionality_assessments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)

    assessment_date = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    step1_regulatory_surplus_passed = Column(Boolean, nullable=False, default=False)
    step1_regulatory_notes = Column(Text, nullable=True)

    step2_positive_list_passed = Column(Boolean, nullable=False, default=False)
    step2_penetration_rate_pct = Column(Numeric(6, 3), nullable=False, default=5.0)

    step3_investment_analysis_passed = Column(Boolean, nullable=False, default=False)
    step3_analysis_option = Column(String(50), nullable=False, default="OPTION_2_BENCHMARK_ANALYSIS")  # OPTION_1_INVESTMENT_COMPARISON, OPTION_2_BENCHMARK_ANALYSIS
    project_irr_pct = Column(Numeric(6, 3), nullable=True)
    benchmark_irr_pct = Column(Numeric(6, 3), nullable=True)
    benchmark_source = Column(String(255), nullable=True)

    overall_additionality_status = Column(String(50), nullable=False, default="INCOMPLETE")  # COMPLETE, INCOMPLETE, NEEDS_REVIEW, NOT_ADDITIONAL
    evidence_hashes_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())

    # Relationships
    organization = relationship("Organization")
    project = relationship("Project")


class VM0044CalculationSnapshot(Base):
    """
    Immutable VM0044 Calculation Input Snapshot.
    Stores exact canonical JSON representation of all calculation inputs and its SHA-256 digest.
    """
    __tablename__ = "vm0044_calculation_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("biochar_batches.id", ondelete="CASCADE"), nullable=False, index=True)

    methodology_code = Column(String(50), nullable=False, default="VM0044")
    methodology_version = Column(String(50), nullable=False, default="1.2")
    snapshot_timestamp = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    snapshot_canonical_json = Column(Text, nullable=False)
    snapshot_hash = Column(String(64), nullable=False, unique=True, index=True)

    created_by_user_id = Column(UUID(as_uuid=True), nullable=True)
    is_locked = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())

    # Relationships
    organization = relationship("Organization")
    project = relationship("Project")
    batch = relationship("BiocharBatch")
    executions = relationship("VM0044CalculationExecution", back_populates="snapshot")


class VM0044CalculationExecution(Base):
    """
    Authoritative VM0044 Calculation Execution Output.
    Stores the full lifecycle result of Equations (1) through (15) with high precision.
    """
    __tablename__ = "vm0044_calculation_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("biochar_batches.id", ondelete="CASCADE"), nullable=False, index=True)
    snapshot_id = Column(UUID(as_uuid=True), ForeignKey("vm0044_calculation_snapshots.id", ondelete="RESTRICT"), nullable=False, index=True)

    calculation_version = Column(Integer, nullable=False, default=1)
    execution_timestamp = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    status = Column(String(50), nullable=False, default="CALCULATED")  # PREVIEW, READY, CALCULATED, VERIFIED, REJECTED, SUPERSEDED

    # Physical parameters & configuration
    technology_class = Column(String(50), nullable=False)  # HIGH_TECHNOLOGY, LOW_TECHNOLOGY
    end_use_pathway = Column(String(50), nullable=False)  # SOIL_APPLICATION, NON_SOIL_APPLICATION
    pyrolysis_temp_celsius = Column(Float, nullable=False)
    biochar_dry_mass_tonnes = Column(Numeric(18, 6), nullable=False)
    c_org_fraction = Column(Numeric(8, 6), nullable=False)
    permanence_factor_pr_de = Column(Numeric(6, 4), nullable=False)

    # Core Equation Terms (Equations 1 - 15)
    organic_carbon_stored_cc_tonnes = Column(Numeric(18, 6), nullable=False)  # CC_t,k,y (Eq 2 / Eq 6)
    gross_co2e_stored_tonnes = Column(Numeric(18, 6), nullable=False)         # CC * 44/12

    er_ss_tonnes = Column(Numeric(18, 6), nullable=False, default=0.0)        # Eq 14 (Sourcing stage = 0)
    pe_d_tonnes = Column(Numeric(18, 6), nullable=False, default=0.0)         # Eq 4 / Eq 8 (Pre-treatment)
    pe_p_tonnes = Column(Numeric(18, 6), nullable=False, default=0.0)         # Eq 9 (Pyrolysis methane, 0 for high-tech)
    pe_c_tonnes = Column(Numeric(18, 6), nullable=False, default=0.0)         # Eq 5 / Eq 10 (Auxiliary energy)
    pe_ps_total_tonnes = Column(Numeric(18, 6), nullable=False, default=0.0)  # Eq 3 / Eq 7 (Total production PE)
    er_ps_tonnes = Column(Numeric(18, 6), nullable=False)                     # Eq 1 (Production stage net removals)

    pe_as_tonnes = Column(Numeric(18, 6), nullable=False, default=0.0)        # Eq 11 / Eq 12 (Application processing)
    le_ts_tonnes = Column(Numeric(18, 6), nullable=False, default=0.0)        # Eq 13 (Biomass transport > 200km)
    le_tap_tonnes = Column(Numeric(18, 6), nullable=False, default=0.0)       # Eq 13 (Biochar transport > 200km)
    le_total_tonnes = Column(Numeric(18, 6), nullable=False, default=0.0)     # Eq 13 (Total leakage)

    er_gross_removals_tonnes = Column(Numeric(18, 6), nullable=False)         # Eq 15 (Net removals before uncertainty)
    uncertainty_pct = Column(Numeric(6, 3), nullable=False, default=0.0)
    uncertainty_deduction_tonnes = Column(Numeric(18, 6), nullable=False, default=0.0)
    er_net_removals_tonnes = Column(Numeric(18, 6), nullable=False)           # Final net removals in tCO2e

    # Cryptographic integrity and lineage
    calculation_hash = Column(String(64), nullable=False, index=True)
    equation_breakdown_json = Column(JSON, default=dict)
    audit_trail_json = Column(JSON, default=dict)
    qa_status = Column(String(50), nullable=False, default="PENDING")
    verified_by_user_id = Column(UUID(as_uuid=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), onupdate=func.now())

    # Relationships
    organization = relationship("Organization")
    project = relationship("Project")
    batch = relationship("BiocharBatch")
    snapshot = relationship("VM0044CalculationSnapshot", back_populates="executions")


# Indices for high-concurrency lookups and deduplication
Index("idx_vm0044_calc_project_status", VM0044CalculationExecution.project_id, VM0044CalculationExecution.status)
Index("idx_vm0044_calc_batch_version", VM0044CalculationExecution.batch_id, VM0044CalculationExecution.calculation_version)
Index("idx_vm0044_snap_batch", VM0044CalculationSnapshot.batch_id, VM0044CalculationSnapshot.snapshot_hash)
