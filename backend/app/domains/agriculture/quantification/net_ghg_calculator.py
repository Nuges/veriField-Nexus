"""
VeriField Nexus — Agriculture Domain: Net GHG Reductions & Removals Engine
==========================================================================
Authoritative implementation of Verra VM0042 v2.2 (21 October 2025)
and 11 June 2026 Corrections & Clarifications (C&C):
- Section 8.2 & 8.3: Sourced Baseline and Project Emissions by Source
- Section 8.4: Leakage Accounting (Activity displacement, livestock displacement,
  11 June 2026 C&C production decline via VMD0054 modifications, TOOL16 biomass energy)
- Section 8.5.1: Carbon Stock Change Completion (Equations 44 & 45)
- Section 8.5: Net GHG Quantification (Equations 37–43)
- Section 8.7: Internal VCU Readiness & NPR Buffer Deductions (Equations 75–79)
- Table 5: Canonical Applicability Router & Fail-Closed Integrity
- Multi-Year Vintage Accounting: Prevents collapsed undated totals
"""

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_EVEN, InvalidOperation
from enum import Enum
import hashlib
import json
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union


class NetGHGCalculationError(Exception):
    """Base exception for Net GHG and VCU readiness calculation failures."""
    def __init__(self, code: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


# Canonical Stoichiometric and Conversion Constants
CO2_TO_C_RATIO = Decimal("44") / Decimal("12")      # 3.66666667
N2O_TO_N_RATIO = Decimal("44") / Decimal("28")      # 1.57142857

# Default IPCC AR5 Global Warming Potentials (100-year time horizon without climate-carbon feedbacks, per VCS v4.x)
GWP_AR5_CO2 = Decimal("1")
GWP_AR5_CH4 = Decimal("28")
GWP_AR5_N2O = Decimal("265")

# Default IPCC AR6 Global Warming Potentials (VCS v5.0)
GWP_AR6_CO2 = Decimal("1")
GWP_AR6_CH4 = Decimal("27.9")
GWP_AR6_N2O = Decimal("273")

# Precision policies
PRECISION_DECIMAL = Decimal("0.0001")     # 4 decimal places for tCO2e/yr
PRECISION_FRACTION = Decimal("0.000001")  # 6 decimal places for rates/fractions
PRECISION_PERCENT = Decimal("0.0001")    # 4 decimal places for %


class ApplicabilityStatus(str, Enum):
    APPLICABLE_CONFIGURED = "APPLICABLE_CONFIGURED"
    APPLICABLE_NOT_CONFIGURED = "APPLICABLE_NOT_CONFIGURED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    EXCLUDED_WITH_METHODOLOGY_JUSTIFICATION = "EXCLUDED_WITH_METHODOLOGY_JUSTIFICATION"


class ActivityDataStatus(str, Enum):
    VERIFIED_ACTIVITY_ZERO = "VERIFIED_ACTIVITY_ZERO"
    MEASURED = "MEASURED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    MISSING_DATA = "MISSING_DATA"
    NOT_CONFIGURED = "NOT_CONFIGURED"


class QuantificationApproach(str, Enum):
    QA1_MEASURE_AND_MODEL = "QA1_MEASURE_AND_MODEL"
    QA2_MEASURE_AND_REMEASURE = "QA2_MEASURE_AND_REMEASURE"
    QA3_ACTIVITY_METHOD = "QA3_ACTIVITY_METHOD"
    NOT_CONFIGURED = "NOT_CONFIGURED"


@dataclass
class GWPConfig:
    """Authoritative Global Warming Potential configuration."""
    gwp_co2: Decimal = GWP_AR5_CO2
    gwp_ch4: Decimal = GWP_AR5_CH4
    gwp_n2o: Decimal = GWP_AR5_N2O
    ipcc_assessment: str = "IPCC_AR5"
    vcs_requirement_version: str = "VCS_STANDARD_V4_7"
    effective_ruleset: str = "VM0042_V2.2_RULES_CC20260611_V1.0"


@dataclass
class SourceApplicabilityItem:
    """Applicability status and rationale for a single Table 5 source or pool."""
    source_category: str  # e.g. CO2_SOC, CO2_FOSSIL_FUEL, CO2_LIMING, N2O_NITROGEN_FERTILIZERS, etc.
    gas: str              # CO2, CH4, N2O
    status: ApplicabilityStatus
    quantification_approach: QuantificationApproach
    activity_data_status: ActivityDataStatus
    rationale: str
    evidence_reference: Optional[str] = None


@dataclass
class FossilFuelActivity:
    """Activity data and factor for fossil fuel combustion."""
    fuel_type: str             # DIESEL, GASOLINE, LPG, NATURAL_GAS
    quantity: Decimal          # in unit
    unit: str                  # LITERS, KG, M3
    emission_factor_tco2e_per_unit: Decimal
    factor_source: str         # e.g. IPCC 2006 Vol 2 Table 3.2.1
    is_verified_zero: bool = False


@dataclass
class LimingActivity:
    """Activity data for liming application."""
    calcitic_limestone_tonnes: Decimal = Decimal("0.0000")
    dolomite_tonnes: Decimal = Decimal("0.0000")
    is_verified_zero: bool = False
    notes: str = ""


@dataclass
class FertilizerN2OActivity:
    """Activity data for nitrogen fertilizer application."""
    fertilizer_type: str       # SYNTHETIC_UREA, ANHYDROUS_AMMONIA, ORGANIC_COMPOST, MANURE_SLURRY
    mass_kg: Decimal
    n_fraction: Decimal        # Fraction of N (e.g. 0.46 for urea)
    ef1_direct: Decimal = Decimal("0.0100")        # 1.0% direct N2O-N per kg N
    frac_gasm_volatilization: Decimal = Decimal("0.1000")
    ef4_volatilization: Decimal = Decimal("0.0100")
    frac_leach: Decimal = Decimal("0.3000")
    ef5_leaching: Decimal = Decimal("0.0075")
    is_verified_zero: bool = False


@dataclass
class NitrogenFixingActivity:
    """Activity data for nitrogen-fixing species."""
    species_name: str
    area_ha: Decimal
    estimated_n_fixed_kg_ha: Decimal
    ef1: Decimal = Decimal("0.0100")
    is_verified_zero: bool = False


@dataclass
class ManureDepositionActivity:
    """Activity data for manure deposition by grazing livestock."""
    livestock_category: str    # DAIRY_CATTLE, OTHER_CATTLE, SHEEP, GOATS
    head_count: int
    ef_ch4_kg_head_yr: Decimal = Decimal("1.5000")
    nex_kg_n_head_yr: Decimal = Decimal("40.0000")
    ef_prp_n2o: Decimal = Decimal("0.0200")
    is_verified_zero: bool = False


@dataclass
class EntericFermentationActivity:
    """Activity data for livestock enteric fermentation."""
    livestock_category: str    # DAIRY_CATTLE, BEEF_CATTLE, BUFFALO, SHEEP
    head_count: int
    ef_ch4_kg_head_yr: Decimal = Decimal("55.0000")  # IPCC Tier 1 default
    is_verified_zero: bool = False


@dataclass
class BiomassBurningActivity:
    """Activity data for biomass burning."""
    dry_matter_tonnes: Decimal
    combustion_factor: Decimal = Decimal("0.8000")
    gef_ch4_g_kg: Decimal = Decimal("2.7000")
    gef_n2o_g_kg: Decimal = Decimal("0.0700")
    is_verified_zero: bool = False


@dataclass
class SoilMethanogenesisActivity:
    """Soil methanogenesis activity (flooded rice / wetland)."""
    qa1_model_configured: bool = False
    qa1_model_id: Optional[str] = None
    annual_ch4_emissions_tco2e: Optional[Decimal] = None
    is_verified_zero: bool = False


@dataclass
class WoodyBiomassPoolData:
    """Woody biomass tree and shrub pools status and stocks."""
    tree_pool_status: ApplicabilityStatus = ApplicabilityStatus.NOT_APPLICABLE
    shrub_pool_status: ApplicabilityStatus = ApplicabilityStatus.NOT_APPLICABLE
    baseline_tree_stock_change_tco2e_yr: Decimal = Decimal("0.0000")
    baseline_shrub_stock_change_tco2e_yr: Decimal = Decimal("0.0000")
    project_tree_stock_change_tco2e_yr: Decimal = Decimal("0.0000")
    project_shrub_stock_change_tco2e_yr: Decimal = Decimal("0.0000")
    harvested_wood_lta_applicable: bool = False
    harvested_wood_lta_configured: bool = False
    is_verified_zero: bool = True
    justification: str = "Project boundary excludes woody biomass; land units are dedicated annual cropland."


class VMD0054Version(str, Enum):
    VMD0054_1_1_CURRENT = "VMD0054_1_1_CURRENT"
    VMD0054_1_0_TRANSITION_ELIGIBLE = "VMD0054_1_0_TRANSITION_ELIGIBLE"
    VMD0054_VERSION_UNRESOLVED = "VMD0054_VERSION_UNRESOLVED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass
class LeakageInputData:
    """Leakage assessment input data under VM0042 Section 8.4 and 11 June 2026 C&C."""
    activity_displacement_tco2e_yr: Decimal = Decimal("0.0000")
    livestock_displacement_tco2e_yr: Decimal = Decimal("0.0000")
    leoa_tco2e_yr: Optional[Decimal] = None  # Ecological leakage outside project boundary (LK_act + LK_ls)
    # Production decline leakage (C&C 11 June 2026 + VMD0054)
    production_decline_leakage_tco2e_yr: Decimal = Decimal("0.0000")  # LKdisp,t
    production_decline_evaluated: bool = True
    commodity_name: Optional[str] = None
    yield_change_pct: Optional[Decimal] = None
    vmd0054_version: Union[VMD0054Version, str] = VMD0054Version.VMD0054_1_1_CURRENT.value
    vmd0054_cumulative_leakage_tco2e: Optional[Decimal] = None
    vmd0054_prior_leakage_tco2e: Optional[Decimal] = None
    vmd0054_verification_period_years: Optional[Decimal] = None
    vmd0054_transition_eligible: Optional[bool] = None
    vmd0054_transition_basis: Optional[str] = None
    vmd0054_source_equation: Optional[str] = None
    vmd0054_effective_ruleset: Optional[str] = None
    production_decline_status: str = "EVALUATED"  # EVALUATED, NOT_APPLICABLE
    production_decline_evidence: Optional[str] = None
    # Transition Governance Fields (Verra submission deadline & request type)
    project_request_type: Optional[str] = None
    verification_subtype: Optional[str] = None
    verra_request_id: Optional[str] = None
    transition_document_id: Optional[str] = None
    submission_date: Optional[date] = None
    transition_deadline: Optional[date] = None
    transition_evidence: Optional[str] = None
    transition_governance: Dict[str, Any] = field(default_factory=dict)
    # Detailed VMD0054 Component Trace Inputs
    al_t_ha: Optional[Decimal] = None
    delta_c_biomass_tc_ha: Optional[Decimal] = None
    delta_soc_tc_ha: Optional[Decimal] = None
    delta_cs_tc_ha: Optional[Decimal] = None
    elm_t_tco2e: Optional[Decimal] = None
    # Biomass residue diversion leakage (TOOL16)
    biomass_residue_diversion_tco2e_yr: Decimal = Decimal("0.0000")  # LEBR,t
    residue_baseline_energy_used: bool = False
    tool16_procedure_reference: Optional[str] = "TOOL16_PROCEDURE"
    tool16_status: str = "EVALUATED"  # EVALUATED, NOT_APPLICABLE
    tool16_not_applicable_reason: Optional[str] = None
    is_verified_zero: bool = False


@dataclass
class NPRRiskAssessmentInput:
    """Authoritative VCS AFOLU Non-Permanence Risk assessment."""
    npr_rating_pct: Decimal  # e.g. Decimal("15.0000") for 15%
    risk_assessment_id: uuid.UUID
    approval_status: str     # APPROVED, VALIDATED
    effective_date: str      # ISO date
    version: str = "1.0"


@dataclass
class AnnualVintageGHGResult:
    """Authoritative net GHG and VCU readiness result for a single calendar vintage year."""
    vintage_year: int
    # Emissions breakdown (tCO2e/yr)
    e_fossil_fuel_bsl: Decimal
    e_fossil_fuel_wp: Decimal
    e_liming_bsl: Decimal
    e_liming_wp: Decimal
    e_fert_n2o_bsl: Decimal
    e_fert_n2o_wp: Decimal
    e_nfix_bsl: Decimal
    e_nfix_wp: Decimal
    e_manure_ch4_bsl: Decimal
    e_manure_ch4_wp: Decimal
    e_manure_n2o_bsl: Decimal
    e_manure_n2o_wp: Decimal
    e_enteric_ch4_bsl: Decimal
    e_enteric_ch4_wp: Decimal
    e_biomass_burn_ch4_bsl: Decimal
    e_biomass_burn_ch4_wp: Decimal
    e_biomass_burn_n2o_bsl: Decimal
    e_biomass_burn_n2o_wp: Decimal
    e_soil_ch4_bsl: Decimal
    e_soil_ch4_wp: Decimal
    # Total emissions by scenario
    total_baseline_emissions_tco2e: Decimal
    total_project_emissions_tco2e: Decimal
    total_emission_reductions_from_sources_tco2e: Decimal
    # Carbon stock changes (tCO2e/yr)
    soc_stock_change_bsl_tco2e: Decimal
    soc_stock_change_wp_tco2e: Decimal
    soc_stock_uncertainty_deduction_tco2e: Decimal
    soc_uncertainty_adjusted_effect_tco2e: Decimal
    woody_stock_change_bsl_tco2e: Decimal
    woody_stock_change_wp_tco2e: Decimal
    # Equation 44 & 45 Total Carbon Stock Changes
    eq44_baseline_total_carbon_stock_change_tco2e: Decimal
    eq45_project_total_carbon_stock_change_tco2e: Decimal
    eq44_eq45_status: str
    cumulative_project_stock_change_tco2e: Decimal
    i_delta_co2_wp: int  # 1 if cumulative stock > 0, else 0
    # Leakage
    lk_activity_displacement_tco2e: Decimal
    lk_livestock_displacement_tco2e: Decimal
    lk_production_decline_tco2e: Decimal
    lk_biomass_residue_tco2e: Decimal
    total_leakage_tco2e: Decimal
    # Equations 37–43
    gross_reductions_er_tco2e: Decimal
    gross_removals_cr_tco2e: Decimal
    leakage_allocation_er_lker_tco2e: Decimal
    leakage_allocation_cr_lkcr_tco2e: Decimal
    net_reductions_ernet_tco2e: Decimal
    net_removals_crnet_tco2e: Decimal
    total_net_ghg_errnet_tco2e: Decimal
    # Section 8.7 VCU Readiness (Eqs 75–79)
    npr_rating_pct: Optional[Decimal] = None
    buffer_deduction_reductions_tco2e: Optional[Decimal] = None
    buffer_deduction_removals_tco2e: Optional[Decimal] = None
    total_buffer_deduction_tco2e: Optional[Decimal] = None
    internal_vcu_eligible_reductions_tco2e: Optional[Decimal] = None
    internal_vcu_eligible_removals_tco2e: Optional[Decimal] = None
    internal_vcu_eligible_total_tco2e: Optional[Decimal] = None
    vcu_readiness_status: str = "NOT_CONFIGURED"
    # Detailed leakage & stock breakdown
    leoa_leakage_tco2e: Decimal = Decimal("0.0000")
    lkdisp_leakage_tco2e: Decimal = Decimal("0.0000")
    lebr_leakage_tco2e: Decimal = Decimal("0.0000")
    stock_reductions_term_tco2e: Decimal = Decimal("0.0000")
    leakage_allocation_status: str = "CALCULATED"
    vmd0054_version: str = "VMD0054_1_1_CURRENT"
    vmd0054_source_equation: str = "VMD0054_V1.1_EQ13"
    vmd0054_transition_basis: Optional[str] = None
    vmd0054_effective_ruleset: str = "VMD0054_V1.1_ACTIVE"
    vmd0054_trace: Dict[str, Any] = field(default_factory=dict)
    transition_governance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            k: (str(v) if isinstance(v, Decimal) else v)
            for k, v in asdict(self).items()
        }


