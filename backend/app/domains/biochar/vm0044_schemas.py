import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class VM0044ApplicabilityEvaluateRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_id: uuid.UUID
    batch_id: Optional[uuid.UUID] = None
    facility_id: Optional[uuid.UUID] = None
    feedstock_source_ids: Optional[List[uuid.UUID]] = None
    end_use_record_ids: Optional[List[uuid.UUID]] = None


class VM0044ApplicabilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: str = Field(..., description="ELIGIBLE, INELIGIBLE, NEEDS_REVIEW")
    facility_check: Dict[str, Any]
    feedstock_check: Dict[str, Any]
    process_check: Dict[str, Any]
    end_use_check: Dict[str, Any]
    blocking_findings: List[str]
    evaluated_at: datetime


class VM0044AdditionalityEvaluateRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_id: uuid.UUID
    regulatory_surplus_demonstrated: bool = Field(..., description="VCS Step 1: Regulatory surplus demonstrated")
    regulatory_notes: Optional[str] = None
    analysis_option: str = Field("OPTION_2_BENCHMARK_ANALYSIS", description="OPTION_1_INVESTMENT_COMPARISON or OPTION_2_BENCHMARK_ANALYSIS")
    project_irr_pct: Optional[Decimal] = None
    benchmark_irr_pct: Optional[Decimal] = None
    benchmark_source: Optional[str] = None
    financial_model_hash: Optional[str] = None


class VM0044AdditionalityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: str = Field(..., description="COMPLETE, INCOMPLETE, NEEDS_REVIEW, NOT_ADDITIONAL")
    step1_regulatory_surplus: bool
    step2_positive_list: bool
    step3_investment_analysis: bool
    findings: List[str]
    evaluated_at: datetime


class VM0044SnapshotRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_id: uuid.UUID
    batch_id: uuid.UUID
    end_use_record_id: Optional[uuid.UUID] = None
    additionality_id: Optional[uuid.UUID] = None
    technology_class: str = Field("HIGH_TECHNOLOGY", description="HIGH_TECHNOLOGY or LOW_TECHNOLOGY")
    custom_permanence_factor: Optional[Decimal] = None
    grid_electricity_kwh: Decimal = Field(Decimal("0.0"), description="Pre-treatment & auxiliary electricity (kWh)")
    fossil_fuel_litres: Decimal = Field(Decimal("0.0"), description="Pre-treatment & auxiliary fossil fuels (Litres)")
    processing_electricity_kwh: Decimal = Field(Decimal("0.0"), description="Post-production mechanical processing electricity (kWh)")
    processing_fossil_fuel_litres: Decimal = Field(Decimal("0.0"), description="Post-production mechanical processing fuel (Litres)")
    biomass_transport_distance_km: Decimal = Field(Decimal("0.0"), description="Feedstock transport round-trip distance (km)")
    biochar_transport_distance_km: Decimal = Field(Decimal("0.0"), description="Biochar end-use transport round-trip distance (km)")
    uncertainty_pct: Decimal = Field(Decimal("0.0"), description="Uncertainty percentage (e.g. 0.05 for 5%)")


class VM0044SnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    snapshot_id: uuid.UUID
    snapshot_hash: str
    batch_id: uuid.UUID
    project_id: uuid.UUID
    created_at: datetime
    canonical_summary: Dict[str, Any]


class VM0044EquationBreakdown(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    # Production terms
    biochar_dry_mass_tonnes: Decimal
    c_org_fraction: Decimal
    permanence_factor_pr_de: Decimal
    organic_carbon_stored_cc_tonnes: Decimal  # Eq 2 / 6
    gross_co2e_stored_tonnes: Decimal         # CC * 44/12

    # Emission terms
    er_ss_tonnes: Decimal                     # Eq 14 (0.0)
    pe_d_tonnes: Decimal                      # Eq 4 / 8
    pe_p_tonnes: Decimal                      # Eq 9 (0 for high-tech)
    pe_c_tonnes: Decimal                      # Eq 5 / 10
    pe_ps_total_tonnes: Decimal               # Eq 3 / 7
    er_ps_tonnes: Decimal                     # Eq 1
    pe_as_tonnes: Decimal                     # Eq 11 / 12
    e_p_tonnes: Decimal                       # Eq 12
    le_ts_tonnes: Decimal                     # Eq 13
    le_tap_tonnes: Decimal                    # Eq 13
    le_total_tonnes: Decimal                  # Eq 13

    # Removal terms
    er_gross_removals_tonnes: Decimal         # Eq 15 before uncertainty
    uncertainty_pct: Decimal
    uncertainty_deduction_tonnes: Decimal
    er_net_removals_tonnes: Decimal           # Final net tCO2e


class VM0044CalculationRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    snapshot_id: Optional[uuid.UUID] = None
    # Direct input payload if snapshot is not pre-created:
    project_id: Optional[uuid.UUID] = None
    batch_id: Optional[uuid.UUID] = None
    end_use_record_id: Optional[uuid.UUID] = None
    additionality_id: Optional[uuid.UUID] = None
    technology_class: str = "HIGH_TECHNOLOGY"
    custom_permanence_factor: Optional[Decimal] = None
    grid_electricity_kwh: Decimal = Decimal("0.0")
    fossil_fuel_litres: Decimal = Decimal("0.0")
    processing_electricity_kwh: Decimal = Decimal("0.0")
    processing_fossil_fuel_litres: Decimal = Decimal("0.0")
    biomass_transport_distance_km: Decimal = Decimal("0.0")
    biochar_transport_distance_km: Decimal = Decimal("0.0")
    uncertainty_pct: Decimal = Decimal("0.0")
    preview: bool = False


class VM0044CalculationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    calculation_id: uuid.UUID
    snapshot_id: uuid.UUID
    project_id: uuid.UUID
    batch_id: uuid.UUID
    status: str
    methodology_code: str = "VM0044"
    methodology_version: str = "1.2"
    net_removal_tco2e: Optional[Decimal] = None
    gross_removal_tco2e: Optional[Decimal] = None
    project_emissions_tco2e: Optional[Decimal] = None
    leakage_emissions_tco2e: Optional[Decimal] = None
    uncertainty_deduction_tco2e: Optional[Decimal] = None
    equation_breakdown: VM0044EquationBreakdown
    snapshot_hash: str
    calculation_hash: str
    execution_timestamp: datetime
    is_issuable: bool
    ccp_eligible: bool


class VM0044RuleDefinitionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rule_id: str
    section_number: str
    rule_title: str
    requirement_type: str
    equation_reference: Optional[str] = None
    is_blocking: bool
    metadata_json: Dict[str, Any]


class VM0044NormativeDependencySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    title: str
    version: str
    document_type: str
    effective_date: Any
    source_reference: Optional[str] = None
    checksum_hash: Optional[str] = None


class VM0044MethodologyVersionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    version: str
    sectoral_scope: str
    release_date: Any
    status: str
    mitigation_outcome: str
    ccp_approved: bool
    source_url: str