@dataclass
class NetGHGProjectOutput:
    """Aggregated multi-vintage Net GHG and VCU readiness result for the verification period."""
    project_id: uuid.UUID
    organization_id: uuid.UUID
    verification_period_start: date
    verification_period_end: date
    elapsed_years: Decimal
    methodology_code: str = "VM0042"
    methodology_version: str = "2.2"
    corrections_clarifications_version: str = "2026-06-11"
    calculation_engine_version: str = "VM0042_V2_2_NET_GHG_V1.0"
    ruleset_version: str = "VM0042_V2.2_RULES_CC20260611_V1.0"
    vmd0054_version: str = "VMD0054_1_1_CURRENT"
    vmd0054_source_equation: str = "VMD0054_V1.1_EQ13"
    vmd0054_transition_basis: Optional[str] = None
    vmd0054_effective_ruleset: str = "VMD0054_V1.1_ACTIVE"
    vmd0054_trace: Dict[str, Any] = field(default_factory=dict)
    transition_governance: Dict[str, Any] = field(default_factory=dict)
    # Table 5 Applicability Snapshot
    applicability_matrix: Dict[str, Any] = field(default_factory=dict)
    # Aggregated totals across verification period
    total_baseline_emissions_tco2e: Decimal = Decimal("0.0000")
    total_project_emissions_tco2e: Decimal = Decimal("0.0000")
    total_emission_reductions_from_sources_tco2e: Decimal = Decimal("0.0000")
    # Carbon stock changes
    eq44_baseline_total_carbon_stock_change_tco2e: Decimal = Decimal("0.0000")
    eq45_project_total_carbon_stock_change_tco2e: Decimal = Decimal("0.0000")
    eq44_eq45_status: str = "CALCULATED"
    # Equations 37–43 Aggregates
    gross_reductions_er_tco2e: Decimal = Decimal("0.0000")
    gross_removals_cr_tco2e: Decimal = Decimal("0.0000")
    total_leakage_tco2e: Decimal = Decimal("0.0000")
    total_leoa_tco2e: Decimal = Decimal("0.0000")
    total_lkdisp_tco2e: Decimal = Decimal("0.0000")
    total_lebr_tco2e: Decimal = Decimal("0.0000")
    leakage_allocation_status: str = "CALCULATED"
    leakage_allocation_er_lker_tco2e: Decimal = Decimal("0.0000")
    leakage_allocation_cr_lkcr_tco2e: Decimal = Decimal("0.0000")
    net_reductions_ernet_tco2e: Decimal = Decimal("0.0000")
    net_removals_crnet_tco2e: Decimal = Decimal("0.0000")
    total_net_ghg_errnet_tco2e: Decimal = Decimal("0.0000")
    # Section 8.7 VCU Readiness Aggregates
    npr_rating_pct: Optional[Decimal] = None
    risk_assessment_id: Optional[str] = None
    buffer_deduction_reductions_tco2e: Optional[Decimal] = None
    buffer_deduction_removals_tco2e: Optional[Decimal] = None
    total_buffer_deduction_tco2e: Optional[Decimal] = None
    internal_vcu_eligible_reductions_tco2e: Optional[Decimal] = None
    internal_vcu_eligible_removals_tco2e: Optional[Decimal] = None
    internal_vcu_eligible_total_tco2e: Optional[Decimal] = None
    vcu_readiness_status: str = "NOT_CONFIGURED"
    # Statuses
    internal_mrv_status: str = "CALCULATED"
    vvb_status: str = "NOT_CONFIGURED / EXTERNAL"
    registry_status: str = "NOT_CONFIGURED / EXTERNAL"
    ledger_status: str = "BLOCKED_FOR_AGRICULTURE"
    result_status: str = "CALCULATED"
    calculation_hash: str = ""
    input_snapshot_hash: str = ""
    vintages: List[AnnualVintageGHGResult] = field(default_factory=list)
    component_breakdown: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Component Calculation Functions
# =============================================================================

def calculate_fossil_fuel_emissions(
    activities: List[FossilFuelActivity],
) -> Decimal:
    """Calculates emissions from fossil fuel combustion in tCO2e/yr."""
    total = Decimal("0.0000")
    for act in activities:
        if act.is_verified_zero:
            continue
        if act.quantity < Decimal("0.0"):
            raise NetGHGCalculationError("INVALID_ACTIVITY_DATA", f"Fuel quantity cannot be negative: {act.quantity}")
        e = act.quantity * act.emission_factor_tco2e_per_unit
        total += e
    return total.quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)


def calculate_liming_emissions(
    activity: LimingActivity,
) -> Decimal:
    """
    Calculates emissions from liming in tCO2e/yr using IPCC 2006 Vol 4 Ch 11 stoichiometry:
    Calcitic limestone: 0.12 * 44/12 = 0.4400 tCO2/t
    Dolomite: 0.13 * 44/12 = 0.47666667 tCO2/t
    """
    if activity.is_verified_zero:
        return Decimal("0.0000")
    if activity.calcitic_limestone_tonnes < Decimal("0.0") or activity.dolomite_tonnes < Decimal("0.0"):
        raise NetGHGCalculationError("INVALID_ACTIVITY_DATA", "Liming material mass cannot be negative.")
    ef_calcitic = Decimal("0.12") * CO2_TO_C_RATIO
    ef_dolomite = Decimal("0.13") * CO2_TO_C_RATIO
    total = (activity.calcitic_limestone_tonnes * ef_calcitic) + (activity.dolomite_tonnes * ef_dolomite)
    return total.quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)


def calculate_fertilizer_n2o_emissions(
    activities: List[FertilizerN2OActivity],
    gwp_n2o: Decimal = GWP_AR5_N2O,
) -> Decimal:
    """
    Calculates N2O emissions from synthetic and organic fertilizer inputs in tCO2e/yr.
    Includes direct emissions and indirect emissions (volatilization and leaching).
    """
    total = Decimal("0.0000")
    for act in activities:
        if act.is_verified_zero:
            continue
        if act.mass_kg < Decimal("0.0") or act.n_fraction < Decimal("0.0"):
            raise NetGHGCalculationError("INVALID_ACTIVITY_DATA", "Fertilizer mass or N fraction cannot be negative.")
        n_input_kg = act.mass_kg * act.n_fraction
        # Direct N2O-N (kg N2O-N)
        n_direct = n_input_kg * act.ef1_direct
        # Indirect volatilization (kg N2O-N)
        n_volat = n_input_kg * act.frac_gasm_volatilization * act.ef4_volatilization
        # Indirect leaching (kg N2O-N)
        n_leach = n_input_kg * act.frac_leach * act.ef5_leaching
        total_n2o_n_kg = n_direct + n_volat + n_leach
        # Convert N2O-N to N2O (44/28)
        total_n2o_kg = total_n2o_n_kg * N2O_TO_N_RATIO
        # Convert kg N2O to tCO2e (10^-3 * GWP_N2O)
        tco2e = total_n2o_kg * Decimal("0.001") * gwp_n2o
        total += tco2e
    return total.quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)


def calculate_nfixing_emissions(
    activities: List[NitrogenFixingActivity],
    gwp_n2o: Decimal = GWP_AR5_N2O,
) -> Decimal:
    """Calculates N2O emissions from nitrogen-fixing species in tCO2e/yr."""
    total = Decimal("0.0000")
    for act in activities:
        if act.is_verified_zero:
            continue
        n_fixed_total_kg = act.area_ha * act.estimated_n_fixed_kg_ha
        n2o_n_kg = n_fixed_total_kg * act.ef1
        n2o_kg = n2o_n_kg * N2O_TO_N_RATIO
        tco2e = n2o_kg * Decimal("0.001") * gwp_n2o
        total += tco2e
    return total.quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)


def calculate_manure_deposition_emissions(
    activities: List[ManureDepositionActivity],
    gwp_ch4: Decimal = GWP_AR5_CH4,
    gwp_n2o: Decimal = GWP_AR5_N2O,
) -> Tuple[Decimal, Decimal]:
    """Calculates (CH4_tco2e, N2O_tco2e) from manure deposition on pasture/paddock/rangeland."""
    ch4_total = Decimal("0.0000")
    n2o_total = Decimal("0.0000")
    for act in activities:
        if act.is_verified_zero:
            continue
        if act.head_count < 0:
            raise NetGHGCalculationError("INVALID_ACTIVITY_DATA", "Livestock head count cannot be negative.")
        # CH4
        ch4_kg = Decimal(str(act.head_count)) * act.ef_ch4_kg_head_yr
        ch4_tco2e = ch4_kg * Decimal("0.001") * gwp_ch4
        ch4_total += ch4_tco2e
        # N2O
        n_excreted_kg = Decimal(str(act.head_count)) * act.nex_kg_n_head_yr
        n2o_n_kg = n_excreted_kg * act.ef_prp_n2o
        n2o_kg = n2o_n_kg * N2O_TO_N_RATIO
        n2o_tco2e = n2o_kg * Decimal("0.001") * gwp_n2o
        n2o_total += n2o_tco2e
    return (
        ch4_total.quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN),
        n2o_total.quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN),
    )


def calculate_enteric_fermentation_emissions(
    activities: List[EntericFermentationActivity],
    gwp_ch4: Decimal = GWP_AR5_CH4,
) -> Decimal:
    """Calculates CH4 emissions from livestock enteric fermentation in tCO2e/yr."""
    total = Decimal("0.0000")
    for act in activities:
        if act.is_verified_zero:
            continue
        if act.head_count < 0:
            raise NetGHGCalculationError("INVALID_ACTIVITY_DATA", "Livestock head count cannot be negative.")
        ch4_kg = Decimal(str(act.head_count)) * act.ef_ch4_kg_head_yr
        ch4_tco2e = ch4_kg * Decimal("0.001") * gwp_ch4
        total += ch4_tco2e
    return total.quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)


def calculate_biomass_burning_emissions(
    activities: List[BiomassBurningActivity],
    gwp_ch4: Decimal = GWP_AR5_CH4,
    gwp_n2o: Decimal = GWP_AR5_N2O,
) -> Tuple[Decimal, Decimal]:
    """Calculates (CH4_tco2e, N2O_tco2e) from biomass burning in tCO2e/yr."""
    ch4_total = Decimal("0.0000")
    n2o_total = Decimal("0.0000")
    for act in activities:
        if act.is_verified_zero:
            continue
        if act.dry_matter_tonnes < Decimal("0.0"):
            raise NetGHGCalculationError("INVALID_ACTIVITY_DATA", "Burned biomass mass cannot be negative.")
        # M_burn * C_f is burned fuel mass in tonnes (10^3 kg)
        fuel_kg = act.dry_matter_tonnes * Decimal("1000") * act.combustion_factor
        # CH4 emission = fuel_kg * (gef_ch4 / 1000) kg CH4
        ch4_kg = fuel_kg * act.gef_ch4_g_kg * Decimal("0.001")
        ch4_tco2e = ch4_kg * Decimal("0.001") * gwp_ch4
        ch4_total += ch4_tco2e
        # N2O emission = fuel_kg * (gef_n2o / 1000) kg N2O
        n2o_kg = fuel_kg * act.gef_n2o_g_kg * Decimal("0.001")
        n2o_tco2e = n2o_kg * Decimal("0.001") * gwp_n2o
        n2o_total += n2o_tco2e
    return (
        ch4_total.quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN),
        n2o_total.quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN),
    )


# =============================================================================
# Standalone VM0042 Equations 37–43 & 75–79 Calculation Functions
# =============================================================================

VERRA_TRANSITION_DEADLINE_2027_01_31 = date(2027, 1, 31)
VERRA_TRANSITION_RULE_VERSION = "VERRA_VMD0054_TRANSITION_RULE_V1.1_CC20260611"


class VerraTransitionRequestCategory(str, Enum):
    """
    Official Verra Transition Request Categories under published VMD0054 transition rules:
    A. REGISTRATION
    B. VERIFICATION_APPROVAL_BASELINE_REASSESSMENT
    C. VERIFICATION_APPROVAL_METHODOLOGY_CHANGE_PD_DEVIATION
    D. CREDITING_PERIOD_RENEWAL
    E. REQUANTIFICATION
    """
    REGISTRATION = "REGISTRATION"
    VERIFICATION_APPROVAL_BASELINE_REASSESSMENT = "VERIFICATION_APPROVAL_BASELINE_REASSESSMENT"
    VERIFICATION_APPROVAL_METHODOLOGY_CHANGE_PD_DEVIATION = "VERIFICATION_APPROVAL_METHODOLOGY_CHANGE_PD_DEVIATION"
    CREDITING_PERIOD_RENEWAL = "CREDITING_PERIOD_RENEWAL"
    REQUANTIFICATION = "REQUANTIFICATION"


class VerraVerificationSubtype(str, Enum):
    """Subtypes qualifying a verification approval for VMD0054 v1.0 transition."""
    BASELINE_REASSESSMENT = "BASELINE_REASSESSMENT"
    METHODOLOGY_CHANGE_PD_DEVIATION = "METHODOLOGY_CHANGE_PD_DEVIATION"


VALID_VERRA_TRANSITION_REQUEST_TYPES = {
    VerraTransitionRequestCategory.REGISTRATION.value,
    "REGISTRATION_REQUEST",
    VerraTransitionRequestCategory.VERIFICATION_APPROVAL_BASELINE_REASSESSMENT.value,
    VerraTransitionRequestCategory.VERIFICATION_APPROVAL_METHODOLOGY_CHANGE_PD_DEVIATION.value,
    VerraTransitionRequestCategory.CREDITING_PERIOD_RENEWAL.value,
    VerraTransitionRequestCategory.REQUANTIFICATION.value,
}

DISALLOWED_GENERIC_CATEGORIES = {
    "VALIDATION_LISTING_REQUEST",
    "VALIDATION_LISTING",
    "PROJECT_DESCRIPTION_SUBMISSION",
    "METHODOLOGY_UPDATE_REQUEST",
    "METHODOLOGY_UPDATE",
    "VERIFICATION_REQUEST",
    "VERIFICATION_APPROVAL",
}


def classify_verra_transition_request(
    request_type: Optional[str],
    verification_subtype: Optional[str] = None,
) -> Tuple[Optional[VerraTransitionRequestCategory], Optional[str], Optional[str]]:
    """
    Classifies a project request into one of the 5 official Verra transition categories:
    A. REGISTRATION
    B. VERIFICATION_APPROVAL_BASELINE_REASSESSMENT
    C. VERIFICATION_APPROVAL_METHODOLOGY_CHANGE_PD_DEVIATION
    D. CREDITING_PERIOD_RENEWAL
    E. REQUANTIFICATION

    Disallows generic categories from independently qualifying:
    - VALIDATION_LISTING_REQUEST
    - PROJECT_DESCRIPTION_SUBMISSION
    - generic METHODOLOGY_UPDATE_REQUEST
    - generic VERIFICATION_REQUEST / VERIFICATION_APPROVAL (without qualifying subtype)

    Returns:
        (category, effective_verification_subtype, error_reason)
    """
    if not request_type:
        return None, None, "MISSING_PROJECT_REQUEST_TYPE"

    req_norm = request_type.strip().upper()
    sub_norm = verification_subtype.strip().upper() if verification_subtype else None

    # Disallowed: VALIDATION_LISTING / VALIDATION_LISTING_REQUEST
    if req_norm in ("VALIDATION_LISTING", "VALIDATION_LISTING_REQUEST"):
        return None, None, "VALIDATION_LISTING_DOES_NOT_ESTABLISH_TRANSITION_ELIGIBILITY"

    # Disallowed: PROJECT_DESCRIPTION_SUBMISSION
    if req_norm in ("PROJECT_DESCRIPTION_SUBMISSION", "PROJECT_DESCRIPTION"):
        return None, None, "PROJECT_DESCRIPTION_SUBMISSION_DOES_NOT_ESTABLISH_TRANSITION_ELIGIBILITY"

    # Disallowed: generic METHODOLOGY_UPDATE_REQUEST
    if req_norm in ("METHODOLOGY_UPDATE_REQUEST", "METHODOLOGY_UPDATE"):
        return None, None, "GENERIC_METHODOLOGY_UPDATE_DOES_NOT_ESTABLISH_TRANSITION_ELIGIBILITY"

    # A. REGISTRATION
    if req_norm in ("REGISTRATION", "REGISTRATION_REQUEST"):
        return VerraTransitionRequestCategory.REGISTRATION, None, None

    # B. VERIFICATION_APPROVAL_BASELINE_REASSESSMENT
    if req_norm in (
        "VERIFICATION_APPROVAL_BASELINE_REASSESSMENT",
        "VERIFICATION_BASELINE_REASSESSMENT",
    ):
        return (
            VerraTransitionRequestCategory.VERIFICATION_APPROVAL_BASELINE_REASSESSMENT,
            VerraVerificationSubtype.BASELINE_REASSESSMENT.value,
            None,
        )

    # C. VERIFICATION_APPROVAL_METHODOLOGY_CHANGE_PD_DEVIATION
    if req_norm in (
        "VERIFICATION_APPROVAL_METHODOLOGY_CHANGE_PD_DEVIATION",
        "VERIFICATION_APPROVAL_PD_DEVIATION",
        "VERIFICATION_METHODOLOGY_CHANGE_PD_DEVIATION",
    ):
        return (
            VerraTransitionRequestCategory.VERIFICATION_APPROVAL_METHODOLOGY_CHANGE_PD_DEVIATION,
            VerraVerificationSubtype.METHODOLOGY_CHANGE_PD_DEVIATION.value,
            None,
        )

    # Generic verification approval or request: qualifies ONLY if explicit qualifying subtype is present
    if req_norm in ("VERIFICATION_APPROVAL", "VERIFICATION_REQUEST", "VERIFICATION"):
        if sub_norm in ("BASELINE_REASSESSMENT",):
            return (
                VerraTransitionRequestCategory.VERIFICATION_APPROVAL_BASELINE_REASSESSMENT,
                VerraVerificationSubtype.BASELINE_REASSESSMENT.value,
                None,
            )
        elif sub_norm in (
            "METHODOLOGY_CHANGE_PD_DEVIATION",
            "PD_DEVIATION",
            "METHODOLOGY_CHANGE_THROUGH_A_PROJECT_DESCRIPTION_DEVIATION",
        ):
            return (
                VerraTransitionRequestCategory.VERIFICATION_APPROVAL_METHODOLOGY_CHANGE_PD_DEVIATION,
                VerraVerificationSubtype.METHODOLOGY_CHANGE_PD_DEVIATION.value,
                None,
            )
        else:
            return (
                None,
                sub_norm,
                "GENERIC_VERIFICATION_DOES_NOT_QUALIFY_WITHOUT_BASELINE_REASSESSMENT_OR_PD_DEVIATION",
            )

    # D. CREDITING_PERIOD_RENEWAL
    if req_norm in ("CREDITING_PERIOD_RENEWAL", "CREDITING_PERIOD_RENEWAL_REQUEST"):
        return VerraTransitionRequestCategory.CREDITING_PERIOD_RENEWAL, None, None

    # E. REQUANTIFICATION
    if req_norm in ("REQUANTIFICATION", "REQUANTIFICATION_REQUEST"):
        return VerraTransitionRequestCategory.REQUANTIFICATION, None, None

    return None, sub_norm, f"INVALID_PROJECT_REQUEST_TYPE_{request_type}"


def calculate_vmd0054_v11_equation_11_delta_cs(
    delta_c_biomass_tc_ha: Decimal,
    delta_soc_tc_ha: Decimal,
) -> Decimal:
    """
    VMD0054 v1.1 Equation 11:
    Delta_CS = Delta_C_biomass + Delta_SOC (t C/ha)
    Change in carbon stocks on newly brought-into-production land.
    NOTE: Equation 11 outputs t C/ha (carbon stock intensity), NOT cumulative leakage tCO2e.
    """
    return (delta_c_biomass_tc_ha + delta_soc_tc_ha).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)


def calculate_vmd0054_v11_equation_13_cumulative_leakage(
    al_t_ha: Decimal,
    delta_cs_tc_ha: Decimal,
    elm_t_tco2e: Decimal = Decimal("0.0000"),
) -> Decimal:
    """
    VMD0054 v1.1 Equation 13:
    LK_t = AL_t * Delta_CS * (44/12) + ELM_t (tCO2e)
    Cumulative market leakage from agricultural production decline up to year t.
    NOTE: Equation 13 outputs cumulative leakage in tCO2e, which supplies LK_t to VM0042 Eq. 36.
    """
    c_to_co2 = Decimal("44") / Decimal("12")
    biomass_soc_co2 = al_t_ha * delta_cs_tc_ha * c_to_co2
    total_lk = biomass_soc_co2 + elm_t_tco2e
    return total_lk.quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)


def calculate_vmd0054_v10_equation_10_cumulative_leakage(
    al_t_ha: Decimal,
    delta_cs_tc_ha: Decimal,
    elm_t_tco2e: Decimal = Decimal("0.0000"),
) -> Decimal:
    """
    VMD0054 v1.0 Equation 10 (Transition Route):
    LK_t = cumulative leakage up to year t (tCO2e).
    Valid strictly for projects meeting Verra pre-2027 transition criteria.
    """
    c_to_co2 = Decimal("44") / Decimal("12")
    total_lk = (al_t_ha * delta_cs_tc_ha * c_to_co2) + elm_t_tco2e
    return total_lk.quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)


def calculate_vm0042_equation_36_market_leakage(
    lk_t_tco2e: Decimal,
    lk_prior_tco2e: Decimal = Decimal("0.0000"),
    verification_period_years: Decimal = Decimal("1.0000"),
) -> Decimal:
    """
    VM0042 corrected Equation 36 (11 June 2026 C&C):
    LKdisp,t = MAX(0, LK_t - LK_prior) / years (tCO2e/yr)
    Allocates cumulative production decline leakage over the verification period.
    Consumes cumulative LK_t from VMD0054 v1.1 Eq. 13 (or v1.0 Eq. 10).
    Units: LK_t (tCO2e), LK_prior (tCO2e), years (yr) -> LKdisp,t (tCO2e/yr).
    """
    if verification_period_years <= Decimal("0.0000"):
        raise NetGHGCalculationError("INVALID_PERIOD", "Verification period years must be strictly positive.")
    delta_lk = max(Decimal("0.0000"), lk_t_tco2e - lk_prior_tco2e)
    lkdisp = delta_lk / verification_period_years
    return lkdisp.quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)


class VMD0054ResolutionResult(tuple):
    """
    4-tuple compatible result (version, source_equation, transition_basis, effective_ruleset)
    with attached structured governance metadata.
    """
    def __new__(
        cls,
        ver: VMD0054Version,
        eq: str,
        basis: str,
        ruleset: str,
        governance: Optional[Dict[str, Any]] = None,
    ):
        instance = super().__new__(cls, (ver, eq, basis, ruleset))
        instance.version = ver
        instance.source_equation = eq
        instance.transition_basis = basis
        instance.effective_ruleset = ruleset
        instance.governance = governance or {}
        return instance

    def __repr__(self) -> str:
        return f"VMD0054ResolutionResult(version={self[0]}, source_equation={self[1]}, transition_basis={self[2]}, effective_ruleset={self[3]})"


def resolve_vmd0054_version(
    vmd0054_version_input: Optional[Union[VMD0054Version, str]] = None,
    transition_eligible: Optional[bool] = None,
    transition_basis: Optional[str] = None,
    production_decline_status: str = "EVALUATED",
    submission_date: Optional[date] = None,
    start_date: Optional[date] = None,
    project_request_type: Optional[str] = None,
    verification_subtype: Optional[str] = None,
    verra_request_id: Optional[str] = None,
    transition_document_id: Optional[str] = None,
    transition_evidence: Optional[str] = None,
) -> VMD0054ResolutionResult:
    """
    Resolve authoritative VMD0054 module version, source equation, transition basis, and effective ruleset.

    Pursuant to Verra VM0042 v2.2 and official VMD0054 transition guidance:
    - VMD0054 v1.1 is ACTIVE (default for current standard), evaluating cumulative LK_t via Eq. 13.
    - VMD0054 v1.0 is transition-eligible ONLY where the relevant project request was submitted by
      31 JANUARY 2027 and the request is one of:
        A. REGISTRATION
        B. VERIFICATION_APPROVAL_BASELINE_REASSESSMENT
        C. VERIFICATION_APPROVAL_METHODOLOGY_CHANGE_PD_DEVIATION
        D. CREDITING_PERIOD_RENEWAL
        E. REQUANTIFICATION
      Generic categories (VALIDATION_LISTING, PROJECT_DESCRIPTION_SUBMISSION, generic METHODOLOGY_UPDATE_REQUEST,
      generic VERIFICATION_REQUEST) do NOT independently qualify.
      Documentary evidence (Verra request identifier or transition document ID) is mandatory.
      No free-text-only qualification.
    - If transition eligibility criteria are not met, returns VMD0054_VERSION_UNRESOLVED (fail closed).

    Returns:
        VMD0054ResolutionResult: 4-tuple (resolved_version, source_equation, transition_basis, effective_ruleset)
        with attached .governance metadata.
    """
    # 1. NOT_APPLICABLE
    if production_decline_status == "NOT_APPLICABLE" or vmd0054_version_input in ("NOT_APPLICABLE", VMD0054Version.NOT_APPLICABLE):
        basis = transition_basis or "PRODUCTION_DECLINE_NOT_APPLICABLE"
        gov = {
            "request_type": project_request_type,
            "verification_subtype": verification_subtype,
            "submission_date": submission_date.isoformat() if submission_date else None,
            "applicable_deadline": "2027-01-31",
            "verra_request_id": verra_request_id or transition_evidence,
            "transition_document_id": transition_document_id or transition_evidence,
            "eligibility_decision": "NOT_APPLICABLE",
            "decision_rule_version": VERRA_TRANSITION_RULE_VERSION,
            "selected_vmd0054_version": VMD0054Version.NOT_APPLICABLE.value,
            "source_equation": "NOT_APPLICABLE",
            "decision_basis": basis,
        }
        return VMD0054ResolutionResult(
            VMD0054Version.NOT_APPLICABLE,
            "NOT_APPLICABLE",
            basis,
            "NOT_APPLICABLE",
            gov,
        )

    ver_str = str(vmd0054_version_input.value if isinstance(vmd0054_version_input, VMD0054Version) else vmd0054_version_input or "").strip()

    # 2. VMD0054 v1.1 Active Standard (Default)
    if not ver_str or ver_str in (
        VMD0054Version.VMD0054_1_1_CURRENT.value,
        "VMD0054_1_1_CURRENT",
        "1.1",
        "v1.1",
        "V1.1",
        "v1.1 (Eq. 13)",
    ):
        basis = transition_basis or "ACTIVE_STANDARD_V1_1"
        gov = {
            "request_type": project_request_type,
            "verification_subtype": verification_subtype,
            "submission_date": submission_date.isoformat() if submission_date else None,
            "applicable_deadline": "2027-01-31",
            "verra_request_id": verra_request_id or transition_evidence,
            "transition_document_id": transition_document_id or transition_evidence,
            "eligibility_decision": "ACTIVE_STANDARD_V1_1",
            "decision_rule_version": VERRA_TRANSITION_RULE_VERSION,
            "selected_vmd0054_version": VMD0054Version.VMD0054_1_1_CURRENT.value,
            "source_equation": "VMD0054_V1.1_EQ13",
            "decision_basis": basis,
        }
        return VMD0054ResolutionResult(
            VMD0054Version.VMD0054_1_1_CURRENT,
            "VMD0054_V1.1_EQ13",
            basis,
            "VMD0054_V1.1_ACTIVE",
            gov,
        )

    # 3. VMD0054 v1.0 Transition Eligibility Check
    is_v10_requested = ver_str in (
        VMD0054Version.VMD0054_1_0_TRANSITION_ELIGIBLE.value,
        "VMD0054_1_0_TRANSITION_ELIGIBLE",
        "1.0",
        "v1.0",
        "V1.0",
        "v1.0 (Eq. 10)",
    )

    if is_v10_requested:
        # Classify request category and verification subtype
        category, eff_subtype, cat_err = classify_verra_transition_request(
            request_type=project_request_type,
            verification_subtype=verification_subtype,
        )

        eff_request_id = verra_request_id or transition_evidence
        eff_doc_id = transition_document_id or transition_evidence

        is_eligible = False
        decision_basis = ""

        # Validate mandatory transition criteria:
        # 1. Submission date must be present and <= 2027-01-31
        if submission_date is None:
            decision_basis = "TRANSITION_ELIGIBILITY_UNVERIFIED_MISSING_SUBMISSION_DATE"
        elif submission_date > VERRA_TRANSITION_DEADLINE_2027_01_31:
            decision_basis = f"SUBMISSION_DATE_{submission_date.isoformat()}_EXCEEDS_DEADLINE_2027-01-31"
        # 2. Must belong to an official qualifying category
        elif category is None:
            decision_basis = cat_err or f"INVALID_PROJECT_REQUEST_TYPE_{project_request_type}"
        # 3. Must have documentary evidence / reference identifier (no free-text-only qualification)
        elif not eff_request_id and not eff_doc_id:
            decision_basis = "MISSING_TRANSITION_DOCUMENTARY_EVIDENCE_OR_REQUEST_IDENTIFIER"
        else:
            is_eligible = True
            decision_basis = (
                f"VERRA_{category.value}_SUBMITTED_{submission_date.isoformat()}"
                f"_DEADLINE_2027-01-31_REF_{eff_request_id or eff_doc_id}"
            )

        if is_eligible and category is not None and submission_date is not None:
            gov = {
                "request_type": category.value,
                "verification_subtype": eff_subtype,
                "submission_date": submission_date.isoformat(),
                "applicable_deadline": "2027-01-31",
                "verra_request_id": eff_request_id,
                "transition_document_id": eff_doc_id,
                "eligibility_decision": "ELIGIBLE",
                "decision_rule_version": VERRA_TRANSITION_RULE_VERSION,
                "selected_vmd0054_version": VMD0054Version.VMD0054_1_0_TRANSITION_ELIGIBLE.value,
                "source_equation": "VMD0054_V1.0_EQ10",
                "decision_basis": decision_basis,
            }
            return VMD0054ResolutionResult(
                VMD0054Version.VMD0054_1_0_TRANSITION_ELIGIBLE,
                "VMD0054_V1.0_EQ10",
                decision_basis,
                "VMD0054_V1.0_TRANSITION",
                gov,
            )
        else:
            gov = {
                "request_type": category.value if category else project_request_type,
                "verification_subtype": eff_subtype,
                "submission_date": submission_date.isoformat() if submission_date else None,
                "applicable_deadline": "2027-01-31",
                "verra_request_id": eff_request_id,
                "transition_document_id": eff_doc_id,
                "eligibility_decision": "NOT_ELIGIBLE",
                "decision_rule_version": VERRA_TRANSITION_RULE_VERSION,
                "selected_vmd0054_version": VMD0054Version.VMD0054_VERSION_UNRESOLVED.value,
                "source_equation": "UNRESOLVED",
                "decision_basis": decision_basis,
            }
            return VMD0054ResolutionResult(
                VMD0054Version.VMD0054_VERSION_UNRESOLVED,
                "UNRESOLVED",
                decision_basis,
                "VMD0054_VERSION_UNRESOLVED",
                gov,
            )

    # 4. Explicit UNRESOLVED or Unknown
    gov = {
        "request_type": project_request_type,
        "verification_subtype": verification_subtype,
        "submission_date": submission_date.isoformat() if submission_date else None,
        "applicable_deadline": "2027-01-31",
        "verra_request_id": verra_request_id or transition_evidence,
        "transition_document_id": transition_document_id or transition_evidence,
        "eligibility_decision": "NOT_ELIGIBLE",
        "decision_rule_version": VERRA_TRANSITION_RULE_VERSION,
        "selected_vmd0054_version": VMD0054Version.VMD0054_VERSION_UNRESOLVED.value,
        "source_equation": "UNRESOLVED",
        "decision_basis": transition_basis or "VERSION_UNRESOLVED",
    }
    return VMD0054ResolutionResult(
        VMD0054Version.VMD0054_VERSION_UNRESOLVED,
        "UNRESOLVED",
        transition_basis or "VERSION_UNRESOLVED",
        "VMD0054_VERSION_UNRESOLVED",
        gov,
    )


def calculate_total_leakage(
    leakage: LeakageInputData,
    authoritative: bool = False,
) -> Tuple[Decimal, Decimal, Decimal, Decimal]:
    """
    Calculates total leakage under VM0042 corrected Eq. 36 (11 June 2026 C&C):
    TOTAL_LEAKAGE_t = LEOA,t + LKdisp,t + LEBR,t
    Where:
    - LEOA,t: Ecological leakage outside project boundary (LK_act + LK_ls)
    - LKdisp,t: Production decline leakage per VMD0054 (v1.1 Eq. 13 or v1.0 Eq. 10 via VM0042 Eq. 36)
    - LEBR,t: Biomass residue diversion leakage per TOOL16
    Returns (total_leakage, leoa, lkdisp, lebr).
    """
    resolution = resolve_vmd0054_version(
        vmd0054_version_input=leakage.vmd0054_version,
        transition_eligible=leakage.vmd0054_transition_eligible,
        transition_basis=leakage.vmd0054_transition_basis,
        production_decline_status=leakage.production_decline_status,
        submission_date=leakage.submission_date,
        project_request_type=leakage.project_request_type,
        verification_subtype=leakage.verification_subtype,
        verra_request_id=leakage.verra_request_id,
        transition_document_id=leakage.transition_document_id,
        transition_evidence=leakage.transition_evidence,
    )
    vmd_ver, vmd_eq, vmd_basis, vmd_ruleset = resolution
    leakage.transition_governance = resolution.governance
    if authoritative and vmd_ver == VMD0054Version.VMD0054_VERSION_UNRESOLVED:
        raise NetGHGCalculationError(
            "VMD0054_VERSION_UNRESOLVED",
            "Cannot determine whether project is eligible to use VMD0054 v1.0. "
            "VMD0054 v1.1 is active standard. Transition metadata unverified; authoritative leakage calculation blocked.",
            details={
                "requested_version": str(leakage.vmd0054_version),
                "transition_basis": vmd_basis,
                "status": "AUTHORITATIVE_NET_GHG_BLOCKED",
            },
        )
    leakage.vmd0054_version = vmd_ver.value
    leakage.vmd0054_source_equation = vmd_eq
    leakage.vmd0054_transition_basis = vmd_basis
    leakage.vmd0054_effective_ruleset = vmd_ruleset

    # Compute production decline leakage if detailed VMD0054 inputs provided
    if leakage.al_t_ha is not None:
        delta_cs = leakage.delta_cs_tc_ha
        if delta_cs is None and leakage.delta_c_biomass_tc_ha is not None and leakage.delta_soc_tc_ha is not None:
            delta_cs = calculate_vmd0054_v11_equation_11_delta_cs(
                delta_c_biomass_tc_ha=leakage.delta_c_biomass_tc_ha,
                delta_soc_tc_ha=leakage.delta_soc_tc_ha,
            )
            leakage.delta_cs_tc_ha = delta_cs
        if delta_cs is not None:
            if vmd_ver == VMD0054Version.VMD0054_1_1_CURRENT:
                cum_lk = calculate_vmd0054_v11_equation_13_cumulative_leakage(
                    al_t_ha=leakage.al_t_ha,
                    delta_cs_tc_ha=delta_cs,
                    elm_t_tco2e=leakage.elm_t_tco2e or Decimal("0.0000"),
                )
            else:
                cum_lk = calculate_vmd0054_v10_equation_10_cumulative_leakage(
                    al_t_ha=leakage.al_t_ha,
                    delta_cs_tc_ha=delta_cs,
                    elm_t_tco2e=leakage.elm_t_tco2e or Decimal("0.0000"),
                )
            leakage.vmd0054_cumulative_leakage_tco2e = cum_lk
            lk_prior = leakage.vmd0054_prior_leakage_tco2e or Decimal("0.0000")
            years = leakage.vmd0054_verification_period_years or Decimal("1.0000")
            leakage.production_decline_leakage_tco2e_yr = calculate_vm0042_equation_36_market_leakage(
                lk_t_tco2e=cum_lk,
                lk_prior_tco2e=lk_prior,
                verification_period_years=years,
            )

    leoa = (
        leakage.leoa_tco2e_yr
        if leakage.leoa_tco2e_yr is not None
        else (leakage.activity_displacement_tco2e_yr + leakage.livestock_displacement_tco2e_yr)
    ).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)
    lkdisp = leakage.production_decline_leakage_tco2e_yr.quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)
    lebr = leakage.biomass_residue_diversion_tco2e_yr.quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)
    total = (leoa + lkdisp + lebr).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)
    return total, leoa, lkdisp, lebr


def calculate_equation_37_gross_reductions(
    delta_e_sources_tco2e: Decimal,
    eq44_bsl_total_tco2e: Decimal,
    eq45_wp_total_tco2e: Decimal,
    i_delta_co2_wp: int,
) -> Tuple[Decimal, Decimal]:
    """
    VM0042 v2.2 Equation 37: Gross GHG Emission Reductions (Before Leakage)
    Literal Official Form (No Outer Clamp):
    WHEN I(ΔCO2_wp) = 1:
        ER_t = sum(Delta_E_sources,t) + [min(0, ΔCO2_wp,t) - min(0, ΔCO2_bsl,t)]
    WHEN I(ΔCO2_wp) = 0:
        ER_t = sum(Delta_E_sources,t) + [min(0, ΔCO2_wp,t) - min(0, ΔCO2_bsl,t) + max(0, ΔCO2_wp,t) - max(0, ΔCO2_bsl,t)]
        (algebraically equals sum(Delta_E_sources,t) + ΔCO2_wp,t - ΔCO2_bsl,t for I=0 branch)

    Returns (er_gross, stock_reductions_term).
    """
    min_wp = min(Decimal("0.0000"), eq45_wp_total_tco2e)
    min_bsl = min(Decimal("0.0000"), eq44_bsl_total_tco2e)
    max_wp = max(Decimal("0.0000"), eq45_wp_total_tco2e)
    max_bsl = max(Decimal("0.0000"), eq44_bsl_total_tco2e)

    if i_delta_co2_wp == 1:
        stock_reductions_term = (min_wp - min_bsl).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)
    else:
        stock_reductions_term = ((min_wp - min_bsl) + (max_wp - max_bsl)).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)

    raw_er = delta_e_sources_tco2e + stock_reductions_term
    er_gross = raw_er.quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)
    return er_gross, stock_reductions_term


def calculate_equation_40_gross_removals(
    eq44_bsl_total_tco2e: Decimal,
    eq45_wp_total_tco2e: Decimal,
    i_delta_co2_wp: int,
) -> Decimal:
    """
    VM0042 v2.2 Equation 40: Gross Carbon Dioxide Removals (Before Leakage)
    CR_t = I(Delta_CO2_wp) * max(0, max(0, Delta_CO2_wp,t) - max(0, Delta_CO2_bsl,t))
    Operative only when cumulative project carbon stock change > 0 (I = 1).
    """
    if i_delta_co2_wp == 0:
        return Decimal("0.0000")
    wp_pos = max(Decimal("0.0000"), eq45_wp_total_tco2e)
    bsl_pos = max(Decimal("0.0000"), eq44_bsl_total_tco2e)
    raw_cr = wp_pos - bsl_pos
    return max(Decimal("0.0000"), raw_cr).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)


def allocate_leakage_eq39_eq42(
    total_leakage: Decimal,
    er_gross: Decimal,
    cr_gross: Decimal,
) -> Tuple[Decimal, Decimal, str]:
    """
    VM0042 v2.2 Equation 39 & Equation 42: Leakage Allocation (11 June 2026 C&C).
    For ER > 0 and CR > 0:
      LKER_t = TOTAL_LEAKAGE * ER / (ER + CR)
      LKCR_t = TOTAL_LEAKAGE - LKER_t
      Guarantees LKER + LKCR == TOTAL_LEAKAGE within Decimal rounding.
    For ER > 0 and CR <= 0:
      LKER_t = TOTAL_LEAKAGE, LKCR_t = 0
    For CR > 0 and ER <= 0:
      LKER_t = 0, LKCR_t = TOTAL_LEAKAGE
    For ER <= 0 and CR <= 0:
      - If total_leakage == 0: return (0, 0, 'NO_BENEFIT_NO_LEAKAGE')
      - If total_leakage > 0: raise LEAKAGE_ALLOCATION_UNDEFINED / AUTHORITATIVE_NET_GHG_BLOCKED
    """
    if er_gross > Decimal("0.0000") and cr_gross > Decimal("0.0000"):
        denom = er_gross + cr_gross
        lker = (total_leakage * (er_gross / denom)).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)
        lkcr = (total_leakage - lker).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)
        return lker, lkcr, "CALCULATED"
    elif er_gross > Decimal("0.0000") and cr_gross <= Decimal("0.0000"):
        return total_leakage.quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN), Decimal("0.0000"), "CALCULATED"
    elif cr_gross > Decimal("0.0000") and er_gross <= Decimal("0.0000"):
        return Decimal("0.0000"), total_leakage.quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN), "CALCULATED"

    if total_leakage == Decimal("0.0000"):
        return Decimal("0.0000"), Decimal("0.0000"), "NO_BENEFIT_NO_LEAKAGE"
    raise NetGHGCalculationError(
        "LEAKAGE_ALLOCATION_UNDEFINED",
        f"Cannot allocate positive leakage ({total_leakage} tCO2e/yr) when ER <= 0 and CR <= 0 "
        f"(ER={er_gross}, CR={cr_gross}). Allocation is undefined under VM0042 Equations 39 & 42; calculation blocked.",
        details={
            "er_gross": str(er_gross),
            "cr_gross": str(cr_gross),
            "total_leakage": str(total_leakage),
            "status": "AUTHORITATIVE_NET_GHG_BLOCKED",
        },
    )


def calculate_equation_39_leakage_allocation_er(
    total_leakage: Decimal,
    er_gross: Decimal,
    cr_gross: Decimal,
) -> Decimal:
    """VM0042 Eq. 39: Leakage allocated to emission reductions."""
    lker, _, _ = allocate_leakage_eq39_eq42(total_leakage, er_gross, cr_gross)
    return lker


def calculate_equation_42_leakage_allocation_cr(
    total_leakage: Decimal,
    er_gross: Decimal,
    cr_gross: Decimal,
) -> Decimal:
    """VM0042 Eq. 42: Leakage allocated to removals."""
    _, lkcr, _ = allocate_leakage_eq39_eq42(total_leakage, er_gross, cr_gross)
    return lkcr


def calculate_equation_38_net_reductions(
    er_gross: Decimal,
    lker: Decimal,
) -> Decimal:
    """VM0042 Eq. 38: Net GHG Emission Reductions ERNET_t = ER_t - LKER_t."""
    return (er_gross - lker).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)


def calculate_equation_41_net_removals(
    cr_gross: Decimal,
    lkcr: Decimal,
) -> Decimal:
    """VM0042 Eq. 41: Net Carbon Dioxide Removals CRNET_t = CR_t - LKCR_t."""
    return (cr_gross - lkcr).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)


def calculate_equation_43_total_net(
    ernet: Decimal,
    crnet: Decimal,
) -> Decimal:
    """VM0042 Eq. 43: Total Net GHG Reductions and Removals ERRNET_t = ERNET_t + CRNET_t."""
    return (ernet + crnet).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)


def calculate_equation_75_buffer_reductions(
    stock_reductions_term: Optional[Decimal] = None,
    npr_fraction: Decimal = Decimal("0.0000"),
    *,
    eq44_bsl_total_tco2e: Optional[Decimal] = None,
    eq45_wp_total_tco2e: Optional[Decimal] = None,
    i_delta_co2_wp: Optional[int] = None,
) -> Decimal:
    """
    VM0042 Section 8.7 Eq. 75: Buffer deduction for emission reductions.
    Literal Official Form:
    BuER,t = I(ΔCO2_wp) * [min(0, ΔCO2_wp,t) - min(0, ΔCO2_bsl,t)] * NPR%
           + (1 - I(ΔCO2_wp)) * [min(0, ΔCO2_wp,t) - min(0, ΔCO2_bsl,t) + max(0, ΔCO2_wp,t) - max(0, ΔCO2_bsl,t)] * NPR%

    Operates on the literal official stock-change reduction term without outer zero-clamping.
    """
    if stock_reductions_term is None:
        if eq44_bsl_total_tco2e is None or eq45_wp_total_tco2e is None or i_delta_co2_wp is None:
            raise ValueError(
                "calculate_equation_75_buffer_reductions requires either stock_reductions_term "
                "or (eq44_bsl_total_tco2e, eq45_wp_total_tco2e, i_delta_co2_wp)"
            )
        min_wp = min(Decimal("0.0000"), eq45_wp_total_tco2e)
        min_bsl = min(Decimal("0.0000"), eq44_bsl_total_tco2e)
        max_wp = max(Decimal("0.0000"), eq45_wp_total_tco2e)
        max_bsl = max(Decimal("0.0000"), eq44_bsl_total_tco2e)
        if i_delta_co2_wp == 1:
            stock_reductions_term = min_wp - min_bsl
        else:
            stock_reductions_term = (min_wp - min_bsl) + (max_wp - max_bsl)

    return (stock_reductions_term * npr_fraction).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)


def calculate_equation_76_buffer_removals(
    cr_gross: Decimal,
    npr_fraction: Decimal,
) -> Decimal:
    """
    VM0042 Section 8.7 Eq. 76: Buffer deduction for carbon dioxide removals.
    BuCR,t = I(Delta_CO2_wp) * [max(0, Delta_CO2_wp,t) - max(0, Delta_CO2_bsl,t)] * NPR% = CR_t * NPR%.
    It is based on qualifying carbon-stock-change gross removals before leakage; NOT CRNET * NPR%.
    """
    qualifying_cr = max(Decimal("0.0000"), cr_gross)
    return (qualifying_cr * npr_fraction).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)


def calculate_equation_77_vcu_reductions(
    ernet: Decimal,
    bu_er: Decimal,
) -> Decimal:
    """VM0042 Section 8.7 Eq. 77: Reduction-side VCU eligible quantity VCUER,t = ERNET_t - BuER,t."""
    return (ernet - bu_er).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)


def calculate_equation_78_vcu_removals(
    crnet: Decimal,
    bu_cr: Decimal,
) -> Decimal:
    """VM0042 Section 8.7 Eq. 78: Removal-side VCU eligible quantity VCUCR,t = CRNET_t - BuCR,t."""
    return (crnet - bu_cr).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)


def calculate_equation_79_total_vcu(
    vcu_er: Decimal,
    vcu_cr: Decimal,
) -> Decimal:
    """
    VM0042 Section 8.7 Eq. 79: Total internal VCU eligible quantity VCU_t = VCUER,t + VCUCR,t.
    Strictly labeled INTERNAL_VCU_ELIGIBLE_QUANTITY.
    """
    return (vcu_er + vcu_cr).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)


# =============================================================================
# Core Net GHG Quantification Pipeline (Equations 37–43 & 75–79)
# =============================================================================

def evaluate_single_vintage_net_ghg(
    vintage_year: int,
    # Sourced emissions inputs
    fossil_fuel_bsl: List[FossilFuelActivity],
    fossil_fuel_wp: List[FossilFuelActivity],
    liming_bsl: LimingActivity,
    liming_wp: LimingActivity,
    fertilizer_bsl: List[FertilizerN2OActivity],
    fertilizer_wp: List[FertilizerN2OActivity],
    nfixing_bsl: List[NitrogenFixingActivity],
    nfixing_wp: List[NitrogenFixingActivity],
    manure_bsl: List[ManureDepositionActivity],
    manure_wp: List[ManureDepositionActivity],
    enteric_bsl: List[EntericFermentationActivity],
    enteric_wp: List[EntericFermentationActivity],
    burning_bsl: List[BiomassBurningActivity],
    burning_wp: List[BiomassBurningActivity],
    methanogenesis_bsl: SoilMethanogenesisActivity,
    methanogenesis_wp: SoilMethanogenesisActivity,
    # Carbon stock changes
    soc_stock_change_bsl_tco2e: Decimal,
    soc_stock_change_wp_tco2e: Decimal,
    soc_uncertainty_deduction_fraction: Decimal,
    soc_sign_indicator: int,
    woody_pool: WoodyBiomassPoolData,
    # Cumulative project stock change up to this vintage year (for I(Delta_CO2_wp) switch)
    prior_cumulative_project_stock_change_tco2e: Decimal,
    # Leakage
    leakage: LeakageInputData,
    # NPR Risk Assessment (optional)
    npr_input: Optional[NPRRiskAssessmentInput] = None,
    # GWP config
    gwp_config: GWPConfig = GWPConfig(),
) -> AnnualVintageGHGResult:
    """
    Evaluates exact VM0042 v2.2 Equations 37–43 and Section 8.7 (Eqs 75–79)
    for a single calendar vintage year.
    """
    # 1. Evaluate baseline and project emissions by source
    e_ff_bsl = calculate_fossil_fuel_emissions(fossil_fuel_bsl)
    e_ff_wp = calculate_fossil_fuel_emissions(fossil_fuel_wp)

    e_lime_bsl = calculate_liming_emissions(liming_bsl)
    e_lime_wp = calculate_liming_emissions(liming_wp)

    e_fert_bsl = calculate_fertilizer_n2o_emissions(fertilizer_bsl, gwp_n2o=gwp_config.gwp_n2o)
    e_fert_wp = calculate_fertilizer_n2o_emissions(fertilizer_wp, gwp_n2o=gwp_config.gwp_n2o)

    e_nfix_bsl = calculate_nfixing_emissions(nfixing_bsl, gwp_n2o=gwp_config.gwp_n2o)
    e_nfix_wp = calculate_nfixing_emissions(nfixing_wp, gwp_n2o=gwp_config.gwp_n2o)

    e_md_ch4_bsl, e_md_n2o_bsl = calculate_manure_deposition_emissions(manure_bsl, gwp_ch4=gwp_config.gwp_ch4, gwp_n2o=gwp_config.gwp_n2o)
    e_md_ch4_wp, e_md_n2o_wp = calculate_manure_deposition_emissions(manure_wp, gwp_ch4=gwp_config.gwp_ch4, gwp_n2o=gwp_config.gwp_n2o)

    e_ent_ch4_bsl = calculate_enteric_fermentation_emissions(enteric_bsl, gwp_ch4=gwp_config.gwp_ch4)
    e_ent_ch4_wp = calculate_enteric_fermentation_emissions(enteric_wp, gwp_ch4=gwp_config.gwp_ch4)

    e_bb_ch4_bsl, e_bb_n2o_bsl = calculate_biomass_burning_emissions(burning_bsl, gwp_ch4=gwp_config.gwp_ch4, gwp_n2o=gwp_config.gwp_n2o)
    e_bb_ch4_wp, e_bb_n2o_wp = calculate_biomass_burning_emissions(burning_wp, gwp_ch4=gwp_config.gwp_ch4, gwp_n2o=gwp_config.gwp_n2o)

    # Soil methanogenesis (QA1 only)
    e_soil_ch4_bsl = Decimal("0.0000")
    e_soil_ch4_wp = Decimal("0.0000")
    if methanogenesis_bsl.annual_ch4_emissions_tco2e is not None and not methanogenesis_bsl.is_verified_zero:
        e_soil_ch4_bsl = methanogenesis_bsl.annual_ch4_emissions_tco2e
    if methanogenesis_wp.annual_ch4_emissions_tco2e is not None and not methanogenesis_wp.is_verified_zero:
        e_soil_ch4_wp = methanogenesis_wp.annual_ch4_emissions_tco2e

    # Sum baseline and project emissions from sources
    total_bsl_emissions = (
        e_ff_bsl + e_lime_bsl + e_fert_bsl + e_nfix_bsl +
        e_md_ch4_bsl + e_md_n2o_bsl + e_ent_ch4_bsl +
        e_bb_ch4_bsl + e_bb_n2o_bsl + e_soil_ch4_bsl
    ).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)

    total_wp_emissions = (
        e_ff_wp + e_lime_wp + e_fert_wp + e_nfix_wp +
        e_md_ch4_wp + e_md_n2o_wp + e_ent_ch4_wp +
        e_bb_ch4_wp + e_bb_n2o_wp + e_soil_ch4_wp
    ).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)

    # Source emission reductions: Delta_E_sources = Baseline emissions - Project emissions
    delta_e_sources = (total_bsl_emissions - total_wp_emissions).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)

    # 2. Woody Biomass and Equations 44 & 45 Completion
    woody_bsl = (woody_pool.baseline_tree_stock_change_tco2e_yr + woody_pool.baseline_shrub_stock_change_tco2e_yr).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)
    woody_wp = (woody_pool.project_tree_stock_change_tco2e_yr + woody_pool.project_shrub_stock_change_tco2e_yr).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)

    # Uncertainty deduction factor for SOC stock: (1 - UNC * I)
    unc_factor = (Decimal("1.000000") - (soc_uncertainty_deduction_fraction * Decimal(str(soc_sign_indicator))))

    # Uncertainty deduction amount
    soc_adj_bsl = (soc_stock_change_bsl_tco2e * unc_factor).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)
    soc_adj_wp = (soc_stock_change_wp_tco2e * unc_factor).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)
    soc_uncertainty_adjusted_effect = (soc_adj_wp - soc_adj_bsl).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)
    soc_uncertainty_deduction_amount = abs((soc_stock_change_wp_tco2e - soc_stock_change_bsl_tco2e) - soc_uncertainty_adjusted_effect)

    # Equation (44): Delta_CO2_bsl,t = Delta_CO2_soil_bsl,t * (1 - UNC * I) + Delta_C_tree,bsl,t + Delta_C_shrub,bsl,t
    eq44_bsl_total = (soc_adj_bsl + woody_bsl).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)

    # Equation (45): Delta_CO2_wp,t = Delta_CO2_soil_wp,t * (1 - UNC * I) + Delta_C_tree,wp,t + Delta_C_shrub,wp,t
    eq45_wp_total = (soc_adj_wp + woody_wp).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)

    eq44_eq45_status = "CALCULATED"

    # Cumulative project stock change up to this vintage year:
    cumulative_project_stock = (prior_cumulative_project_stock_change_tco2e + eq45_wp_total).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)
    # VM0042 Section 8.5 switch I(Delta_CO2_wp): 1 if cumulative project stock > 0, else 0
    i_delta_co2_wp = 1 if cumulative_project_stock > Decimal("0.0") else 0

    # 3. Leakage (Section 8.4 + 11 June 2026 C&C + VMD0054 Resolution)
    resolution = resolve_vmd0054_version(
        vmd0054_version_input=leakage.vmd0054_version,
        transition_eligible=leakage.vmd0054_transition_eligible,
        transition_basis=leakage.vmd0054_transition_basis,
        production_decline_status=leakage.production_decline_status,
        submission_date=leakage.submission_date,
        project_request_type=leakage.project_request_type,
        verification_subtype=leakage.verification_subtype,
        verra_request_id=leakage.verra_request_id,
        transition_document_id=leakage.transition_document_id,
        transition_evidence=leakage.transition_evidence,
    )
    vmd_version, vmd_eq, vmd_basis, vmd_ruleset = resolution
    leakage.transition_governance = resolution.governance
    if vmd_version == VMD0054Version.VMD0054_VERSION_UNRESOLVED:
        raise NetGHGCalculationError(
            "VMD0054_VERSION_UNRESOLVED",
            "Cannot determine whether project is eligible to use VMD0054 v1.0. "
            "VMD0054 v1.1 is active standard. Transition metadata unverified; authoritative leakage calculation blocked.",
            details={
                "requested_version": str(leakage.vmd0054_version),
                "transition_basis": vmd_basis,
                "status": "AUTHORITATIVE_NET_GHG_BLOCKED",
            },
        )
    leakage.vmd0054_version = vmd_version.value
    leakage.vmd0054_source_equation = vmd_eq
    leakage.vmd0054_transition_basis = vmd_basis
    leakage.vmd0054_effective_ruleset = vmd_ruleset
    total_leakage, lk_leoa, lk_disp, lk_lebr = calculate_total_leakage(leakage)
    lk_act = leakage.activity_displacement_tco2e_yr
    lk_ls = leakage.livestock_displacement_tco2e_yr
    lk_prod = leakage.production_decline_leakage_tco2e_yr
    lk_res = leakage.biomass_residue_diversion_tco2e_yr

    # 4. Equation 37: Gross Reductions (ER_t)
    er_gross, stock_reductions_term = calculate_equation_37_gross_reductions(
        delta_e_sources_tco2e=delta_e_sources,
        eq44_bsl_total_tco2e=eq44_bsl_total,
        eq45_wp_total_tco2e=eq45_wp_total,
        i_delta_co2_wp=i_delta_co2_wp,
    )

    # 5. Equation 40: Gross Removals (CR_t)
    cr_gross = calculate_equation_40_gross_removals(
        eq44_bsl_total_tco2e=eq44_bsl_total,
        eq45_wp_total_tco2e=eq45_wp_total,
        i_delta_co2_wp=i_delta_co2_wp,
    )

    # 6. Equations 39 & 42: Leakage Allocation (11 June 2026 C&C + Zero Denominator Safety)
    lker, lkcr, lk_status = allocate_leakage_eq39_eq42(
        total_leakage=total_leakage,
        er_gross=er_gross,
        cr_gross=cr_gross,
    )

    # 7. Equations 38 & 41: Net Reductions and Removals
    ernet = calculate_equation_38_net_reductions(er_gross=er_gross, lker=lker)
    crnet = calculate_equation_41_net_removals(cr_gross=cr_gross, lkcr=lkcr)

    # 8. Equation 43: Total Net GHG Reductions & Removals (ERRNET_t)
    errnet = calculate_equation_43_total_net(ernet=ernet, crnet=crnet)

    # Perfect component reconciliation check
    rec_residual = abs((ernet + crnet) - errnet)
    if rec_residual > Decimal("0.0001"):
        raise NetGHGCalculationError("RECONCILIATION_FAILED", f"Equation 43 reconciliation failed: residual={rec_residual}")

    # 9. Section 8.7 VCU Readiness (Eqs 75–79)
    buf_er = None
    buf_cr = None
    buf_total = None
    vcu_er = None
    vcu_cr = None
    vcu_total = None
    vcu_readiness_status = "NOT_CONFIGURED"
    npr_pct = None

    if npr_input is not None:
        npr_pct = npr_input.npr_rating_pct
        npr_fraction = (npr_pct / Decimal("100.0")).quantize(PRECISION_FRACTION, rounding=ROUND_HALF_EVEN)

        # Eq. 75: Buffer deduction for qualifying stock reductions
        buf_er = calculate_equation_75_buffer_reductions(
            stock_reductions_term=stock_reductions_term,
            npr_fraction=npr_fraction,
        )

        # Eq. 76: Buffer deduction for qualifying stock removals
        buf_cr = calculate_equation_76_buffer_removals(
            cr_gross=cr_gross,
            npr_fraction=npr_fraction,
        )

        buf_total = (buf_er + buf_cr).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)

        # Eq. 77: Reduction-side VCU quantity
        vcu_er = calculate_equation_77_vcu_reductions(ernet=ernet, bu_er=buf_er)

        # Eq. 78: Removal-side VCU quantity
        vcu_cr = calculate_equation_78_vcu_removals(crnet=crnet, bu_cr=buf_cr)

        # Eq. 79: Total internal VCU eligible quantity
        vcu_total = calculate_equation_79_total_vcu(vcu_er=vcu_er, vcu_cr=vcu_cr)
        vcu_readiness_status = "CALCULATED"
    else:
        vcu_readiness_status = "NOT_CONFIGURED_MISSING_NPR"

    return AnnualVintageGHGResult(
        vintage_year=vintage_year,
        e_fossil_fuel_bsl=e_ff_bsl,
        e_fossil_fuel_wp=e_ff_wp,
        e_liming_bsl=e_lime_bsl,
        e_liming_wp=e_lime_wp,
        e_fert_n2o_bsl=e_fert_bsl,
        e_fert_n2o_wp=e_fert_wp,
        e_nfix_bsl=e_nfix_bsl,
        e_nfix_wp=e_nfix_wp,
        e_manure_ch4_bsl=e_md_ch4_bsl,
        e_manure_ch4_wp=e_md_ch4_wp,
        e_manure_n2o_bsl=e_md_n2o_bsl,
        e_manure_n2o_wp=e_md_n2o_wp,
        e_enteric_ch4_bsl=e_ent_ch4_bsl,
        e_enteric_ch4_wp=e_ent_ch4_wp,
        e_biomass_burn_ch4_bsl=e_bb_ch4_bsl,
        e_biomass_burn_ch4_wp=e_bb_ch4_wp,
        e_biomass_burn_n2o_bsl=e_bb_n2o_bsl,
        e_biomass_burn_n2o_wp=e_bb_n2o_wp,
        e_soil_ch4_bsl=e_soil_ch4_bsl,
        e_soil_ch4_wp=e_soil_ch4_wp,
        total_baseline_emissions_tco2e=total_bsl_emissions,
        total_project_emissions_tco2e=total_wp_emissions,
        total_emission_reductions_from_sources_tco2e=delta_e_sources,
        soc_stock_change_bsl_tco2e=soc_stock_change_bsl_tco2e,
        soc_stock_change_wp_tco2e=soc_stock_change_wp_tco2e,
        soc_stock_uncertainty_deduction_tco2e=soc_uncertainty_deduction_amount,
        soc_uncertainty_adjusted_effect_tco2e=soc_uncertainty_adjusted_effect,
        woody_stock_change_bsl_tco2e=woody_bsl,
        woody_stock_change_wp_tco2e=woody_wp,
        eq44_baseline_total_carbon_stock_change_tco2e=eq44_bsl_total,
        eq45_project_total_carbon_stock_change_tco2e=eq45_wp_total,
        eq44_eq45_status=eq44_eq45_status,
        cumulative_project_stock_change_tco2e=cumulative_project_stock,
        i_delta_co2_wp=i_delta_co2_wp,
        lk_activity_displacement_tco2e=lk_act,
        lk_livestock_displacement_tco2e=lk_ls,
        lk_production_decline_tco2e=lk_prod,
        lk_biomass_residue_tco2e=lk_res,
        total_leakage_tco2e=total_leakage,
        gross_reductions_er_tco2e=er_gross,
        gross_removals_cr_tco2e=cr_gross,
        leakage_allocation_er_lker_tco2e=lker,
        leakage_allocation_cr_lkcr_tco2e=lkcr,
        net_reductions_ernet_tco2e=ernet,
        net_removals_crnet_tco2e=crnet,
        total_net_ghg_errnet_tco2e=errnet,
        npr_rating_pct=npr_pct,
        buffer_deduction_reductions_tco2e=buf_er,
        buffer_deduction_removals_tco2e=buf_cr,
        total_buffer_deduction_tco2e=buf_total,
        internal_vcu_eligible_reductions_tco2e=vcu_er,
        internal_vcu_eligible_removals_tco2e=vcu_cr,
        internal_vcu_eligible_total_tco2e=vcu_total,
        vcu_readiness_status=vcu_readiness_status,
        leoa_leakage_tco2e=lk_leoa,
        lkdisp_leakage_tco2e=lk_disp,
        lebr_leakage_tco2e=lk_lebr,
        stock_reductions_term_tco2e=stock_reductions_term,
        leakage_allocation_status=lk_status,
        vmd0054_version=str(leakage.vmd0054_version),
        vmd0054_source_equation=str(leakage.vmd0054_source_equation or ("VMD0054_V1.1_EQ13" if "1.1" in str(leakage.vmd0054_version) else "VMD0054_V1.0_EQ10")),
        vmd0054_transition_basis=leakage.vmd0054_transition_basis,
        vmd0054_effective_ruleset=str(leakage.vmd0054_effective_ruleset or ("VMD0054_V1.1_ACTIVE" if "1.1" in str(leakage.vmd0054_version) else "VMD0054_V1.0_TRANSITION")),
        vmd0054_trace={
            "vmd0054_version": str(leakage.vmd0054_version),
            "vmd0054_source_equation": str(leakage.vmd0054_source_equation or ("VMD0054_V1.1_EQ13" if "1.1" in str(leakage.vmd0054_version) else "VMD0054_V1.0_EQ10")),
            "al_t_ha": str(leakage.al_t_ha) if leakage.al_t_ha is not None else None,
            "delta_c_biomass_tc_ha": str(leakage.delta_c_biomass_tc_ha) if leakage.delta_c_biomass_tc_ha is not None else None,
            "delta_soc_tc_ha": str(leakage.delta_soc_tc_ha) if leakage.delta_soc_tc_ha is not None else None,
            "delta_cs_tc_ha": str(leakage.delta_cs_tc_ha) if leakage.delta_cs_tc_ha is not None else None,
            "elm_t_tco2e": str(leakage.elm_t_tco2e) if leakage.elm_t_tco2e is not None else "0.0000",
            "lk_t_cumulative_tco2e": str(leakage.vmd0054_cumulative_leakage_tco2e) if leakage.vmd0054_cumulative_leakage_tco2e is not None else str(lk_disp),
            "lk_prior_tco2e": str(leakage.vmd0054_prior_leakage_tco2e) if leakage.vmd0054_prior_leakage_tco2e is not None else "0.0000",
            "vm0042_lkdisp_tco2e_yr": str(lk_disp),
        },
        transition_governance=leakage.transition_governance if leakage.transition_governance else {
            "request_type": leakage.project_request_type,
            "verification_subtype": leakage.verification_subtype,
            "submission_date": leakage.submission_date.isoformat() if leakage.submission_date else None,
            "applicable_deadline": "2027-01-31",
            "verra_request_id": leakage.verra_request_id or leakage.transition_evidence,
            "transition_document_id": leakage.transition_document_id or leakage.transition_evidence,
            "eligibility_decision": "ELIGIBLE" if "1.0" in str(leakage.vmd0054_version) else "ACTIVE_STANDARD_V1_1",
            "decision_rule_version": VERRA_TRANSITION_RULE_VERSION,
            "selected_vmd0054_version": str(leakage.vmd0054_version),
            "source_equation": str(leakage.vmd0054_source_equation or ("VMD0054_V1.1_EQ13" if "1.1" in str(leakage.vmd0054_version) else "VMD0054_V1.0_EQ10")),
        },
    )


# =============================================================================
# Table 5 Applicability Router & Fail-Closed Gatekeeper
# =============================================================================

def validate_table_5_applicability(
    applicability_items: List[SourceApplicabilityItem],
) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """
    Validates project-wide source and pool applicability against VM0042 Table 5 rules:
    - Fails closed if any mandatory/applicable component is APPLICABLE_NOT_CONFIGURED.
    - Fails closed if any required activity data is MISSING_DATA.
    - Validates that QA2 is strictly routed to SOC, and never to CH4 soil methanogenesis.
    - Validates consistent quantification approach between baseline and project.
    """
    report: Dict[str, Any] = {}
    blocked_reasons: List[str] = []

    for item in applicability_items:
        key = item.source_category
        report[key] = {
            "gas": item.gas,
            "status": item.status.value,
            "approach": item.quantification_approach.value,
            "activity_status": item.activity_data_status.value,
            "rationale": item.rationale,
            "evidence": item.evidence_reference,
        }

        # Check for unconfigured applicable component
        if item.status == ApplicabilityStatus.APPLICABLE_NOT_CONFIGURED:
            blocked_reasons.append(
                f"Source/Pool {key} is APPLICABLE but NOT_CONFIGURED. All applicable sources must be fully configured per VM0042 Table 5."
            )

        # Check for missing data
        if item.activity_data_status in (ActivityDataStatus.MISSING_DATA, ActivityDataStatus.NOT_CONFIGURED):
            if item.status == ApplicabilityStatus.APPLICABLE_CONFIGURED:
                blocked_reasons.append(
                    f"Source/Pool {key} requires activity data but reports {item.activity_data_status.value}."
                )

        # Table 5 QA restriction: QA2 is permitted ONLY for Soil Organic Carbon (SOC)
        if item.quantification_approach == QuantificationApproach.QA2_MEASURE_AND_REMEASURE and item.source_category != "CO2_SOC":
            blocked_reasons.append(
                f"Source {key} configured with QA2 Measure & Remeasure. VM0042 Table 5 permits QA2 strictly for Soil Organic Carbon (SOC)."
            )

        # Table 5 QA restriction: Soil methanogenesis permits ONLY QA1 (Model only)
        if "METHANOGENESIS" in key and item.quantification_approach != QuantificationApproach.QA1_MEASURE_AND_MODEL:
            if item.status == ApplicabilityStatus.APPLICABLE_CONFIGURED:
                blocked_reasons.append(
                    f"Source {key} configured with {item.quantification_approach.value}. VM0042 Table 5 permits strictly QA1 biogeochemical model for soil methanogenesis."
                )

        # Table 5 QA routing for QA1 on agricultural sources (fertilizer, n-fixing, manure, methanogenesis):
        # QA1 requires an accepted/approved biogeochemical model. If QA1 is selected without an accepted model, fail closed.
        if item.quantification_approach == QuantificationApproach.QA1_MEASURE_AND_MODEL and item.status == ApplicabilityStatus.APPLICABLE_CONFIGURED:
            if not item.evidence_reference or item.evidence_reference.strip() == "":
                blocked_reasons.append(
                    f"Source {key} configured with QA1 Measure & Model, but no approved biogeochemical model reference/evidence is configured per VM0042 Table 5 (NOT_CONFIGURED)."
                )

    if blocked_reasons:
        return False, "TABLE_5_APPLICABILITY_BLOCKED: " + " | ".join(blocked_reasons), report

    return True, None, report


# =============================================================================
# Aggregated Multi-Year Verification Period Engine
# =============================================================================

def aggregate_verification_period_net_ghg(
    project_id: uuid.UUID,
    organization_id: uuid.UUID,
    start_date: date,
    end_date: date,
    annual_vintages: List[AnnualVintageGHGResult],
    applicability_report: Dict[str, Any],
    npr_input: Optional[NPRRiskAssessmentInput] = None,
    gwp_config: GWPConfig = GWPConfig(),
) -> NetGHGProjectOutput:
    """
    Aggregates annual vintage results into project-level totals across the verification period.
    Ensures that multi-year periods retain individual vintage rows.
    """
    if not annual_vintages:
        raise NetGHGCalculationError("NO_VINTAGES", "At least one annual vintage is required.")

    elapsed_days = (end_date - start_date).days
    elapsed_years = (Decimal(str(elapsed_days)) / Decimal("365.25")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)
    if elapsed_years <= Decimal("0.0"):
        raise NetGHGCalculationError("INVALID_PERIOD", "Verification period length must be positive.")

    # Sum totals across vintages
    tot_bsl_emissions = sum(v.total_baseline_emissions_tco2e for v in annual_vintages).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)
    tot_wp_emissions = sum(v.total_project_emissions_tco2e for v in annual_vintages).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)
    tot_delta_sources = sum(v.total_emission_reductions_from_sources_tco2e for v in annual_vintages).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)

    tot_eq44 = sum(v.eq44_baseline_total_carbon_stock_change_tco2e for v in annual_vintages).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)
    tot_eq45 = sum(v.eq45_project_total_carbon_stock_change_tco2e for v in annual_vintages).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)

    tot_er_gross = sum(v.gross_reductions_er_tco2e for v in annual_vintages).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)
    tot_cr_gross = sum(v.gross_removals_cr_tco2e for v in annual_vintages).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)
    tot_lk = sum(v.total_leakage_tco2e for v in annual_vintages).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)
    tot_leoa = sum(v.leoa_leakage_tco2e for v in annual_vintages).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)
    tot_lkdisp = sum(v.lkdisp_leakage_tco2e for v in annual_vintages).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)
    tot_lebr = sum(v.lebr_leakage_tco2e for v in annual_vintages).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)
    tot_lker = sum(v.leakage_allocation_er_lker_tco2e for v in annual_vintages).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)
    tot_lkcr = sum(v.leakage_allocation_cr_lkcr_tco2e for v in annual_vintages).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)
    tot_ernet = sum(v.net_reductions_ernet_tco2e for v in annual_vintages).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)
    tot_crnet = sum(v.net_removals_crnet_tco2e for v in annual_vintages).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)
    tot_errnet = sum(v.total_net_ghg_errnet_tco2e for v in annual_vintages).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)

    overall_lk_status = "NO_BENEFIT_NO_LEAKAGE" if all(v.leakage_allocation_status == "NO_BENEFIT_NO_LEAKAGE" for v in annual_vintages) else "CALCULATED"

    # VCU readiness
    tot_buf_er = None
    tot_buf_cr = None
    tot_buf = None
    tot_vcu_er = None
    tot_vcu_cr = None
    tot_vcu = None
    vcu_status = "NOT_CONFIGURED"
    npr_pct = None
    risk_id_str = None

    if npr_input is not None:
        npr_pct = npr_input.npr_rating_pct
        risk_id_str = str(npr_input.risk_assessment_id)
        tot_buf_er = sum(v.buffer_deduction_reductions_tco2e or Decimal("0.0000") for v in annual_vintages).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)
        tot_buf_cr = sum(v.buffer_deduction_removals_tco2e or Decimal("0.0000") for v in annual_vintages).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)
        tot_buf = (tot_buf_er + tot_buf_cr).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)

        tot_vcu_er = sum(v.internal_vcu_eligible_reductions_tco2e or Decimal("0.0000") for v in annual_vintages).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)
        tot_vcu_cr = sum(v.internal_vcu_eligible_removals_tco2e or Decimal("0.0000") for v in annual_vintages).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)
        tot_vcu = (tot_vcu_er + tot_vcu_cr).quantize(PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)
        vcu_status = "CALCULATED"
    else:
        vcu_status = "NOT_CONFIGURED_MISSING_NPR"

    # Compute deterministic cryptographic calculation hash
    hash_payload = {
        "project_id": str(project_id),
        "organization_id": str(organization_id),
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
        "total_errnet": str(tot_errnet),
        "total_er_gross": str(tot_er_gross),
        "total_cr_gross": str(tot_cr_gross),
        "total_leakage": str(tot_lk),
        "vcu_status": vcu_status,
        "vcu_total": str(tot_vcu) if tot_vcu is not None else None,
        "vmd0054_version": annual_vintages[0].vmd0054_version if annual_vintages else "VMD0054_1_1_CURRENT",
        "vmd0054_source_equation": annual_vintages[0].vmd0054_source_equation if annual_vintages else "VMD0054_V1.1_EQ13",
        "vintages": [v.to_dict() for v in annual_vintages],
    }
    calc_hash = hashlib.sha256(json.dumps(hash_payload, sort_keys=True).encode("utf-8")).hexdigest()

    first_v = annual_vintages[0] if annual_vintages else None
    v_trace = first_v.vmd0054_trace if first_v else {}
    t_gov = first_v.transition_governance if first_v else {}

    return NetGHGProjectOutput(
        project_id=project_id,
        organization_id=organization_id,
        verification_period_start=start_date,
        verification_period_end=end_date,
        elapsed_years=elapsed_years,
        applicability_matrix=applicability_report,
        total_baseline_emissions_tco2e=tot_bsl_emissions,
        total_project_emissions_tco2e=tot_wp_emissions,
        total_emission_reductions_from_sources_tco2e=tot_delta_sources,
        eq44_baseline_total_carbon_stock_change_tco2e=tot_eq44,
        eq45_project_total_carbon_stock_change_tco2e=tot_eq45,
        eq44_eq45_status="CALCULATED",
        gross_reductions_er_tco2e=tot_er_gross,
        gross_removals_cr_tco2e=tot_cr_gross,
        total_leakage_tco2e=tot_lk,
        total_leoa_tco2e=tot_leoa,
        total_lkdisp_tco2e=tot_lkdisp,
        total_lebr_tco2e=tot_lebr,
        leakage_allocation_status=overall_lk_status,
        leakage_allocation_er_lker_tco2e=tot_lker,
        leakage_allocation_cr_lkcr_tco2e=tot_lkcr,
        net_reductions_ernet_tco2e=tot_ernet,
        net_removals_crnet_tco2e=tot_crnet,
        total_net_ghg_errnet_tco2e=tot_errnet,
        npr_rating_pct=npr_pct,
        risk_assessment_id=risk_id_str,
        buffer_deduction_reductions_tco2e=tot_buf_er,
        buffer_deduction_removals_tco2e=tot_buf_cr,
        total_buffer_deduction_tco2e=tot_buf,
        internal_vcu_eligible_reductions_tco2e=tot_vcu_er,
        internal_vcu_eligible_removals_tco2e=tot_vcu_cr,
        internal_vcu_eligible_total_tco2e=tot_vcu,
        vcu_readiness_status=vcu_status,
        internal_mrv_status="CALCULATED",
        vvb_status="NOT_CONFIGURED / EXTERNAL",
        registry_status="NOT_CONFIGURED / EXTERNAL",
        ledger_status="BLOCKED_FOR_AGRICULTURE",
        vmd0054_version=annual_vintages[0].vmd0054_version if annual_vintages else "VMD0054_1_1_CURRENT",
        vmd0054_source_equation=annual_vintages[0].vmd0054_source_equation if annual_vintages else "VMD0054_V1.1_EQ13",
        vmd0054_transition_basis=annual_vintages[0].vmd0054_transition_basis if annual_vintages else None,
        vmd0054_effective_ruleset=annual_vintages[0].vmd0054_effective_ruleset if annual_vintages else "VMD0054_V1.1_ACTIVE",
        vmd0054_trace=v_trace,
        transition_governance=t_gov,
        result_status="CALCULATED",
        calculation_hash=calc_hash,
        input_snapshot_hash=hashlib.sha256(json.dumps(applicability_report, sort_keys=True).encode("utf-8")).hexdigest(),
        vintages=annual_vintages,
        component_breakdown={
            "methodology_version": "2.2",
            "c_and_c_version": "2026-06-11",
            "vcs_requirement_version": gwp_config.vcs_requirement_version,
            "ipcc_assessment": gwp_config.ipcc_assessment,
            "gwp_ch4": str(gwp_config.gwp_ch4),
            "gwp_n2o": str(gwp_config.gwp_n2o),
            "effective_ruleset": gwp_config.effective_ruleset,
            "vmd0054_version": annual_vintages[0].vmd0054_version if annual_vintages else "VMD0054_1_1_CURRENT",
            "vmd0054_source_equation": annual_vintages[0].vmd0054_source_equation if annual_vintages else "VMD0054_V1.1_EQ13",
            "vmd0054_transition_basis": annual_vintages[0].vmd0054_transition_basis if annual_vintages else "ACTIVE_STANDARD_V1_1",
            "vmd0054_effective_ruleset": annual_vintages[0].vmd0054_effective_ruleset if annual_vintages else "VMD0054_V1.1_ACTIVE",
            "tool16_procedure_reference": "TOOL16_PROCEDURE",
            "total_baseline_emissions_tco2e": str(tot_bsl_emissions),
            "total_project_emissions_tco2e": str(tot_wp_emissions),
            "total_emission_reductions_from_sources_tco2e": str(tot_delta_sources),
            "eq44_baseline_total_carbon_stock_change_tco2e": str(tot_eq44),
            "eq45_project_total_carbon_stock_change_tco2e": str(tot_eq45),
            "gross_reductions_er_tco2e": str(tot_er_gross),
            "gross_removals_cr_tco2e": str(tot_cr_gross),
            "total_leakage_tco2e": str(tot_lk),
            "total_leoa_tco2e": str(tot_leoa),
            "total_lkdisp_tco2e": str(tot_lkdisp),
            "total_lebr_tco2e": str(tot_lebr),
            "leakage_allocation_status": overall_lk_status,
            "leakage_allocation_er_lker_tco2e": str(tot_lker),
            "leakage_allocation_cr_lkcr_tco2e": str(tot_lkcr),
            "net_reductions_ernet_tco2e": str(tot_ernet),
            "net_removals_crnet_tco2e": str(tot_crnet),
            "total_net_ghg_errnet_tco2e": str(tot_errnet),
            "eq37_formula": "ER_t = I(Delta_CO2_wp) * (sum(Delta_E_sources,t) + min(0, Delta_CO2_wp,t) - min(0, Delta_CO2_bsl,t)) + (1 - I(Delta_CO2_wp)) * (sum(Delta_E_sources,t) + min(0, Delta_CO2_wp,t) - min(0, Delta_CO2_bsl,t) + max(0, Delta_CO2_wp,t) - max(0, Delta_CO2_bsl,t))",
            "eq75_formula": "BuER,t = NPR * (I(Delta_CO2_wp) * (min(0, Delta_CO2_wp,t) - min(0, Delta_CO2_bsl,t)) + (1 - I(Delta_CO2_wp)) * (min(0, Delta_CO2_wp,t) - min(0, Delta_CO2_bsl,t) + max(0, Delta_CO2_wp,t) - max(0, Delta_CO2_bsl,t)))",
            "eq76_formula": "BuCR,t = NPR * (I(Delta_CO2_wp) * (max(0, Delta_CO2_wp,t) - max(0, Delta_CO2_bsl,t)))",
            "eq77_formula": "VCUER,t = ERNET,t - BuER,t",
            "eq78_formula": "VCUCR,t = CRNET,t - BuCR,t",
            "eq79_formula": "VCU_t = VCUER,t + VCUCR,t",
            "internal_vcu_eligible_label": "INTERNAL_VCU_ELIGIBLE_QUANTITY",
            "vcu_readiness_status": vcu_status,
            "vcu_eligible_total_tco2e": str(tot_vcu) if tot_vcu is not None else None,
            "vvb_status": "NOT_CONFIGURED / EXTERNAL",
            "registry_status": "NOT_CONFIGURED / EXTERNAL",
            "registry_issued_quantity": None,
            # Explicit VMD0054 v1.1 Component Trace
            "vmd0054_trace": v_trace,
            "al_t": v_trace.get("al_t_ha"),
            "delta_c_biomass": v_trace.get("delta_c_biomass_tc_ha"),
            "delta_soc": v_trace.get("delta_soc_tc_ha"),
            "delta_cs_from_eq11": v_trace.get("delta_cs_tc_ha"),
            "elm_t": v_trace.get("elm_t_tco2e", "0.0000"),
            "lk_t_from_eq13": v_trace.get("lk_t_cumulative_tco2e", str(tot_lkdisp * elapsed_years)),
            "lk_prior": v_trace.get("lk_prior_tco2e", "0.0000"),
            "verification_period_years": str(elapsed_years),
            "vm0042_lkdisp_t_from_eq36": str(tot_lkdisp),
            "calculation_hash": calc_hash,
            "transition_governance": t_gov,
        },
    )
