"""
VeriField Nexus — Agriculture Domain: SOC Stock Change & Uncertainty Engine (VM0042 QA2)
========================================================================================
Authoritative implementation of Verra VM0042 v2.2 (21 October 2025) and 11 June 2026 C&C:
- Section 8.5.1:
  - Equation (44): Total carbon stock change in baseline scenario (partially configured: SOC pool only;
    tree and shrub carbon pools out of scope in Phase 3B-2).
  - Equation (45): Total carbon stock change in project scenario (partially configured: SOC pool only;
    tree and shrub carbon pools out of scope in Phase 3B-2).
  - Conservative sign indicator I(ΔCO2_soil_t) ensures uncertainty deduction increases magnitude of loss
    when project SOC performance is worse than baseline (I = -1) and decreases credited removals when
    project performance exceeds baseline (I = +1).
- Section 8.5.2:
  - Equation (46): Baseline scenario SOC stock change ΔCO2_soil_bsl,t (tCO2e/yr) across project area.
  - Equation (47): Project scenario SOC stock change ΔCO2_soil_wp,t (tCO2e/yr) across project area.
- QA2 Comparative Effect: Project scenario minus baseline-control scenario (tCO2e/yr).
- Section 8.6.2.2:
  - Equation (70): Sampling variance of mean project-wide SOC stock change (t C/ha/yr)^2 with exact
    algebraic parity between total-stratum variance and normalized area-weighted variance.
  - Equation (71): Stratum-level sampling variance accounting for paired core covariance without
    forcing positivity (covariance may be positive, zero, or negative based on empirical data).
- Section 8.6.2.2 / Figure 5:
  - Equation (74): Student's t uncertainty deduction at 66.7% confidence (p = 0.667) across design
    degrees of freedom.
  - ZERO DEADBAND: Equation (74) yields the deduction percentage directly; small nonzero uncertainty
    produces a corresponding small nonzero deduction. No 15% threshold bypass in Eq. (74) itself.
  - Zero-mean removal denominator safety: fails closed deterministically.
- Section 8.6.2:
  - Laboratory measurement error router: proficient dry combustion with verified QC is classified
    as NEGLIGIBLE_PER_VM0042_CONDITIONS (0.0 error variance). Spectroscopy / proximal sensors fail closed.
- Carbon Accounting Boundary:
  - PROJECT_NET_tCO2e is NOT_CONFIGURED (Phase 3B-2 SOC stock component only; zero Table 5 GHG sources,
    zero woody biomass, zero livestock, zero leakage, zero buffer pool deductions, zero VCUs).
  - Ledger Status: BLOCKED_FOR_AGRICULTURE. All credit minting attempts fail closed.
"""

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_EVEN, InvalidOperation
import hashlib
import json
import math
from typing import Any, Dict, List, Optional, Tuple, Union
import uuid


class SOCChangeCalculationError(Exception):
    """Base exception for SOC stock change and uncertainty quantification failures."""
    def __init__(self, code: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


# Exact Stoichiometric Ratio: 44 (molecular weight CO2) / 12 (atomic weight C)
# VM0042 v2.2 Section 8.5.2 & Equations (46) & (47)
CO2_TO_C_RATIO = Decimal("44") / Decimal("12")

# VM0042 v2.2 Section 8.6.2.2 Equation (74) Confidence Level: 66.7% one-sided Student's t (p = 0.667)
VM0042_CONFIDENCE_P_VALUE = 0.667

# Degrees of Freedom Estimator Classification for Stratified Random Sampling
DEFAULT_STRATIFIED_RANDOM_DF_ESTIMATOR = "DEFAULT_STRATIFIED_RANDOM_DF_ESTIMATOR"

# Equation 44 & 45 Readiness Classification (SOC Pool Only; Tree/Shrub Pools Deferred)
EQ44_EQ45_PARTIALLY_CONFIGURED_SOC_ONLY = "PARTIALLY_CONFIGURED_SOC_ONLY"

# Rounding precisions
PRECISION_MASS = Decimal("0.0001")        # 4 decimal places for t C/ha and t C/ha/yr
PRECISION_AREA = Decimal("0.0001")        # 4 decimal places for hectares
PRECISION_CO2 = Decimal("0.0001")         # 4 decimal places for tCO2e/yr
PRECISION_UNCERTAINTY = Decimal("0.0001") # 4 decimal places for %
PRECISION_FRACTION = Decimal("0.000001")  # 6 decimal places for deduction fraction
PRECISION_VARIANCE = Decimal("0.00000001") # 8 decimal places for variance


def calculate_student_t_0667(df: int) -> Decimal:
    """
    Computes exact Student's t value for one-sided 66.7% confidence (p = 0.667)
    with specified degrees of freedom, as required by VM0042 v2.2 Section 8.6.2.2 / Eq. (74).
    Uses scipy.stats.t.ppf directly. Fails closed if scipy is unavailable.
    """
    if df < 1:
        raise SOCChangeCalculationError(
            code="INVALID_DEGREES_OF_FREEDOM",
            message=f"Degrees of freedom must be >= 1 for Student's t calculation. Received {df}.",
        )

    try:
        from scipy.stats import t
        val = float(t.ppf(VM0042_CONFIDENCE_P_VALUE, df))
        return Decimal(str(val)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)
    except Exception as e:
        raise SOCChangeCalculationError(
            code="SCIPY_T_DISTRIBUTION_UNAVAILABLE",
            message=f"Deterministic scipy.stats Student's t evaluation failed for df={df}: {str(e)}",
        )


@dataclass
class StratumInputData:
    """Inputs for calculating SOC stock change and variance in a single stratum."""
    stratum_id: uuid.UUID
    stratum_code: str
    area_ha: Decimal
    baseline_mean_soc_t_c_per_ha: Decimal
    monitoring_mean_soc_t_c_per_ha: Decimal
    sample_count_project: int
    sample_count_baseline: int
    baseline_delta_soc_t_c_ha_yr: Optional[Decimal] = None
    sample_variance_project_t1: Optional[Decimal] = None
    sample_variance_project_t2: Optional[Decimal] = None
    paired_covariance_project: Optional[Decimal] = None
    sample_variance_baseline_t1: Optional[Decimal] = None
    sample_variance_baseline_t2: Optional[Decimal] = None
    paired_covariance_baseline: Optional[Decimal] = None
    paired_point_changes_project: Optional[List[Decimal]] = None
    paired_point_changes_baseline: Optional[List[Decimal]] = None


@dataclass
class StratumChangeOutput:
    """Calculated scenario stock change and variance components for a stratum."""
    stratum_id: uuid.UUID
    stratum_code: str
    area_ha: Decimal
    # Annualized rates per hectare in t C/ha/yr
    delta_soc_project_t_c_ha_yr: Decimal
    delta_soc_baseline_t_c_ha_yr: Decimal
    delta_soc_net_t_c_ha_yr: Decimal
    # Annualized rates per hectare in tCO2e/ha/yr (stoichiometric 44/12)
    delta_co2_project_tco2e_ha_yr: Decimal
    delta_co2_baseline_tco2e_ha_yr: Decimal
    delta_co2_net_tco2e_ha_yr: Decimal
    # VM0042 Section 8.5.2 Stratum Totals in tCO2e/yr
    baseline_soc_change_tco2e_yr: Decimal     # VM0042 Eq. 46 Stratum Component
    project_soc_change_tco2e_yr: Decimal      # VM0042 Eq. 47 Stratum Component
    qa2_net_soc_effect_tco2e_yr: Decimal      # QA2 Stratum Comparative Net Effect (Project - Baseline)
    # Stratum Variances
    variance_delta_soc_proj: Decimal
    variance_delta_soc_bsl: Decimal
    stratum_variance_net: Decimal
    sample_count_project: int
    sample_count_baseline: int
    degrees_of_freedom: int
    paired_covariance_project: Optional[Decimal] = None
    paired_covariance_baseline: Optional[Decimal] = None
    # Backwards-compatibility aliases
    total_project_delta_co2_tco2e_yr: Decimal = field(init=False)
    total_baseline_delta_co2_tco2e_yr: Decimal = field(init=False)
    total_net_delta_co2_tco2e_yr: Decimal = field(init=False)

    def __post_init__(self):
        self.total_project_delta_co2_tco2e_yr = self.project_soc_change_tco2e_yr
        self.total_baseline_delta_co2_tco2e_yr = self.baseline_soc_change_tco2e_yr
        self.total_net_delta_co2_tco2e_yr = self.qa2_net_soc_effect_tco2e_yr


@dataclass
class UncertaintyDeductionOutput:
    """VM0042 v2.2 Section 8.6.2.2 Equation (74) uncertainty deduction results."""
    degrees_of_freedom: int
    df_estimator: str
    student_t_value_0667: Decimal
    standard_error_delta_soc_t_c_ha_yr: Decimal
    standard_error_tco2e_yr: Decimal
    mean_net_removal_tco2e_yr: Decimal         # QA2 Net SOC Comparative Effect (tCO2e/yr)
    relative_uncertainty_pct: Decimal          # U (%) from Eq. (74)
    uncertainty_deduction_pct: Decimal         # Exactly equal to U (%) (No 15% deadband)
    uncertainty_deduction_fraction: Decimal    # U% / 100 (capped at 1.0)
    sign_indicator: int                        # I(ΔCO2_soil_t): +1 if net >= 0, -1 if net < 0
    uncertainty_adjusted_soc_effect_tco2e_yr: Decimal  # Post-uncertainty net SOC effect (tCO2e/yr)
    deduction_applied: bool
    denominator_non_positive: bool
    uncertainty_status: str
    # Backwards-compatibility alias
    adjusted_net_delta_co2_tco2e_yr: Decimal = field(init=False)
    allowable_uncertainty_pct: Decimal = Decimal("0.0000")

    def __post_init__(self):
        self.adjusted_net_delta_co2_tco2e_yr = self.uncertainty_adjusted_soc_effect_tco2e_yr


@dataclass
class ProjectSOCChangeOutput:
    """Aggregated project-level SOC stock change, variance, and uncertainty result."""
    total_project_area_ha: Decimal
    baseline_mean_soc_t_c_per_ha: Decimal
    monitoring_mean_soc_t_c_per_ha: Decimal
    delta_soc_project_t_c_ha_yr: Decimal
    delta_soc_baseline_t_c_ha_yr: Decimal
    delta_soc_net_t_c_ha_yr: Decimal
    delta_co2_project_tco2e_ha_yr: Decimal
    delta_co2_baseline_tco2e_ha_yr: Decimal
    delta_co2_net_tco2e_ha_yr: Decimal
    # Authoritative VM0042 Quantities
    baseline_soc_change_tco2e_yr: Decimal            # VM0042 Equation (46): ΔCO2_soil_bsl,t
    project_soc_change_tco2e_yr: Decimal             # VM0042 Equation (47): ΔCO2_soil_wp,t
    qa2_net_soc_effect_tco2e_yr: Decimal             # QA2 Comparative Effect: Eq. 47 - Eq. 46
    uncertainty_adjusted_soc_effect_tco2e_yr: Decimal # Post-uncertainty net SOC component
    sign_indicator: int                              # I(ΔCO2_soil_t) in Eqs. 44 & 45 (+1 or -1)
    # Variance and Uncertainty
    variance_delta_soc_project: Decimal
    variance_delta_soc_baseline: Decimal
    total_variance_delta_soc: Decimal
    uncertainty: UncertaintyDeductionOutput
    strata_results: List[StratumChangeOutput]
    measurement_error_status: str
    measurement_error_router: str
    # Architecture and Invariant Classifications
    eq44_eq45_status: str = EQ44_EQ45_PARTIALLY_CONFIGURED_SOC_ONLY
    df_estimator: str = DEFAULT_STRATIFIED_RANDOM_DF_ESTIMATOR
    carbon_accounting_status: str = "PARTIALLY_CONFIGURED_SOC_ONLY"
    project_net_tco2e: str = "NOT_CONFIGURED"
    ledger_status: str = "BLOCKED_FOR_AGRICULTURE"
    calculation_hash: str = ""
    # Backwards-compatibility aliases
    total_project_delta_co2_tco2e_yr: Decimal = field(init=False)
    total_baseline_delta_co2_tco2e_yr: Decimal = field(init=False)
    total_net_delta_co2_tco2e_yr: Decimal = field(init=False)
    adjusted_net_delta_co2_tco2e_yr: Decimal = field(init=False)

    def __post_init__(self):
        self.total_project_delta_co2_tco2e_yr = self.project_soc_change_tco2e_yr
        self.total_baseline_delta_co2_tco2e_yr = self.baseline_soc_change_tco2e_yr
        self.total_net_delta_co2_tco2e_yr = self.qa2_net_soc_effect_tco2e_yr
        self.adjusted_net_delta_co2_tco2e_yr = self.uncertainty_adjusted_soc_effect_tco2e_yr


def compute_sample_variance(values: List[Decimal]) -> Decimal:
    """Computes unbiased sample variance s^2 with (n - 1) denominator."""
    n = len(values)
    if n < 2:
        return Decimal("0.00000000")
    mean = sum(values) / Decimal(n)
    sq_diff_sum = sum((x - mean) ** 2 for x in values)
    return (sq_diff_sum / Decimal(n - 1)).quantize(PRECISION_VARIANCE, rounding=ROUND_HALF_EVEN)


def compute_sample_covariance(x_vals: List[Decimal], y_vals: List[Decimal]) -> Decimal:
    """
    Computes empirical sample covariance cov(X, Y) with (n - 1) denominator across paired points.
    NOTE: Covariance is not forced to be positive; empirical paired core measurements may exhibit
    positive, zero, or negative covariance.
    """
    if len(x_vals) != len(y_vals):
        raise SOCChangeCalculationError(
            code="PAIRED_SAMPLE_COUNT_MISMATCH",
            message=f"Paired core sample counts mismatch: {len(x_vals)} vs {len(y_vals)}.",
        )
    n = len(x_vals)
    if n < 2:
        return Decimal("0.00000000")
    mean_x = sum(x_vals) / Decimal(n)
    mean_y = sum(y_vals) / Decimal(n)
    cov_sum = sum((x_vals[i] - mean_x) * (y_vals[i] - mean_y) for i in range(n))
    return (cov_sum / Decimal(n - 1)).quantize(PRECISION_VARIANCE, rounding=ROUND_HALF_EVEN)


def calculate_stratum_soc_change_and_variance(
    stratum: StratumInputData,
    elapsed_years: Decimal,
) -> StratumChangeOutput:
    """
    Computes annualized SOC stock changes and sampling variance for a single stratum.
    Implements VM0042 v2.2 Equations (46), (47), and (71).
    Validation: elapsed_years must be strictly positive (x > 0).
    """
    if elapsed_years <= Decimal("0.0"):
        raise SOCChangeCalculationError(
            code="INVALID_ELAPSED_YEARS",
            message=f"Elapsed monitoring period years must be strictly positive (x > 0). Received {elapsed_years}.",
        )
    if stratum.area_ha <= Decimal("0.0"):
        raise SOCChangeCalculationError(
            code="INVALID_STRATUM_AREA",
            message=f"Stratum {stratum.stratum_code} area must be strictly positive. Received {stratum.area_ha} ha.",
        )

    # 1. Project annual stock change rate in t C/ha/yr: (SOC_t2 - SOC_t1) / x
    delta_soc_proj = (
        (stratum.monitoring_mean_soc_t_c_per_ha - stratum.baseline_mean_soc_t_c_per_ha) / elapsed_years
    ).quantize(PRECISION_MASS, rounding=ROUND_HALF_EVEN)

    # 2. Baseline annual stock change rate in t C/ha/yr
    delta_soc_bsl = Decimal("0.0000")
    if stratum.baseline_delta_soc_t_c_ha_yr is not None:
        delta_soc_bsl = Decimal(str(stratum.baseline_delta_soc_t_c_ha_yr)).quantize(
            PRECISION_MASS, rounding=ROUND_HALF_EVEN
        )

    # Net comparative SOC rate per ha: delta_proj - delta_bsl
    delta_soc_net = (delta_soc_proj - delta_soc_bsl).quantize(PRECISION_MASS, rounding=ROUND_HALF_EVEN)

    # 3. Stoichiometric conversion to tCO2e/ha/yr using exact Decimal 44/12
    delta_co2_proj = (delta_soc_proj * CO2_TO_C_RATIO).quantize(PRECISION_MASS, rounding=ROUND_HALF_EVEN)
    delta_co2_bsl = (delta_soc_bsl * CO2_TO_C_RATIO).quantize(PRECISION_MASS, rounding=ROUND_HALF_EVEN)
    delta_co2_net = (delta_soc_net * CO2_TO_C_RATIO).quantize(PRECISION_MASS, rounding=ROUND_HALF_EVEN)

    # 4. Stratum Total CO2 Changes in tCO2e/yr (VM0042 Section 8.5.2)
    # Equation (46) Stratum Component: Baseline Scenario SOC Stock Change (tCO2e/yr)
    bsl_change_tco2e_yr = (delta_co2_bsl * stratum.area_ha).quantize(PRECISION_CO2, rounding=ROUND_HALF_EVEN)
    # Equation (47) Stratum Component: Project Scenario SOC Stock Change (tCO2e/yr)
    proj_change_tco2e_yr = (delta_co2_proj * stratum.area_ha).quantize(PRECISION_CO2, rounding=ROUND_HALF_EVEN)
    # QA2 Stratum Comparative Net Effect: Project minus Baseline (tCO2e/yr)
    qa2_net_effect_tco2e_yr = (proj_change_tco2e_yr - bsl_change_tco2e_yr).quantize(
        PRECISION_CO2, rounding=ROUND_HALF_EVEN
    )

    # 5. Equation (71): Stratum sampling variance calculation
    n_p = stratum.sample_count_project
    if n_p < 2:
        raise SOCChangeCalculationError(
            code="INSUFFICIENT_STRATUM_SAMPLE_COUNT",
            message=f"Stratum {stratum.stratum_code} project sample count ({n_p}) must be >= 2 to compute sampling variance.",
        )

    # Direct paired-differences check:
    if stratum.paired_point_changes_project and len(stratum.paired_point_changes_project) >= 2:
        s2_delta = compute_sample_variance(stratum.paired_point_changes_project)
        var_proj = (s2_delta / Decimal(n_p)).quantize(PRECISION_VARIANCE, rounding=ROUND_HALF_EVEN)
        cov_proj = stratum.paired_covariance_project
    elif (
        stratum.sample_variance_project_t1 is not None
        and stratum.sample_variance_project_t2 is not None
    ):
        # Component form: (1 / (x^2 * n)) * [ s^2_t1 + s^2_t2 - 2 * cov(t1, t2) ]
        s2_t1 = stratum.sample_variance_project_t1
        s2_t2 = stratum.sample_variance_project_t2
        cov = stratum.paired_covariance_project or Decimal("0.00000000")
        cov_proj = cov
        bracket = s2_t1 + s2_t2 - (Decimal("2.0") * cov)
        bracket = max(Decimal("0.00000000"), bracket)
        x2_n = (elapsed_years ** 2) * Decimal(n_p)
        var_proj = (bracket / x2_n).quantize(PRECISION_VARIANCE, rounding=ROUND_HALF_EVEN)
    else:
        var_proj = Decimal("0.00000000")
        cov_proj = None

    # Baseline variance component:
    n_b = stratum.sample_count_baseline
    var_bsl = Decimal("0.00000000")
    cov_bsl = None
    if n_b >= 2:
        if stratum.paired_point_changes_baseline and len(stratum.paired_point_changes_baseline) >= 2:
            s2_delta_b = compute_sample_variance(stratum.paired_point_changes_baseline)
            var_bsl = (s2_delta_b / Decimal(n_b)).quantize(PRECISION_VARIANCE, rounding=ROUND_HALF_EVEN)
            cov_bsl = stratum.paired_covariance_baseline
        elif (
            stratum.sample_variance_baseline_t1 is not None
            and stratum.sample_variance_baseline_t2 is not None
        ):
            s2_b_t1 = stratum.sample_variance_baseline_t1
            s2_b_t2 = stratum.sample_variance_baseline_t2
            cov_b = stratum.paired_covariance_baseline or Decimal("0.00000000")
            cov_bsl = cov_b
            bracket_b = max(Decimal("0.00000000"), s2_b_t1 + s2_b_t2 - (Decimal("2.0") * cov_b))
            x2_nb = (elapsed_years ** 2) * Decimal(n_b)
            var_bsl = (bracket_b / x2_nb).quantize(PRECISION_VARIANCE, rounding=ROUND_HALF_EVEN)

    stratum_var_net = (var_proj + var_bsl).quantize(PRECISION_VARIANCE, rounding=ROUND_HALF_EVEN)
    dof = (n_p - 1) + (max(0, n_b - 1))

    return StratumChangeOutput(
        stratum_id=stratum.stratum_id,
        stratum_code=stratum.stratum_code,
        area_ha=stratum.area_ha.quantize(PRECISION_AREA, rounding=ROUND_HALF_EVEN),
        delta_soc_project_t_c_ha_yr=delta_soc_proj,
        delta_soc_baseline_t_c_ha_yr=delta_soc_bsl,
        delta_soc_net_t_c_ha_yr=delta_soc_net,
        delta_co2_project_tco2e_ha_yr=delta_co2_proj,
        delta_co2_baseline_tco2e_ha_yr=delta_co2_bsl,
        delta_co2_net_tco2e_ha_yr=delta_co2_net,
        baseline_soc_change_tco2e_yr=bsl_change_tco2e_yr,
        project_soc_change_tco2e_yr=proj_change_tco2e_yr,
        qa2_net_soc_effect_tco2e_yr=qa2_net_effect_tco2e_yr,
        variance_delta_soc_proj=var_proj,
        variance_delta_soc_bsl=var_bsl,
        stratum_variance_net=stratum_var_net,
        sample_count_project=n_p,
        sample_count_baseline=n_b,
        degrees_of_freedom=dof,
        paired_covariance_project=cov_proj,
        paired_covariance_baseline=cov_bsl,
    )


def calculate_vm0042_eq74_uncertainty_deduction(
    mean_net_removal_tco2e_yr: Decimal,
    total_project_area_ha: Decimal,
    total_variance_delta_soc: Decimal,
    degrees_of_freedom: int,
) -> UncertaintyDeductionOutput:
    """
    Computes VM0042 v2.2 Section 8.6.2.2 Equation (74) uncertainty deduction at 66.7% confidence level:
        UNC_Δ,t = ( sqrt(s²_Δ,t) / |mean_Δ,t| * 100 ) * t_0.667

    CRITICAL METHODOLOGY RULES:
    1. ZERO DEADBAND: Equation (74) yields the deduction percentage directly. Any nonzero relative
       uncertainty produces an exact corresponding nonzero deduction fraction. No 15% deadband.
    2. ZERO VARIANCE: If s² == 0, UNC_Δ,t = 0.0000% and deduction fraction is 0.000000.
    3. ZERO DENOMINATOR: If mean_net_removal == 0 and variance > 0, fails closed deterministically
       with code ZERO_MEAN_REMOVAL_UNDEFINED_UNCERTAINTY.
    4. CONSERVATIVE SIGN INDICATOR: I(ΔCO2_soil_t) in Equations (44) & (45):
       - If mean_net_removal >= 0: I = +1. Adjusted net effect is mean * (1 - UNC_fraction), reducing credits.
       - If mean_net_removal < 0:  I = -1. Adjusted net effect is mean * (1 + UNC_fraction), increasing loss magnitude.
    """
    if degrees_of_freedom < 1:
        raise SOCChangeCalculationError(
            code="INSUFFICIENT_DEGREES_OF_FREEDOM",
            message=f"Degrees of freedom ({degrees_of_freedom}) is insufficient for uncertainty deduction (minimum 1 required).",
        )

    # 1. Standard Error of project mean annual net SOC change rate (t C/ha/yr)
    se_soc_float = math.sqrt(float(max(Decimal("0.0"), total_variance_delta_soc)))
    se_soc = Decimal(str(se_soc_float)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_EVEN)

    # 2. Standard Error in tCO2e/yr: Area_total * (44/12) * SE_SOC
    se_co2 = (total_project_area_ha * CO2_TO_C_RATIO * se_soc).quantize(PRECISION_CO2, rounding=ROUND_HALF_EVEN)

    # 3. Student's t critical value for p = 0.667
    t_val = calculate_student_t_0667(degrees_of_freedom)

    # 4. Denominator & Zero Checks
    if mean_net_removal_tco2e_yr == Decimal("0.0000"):
        if total_variance_delta_soc == Decimal("0.00000000"):
            # Perfectly measured zero change
            return UncertaintyDeductionOutput(
                degrees_of_freedom=degrees_of_freedom,
                df_estimator=DEFAULT_STRATIFIED_RANDOM_DF_ESTIMATOR,
                student_t_value_0667=t_val,
                standard_error_delta_soc_t_c_ha_yr=Decimal("0.000000"),
                standard_error_tco2e_yr=Decimal("0.0000"),
                mean_net_removal_tco2e_yr=Decimal("0.0000"),
                relative_uncertainty_pct=Decimal("0.0000"),
                uncertainty_deduction_pct=Decimal("0.0000"),
                uncertainty_deduction_fraction=Decimal("0.000000"),
                sign_indicator=1,
                uncertainty_adjusted_soc_effect_tco2e_yr=Decimal("0.0000"),
                deduction_applied=False,
                denominator_non_positive=False,
                uncertainty_status="ZERO_CHANGE_ZERO_VARIANCE",
            )
        else:
            # Undefined relative uncertainty (divide by zero)
            raise SOCChangeCalculationError(
                code="ZERO_MEAN_REMOVAL_UNDEFINED_UNCERTAINTY",
                message="Mean net comparative SOC effect is zero with non-zero variance; relative uncertainty is mathematically undefined (zero denominator).",
                details={
                    "mean_net_removal_tco2e_yr": str(mean_net_removal_tco2e_yr),
                    "total_variance_delta_soc": str(total_variance_delta_soc),
                    "standard_error_tco2e_yr": str(se_co2),
                },
            )

    # 5. Equation (74): Relative uncertainty U (%) = (t_0.667 * SE_co2 / |Mean_removal|) * 100
    abs_mean = abs(mean_net_removal_tco2e_yr)
    u_pct = ((t_val * se_co2 / abs_mean) * Decimal("100.0")).quantize(
        PRECISION_UNCERTAINTY, rounding=ROUND_HALF_EVEN
    )

    # 6. Authoritative Deduction: UNC% = U% directly (NO 15% DEADBAND)
    deduction_pct = u_pct
    deduction_fraction = (deduction_pct / Decimal("100.0")).quantize(
        PRECISION_FRACTION, rounding=ROUND_HALF_EVEN
    )
    if deduction_fraction > Decimal("1.000000"):
        deduction_fraction = Decimal("1.000000")

    # 7. Equations (44) & (45) Conservative Sign Indicator:
    # I(ΔCO2_soil_t) = +1 if mean >= 0, else -1
    sign_ind = 1 if mean_net_removal_tco2e_yr >= Decimal("0.0000") else -1

    # Conservative multiplier: (1 - deduction_fraction * sign_ind)
    # If mean > 0 (I = +1): multiplier = (1 - fraction) <= 1.0 (reduces credited removals)
    # If mean < 0 (I = -1): multiplier = (1 + fraction) >= 1.0 (increases loss magnitude)
    adjustment_factor = Decimal("1.000000") - (deduction_fraction * Decimal(sign_ind))
    adjusted_removal = (mean_net_removal_tco2e_yr * adjustment_factor).quantize(
        PRECISION_CO2, rounding=ROUND_HALF_EVEN
    )

    deduction_applied = deduction_fraction > Decimal("0.000000")
    status = "EXACT_EQ74_DEDUCTION_APPLIED" if deduction_applied else "ZERO_VARIANCE_ZERO_DEDUCTION"

    return UncertaintyDeductionOutput(
        degrees_of_freedom=degrees_of_freedom,
        df_estimator=DEFAULT_STRATIFIED_RANDOM_DF_ESTIMATOR,
        student_t_value_0667=t_val,
        standard_error_delta_soc_t_c_ha_yr=se_soc,
        standard_error_tco2e_yr=se_co2,
        mean_net_removal_tco2e_yr=mean_net_removal_tco2e_yr,
        relative_uncertainty_pct=u_pct,
        uncertainty_deduction_pct=deduction_pct,
        uncertainty_deduction_fraction=deduction_fraction,
        sign_indicator=sign_ind,
        uncertainty_adjusted_soc_effect_tco2e_yr=adjusted_removal,
        deduction_applied=deduction_applied,
        denominator_non_positive=mean_net_removal_tco2e_yr < Decimal("0.0000"),
        uncertainty_status=status,
    )


def route_measurement_error(
    laboratory_method: str,
    lab_qa_verified: bool,
    active_lab_proficiency: bool,
) -> Tuple[str, str, Decimal]:
    """
    Evaluates laboratory measurement error under VM0042 Section 8.6.2.
    Proficient dry combustion elemental analysis with verified QA/QC is classified as negligible.
    ISO/IEC 17025 accreditation alone without proficiency evidence fails closed.
    Returns: (measurement_error_status, measurement_error_router, error_variance)
    """
    method = (laboratory_method or "").strip().upper()

    if method in ("DRY_COMBUSTION", "ELEMENTAL_ANALYSIS"):
        if not lab_qa_verified or not active_lab_proficiency:
            raise SOCChangeCalculationError(
                code="LAB_PROFICIENCY_EVIDENCE_INCOMPLETE",
                message="Laboratory analysis lacks demonstrated proficiency and quality-control evidence required for the conventional QA2 measurement-error pathway under VM0042 Section 8.6.2.",
                details={
                    "method": method,
                    "lab_qa_verified": lab_qa_verified,
                    "active_lab_proficiency": active_lab_proficiency,
                },
            )
        return (
            "NEGLIGIBLE_PER_VM0042_CONDITIONS",
            "CONVENTIONAL_DRY_COMBUSTION",
            Decimal("0.00000000"),
        )

    if method in ("VIS_NIR", "MIR", "PROXIMAL_SENSOR", "SPECTROSCOPY", "SPECTROSCOPY_WITH_DIRECT_CALIBRATION"):
        raise SOCChangeCalculationError(
            code="QA2_ALTERNATIVE_MEASUREMENT_UNCERTAINTY_NOT_CONFIGURED",
            message="Alternative sensor / proximal measurement error propagation (VM0042 Eqs. 72/73) is not configured in this release.",
            details={"method": method},
        )

    raise SOCChangeCalculationError(
        code="UNSUPPORTED_ANALYSIS_METHOD",
        message=f"Analysis method '{method}' is not recognized under VM0042 QA2 Measure & Re-Measure pathway.",
    )


def aggregate_project_qa2_soc_change(
    strata_inputs: List[StratumInputData],
    elapsed_years: Decimal,
    laboratory_method: str = "DRY_COMBUSTION",
    lab_qa_verified: bool = True,
    active_lab_proficiency: bool = True,
) -> ProjectSOCChangeOutput:
    """
    Full VM0042 v2.2 QA2 Project Aggregation:
    - Calculates scenario stock changes per stratum.
    - Aggregates Equation (46) baseline SOC stock change: ΔCO2_soil_bsl,t (tCO2e/yr).
    - Aggregates Equation (47) project SOC stock change: ΔCO2_soil_wp,t (tCO2e/yr).
    - Calculates QA2 comparative effect: project minus baseline (tCO2e/yr).
    - Calculates project-area-weighted sampling variance (Eq. 70, 71).
    - Routes laboratory measurement error (verified dry combustion = negligible).
    - Calculates Student's t uncertainty deduction (Eq. 74) with ZERO DEADBAND.
    - Preserves conservative sign indicator I(ΔCO2_soil_t) in Equations (44) & (45).
    - Generates cryptographic verification hash.
    """
    if not strata_inputs:
        raise SOCChangeCalculationError(
            code="EMPTY_PROJECT_STRATA",
            message="Cannot compute project SOC change without strata data.",
        )

    # 1. Route laboratory measurement error
    err_status, err_router, err_var = route_measurement_error(
        laboratory_method=laboratory_method,
        lab_qa_verified=lab_qa_verified,
        active_lab_proficiency=active_lab_proficiency,
    )

    # 2. Calculate stratum-level results
    strata_results: List[StratumChangeOutput] = []
    total_area = Decimal("0.0000")
    total_bsl_stock_weighted = Decimal("0.0000")
    total_mon_stock_weighted = Decimal("0.0000")

    for s_in in strata_inputs:
        st_res = calculate_stratum_soc_change_and_variance(s_in, elapsed_years)
        strata_results.append(st_res)
        total_area += st_res.area_ha
        total_bsl_stock_weighted += (s_in.baseline_mean_soc_t_c_per_ha * st_res.area_ha)
        total_mon_stock_weighted += (s_in.monitoring_mean_soc_t_c_per_ha * st_res.area_ha)

    if total_area <= Decimal("0.0000"):
        raise SOCChangeCalculationError(
            code="INVALID_TOTAL_AREA",
            message="Total project area must be strictly positive.",
        )

    total_area = total_area.quantize(PRECISION_AREA, rounding=ROUND_HALF_EVEN)
    bsl_mean_stock = (total_bsl_stock_weighted / total_area).quantize(PRECISION_MASS, rounding=ROUND_HALF_EVEN)
    mon_mean_stock = (total_mon_stock_weighted / total_area).quantize(PRECISION_MASS, rounding=ROUND_HALF_EVEN)

    # 3. Sum annualized scenario CO2 changes across all strata
    # Equation (46): Baseline Scenario SOC Stock Change (tCO2e/yr)
    tot_bsl_co2 = sum(s.baseline_soc_change_tco2e_yr for s in strata_results).quantize(
        PRECISION_CO2, rounding=ROUND_HALF_EVEN
    )
    # Equation (47): Project Scenario SOC Stock Change (tCO2e/yr)
    tot_proj_co2 = sum(s.project_soc_change_tco2e_yr for s in strata_results).quantize(
        PRECISION_CO2, rounding=ROUND_HALF_EVEN
    )
    # QA2 Net Comparative SOC Effect: Project minus Baseline (tCO2e/yr)
    tot_net_co2 = (tot_proj_co2 - tot_bsl_co2).quantize(PRECISION_CO2, rounding=ROUND_HALF_EVEN)

    # Project-level per-hectare rates
    delta_soc_proj = (sum(s.delta_soc_project_t_c_ha_yr * s.area_ha for s in strata_results) / total_area).quantize(
        PRECISION_MASS, rounding=ROUND_HALF_EVEN
    )
    delta_soc_bsl = (sum(s.delta_soc_baseline_t_c_ha_yr * s.area_ha for s in strata_results) / total_area).quantize(
        PRECISION_MASS, rounding=ROUND_HALF_EVEN
    )
    delta_soc_net = (delta_soc_proj - delta_soc_bsl).quantize(PRECISION_MASS, rounding=ROUND_HALF_EVEN)

    delta_co2_proj = (delta_soc_proj * CO2_TO_C_RATIO).quantize(PRECISION_MASS, rounding=ROUND_HALF_EVEN)
    delta_co2_bsl = (delta_soc_bsl * CO2_TO_C_RATIO).quantize(PRECISION_MASS, rounding=ROUND_HALF_EVEN)
    delta_co2_net = (delta_soc_net * CO2_TO_C_RATIO).quantize(PRECISION_MASS, rounding=ROUND_HALF_EVEN)

    # 4. Equation (70): Area-weighted sampling variance across project strata
    # Official form: s^2_mean = (1 / A_total^2) * sum( s^2_total,h )
    # Equivalent to: sum( (A_k / A_total)^2 * s^2_k )
    weighted_var_proj = Decimal("0.00000000")
    weighted_var_bsl = Decimal("0.00000000")

    for s in strata_results:
        w_k = s.area_ha / total_area
        w_k_sq = w_k ** 2
        weighted_var_proj += (w_k_sq * s.variance_delta_soc_proj)
        weighted_var_bsl += (w_k_sq * s.variance_delta_soc_bsl)

    weighted_var_proj = weighted_var_proj.quantize(PRECISION_VARIANCE, rounding=ROUND_HALF_EVEN)
    weighted_var_bsl = weighted_var_bsl.quantize(PRECISION_VARIANCE, rounding=ROUND_HALF_EVEN)
    tot_var = (weighted_var_proj + weighted_var_bsl + err_var).quantize(
        PRECISION_VARIANCE, rounding=ROUND_HALF_EVEN
    )

    # 5. Total degrees of freedom across all strata
    total_dof = sum(s.degrees_of_freedom for s in strata_results)
    if total_dof < 1:
        total_dof = 1

    # 6. Equation (74): Uncertainty deduction calculation (NO DEADBAND)
    unc = calculate_vm0042_eq74_uncertainty_deduction(
        mean_net_removal_tco2e_yr=tot_net_co2,
        total_project_area_ha=total_area,
        total_variance_delta_soc=tot_var,
        degrees_of_freedom=total_dof,
    )

    # 7. Deterministic cryptographic hash of output payload
    hash_payload = {
        "total_project_area_ha": str(total_area),
        "elapsed_years": str(elapsed_years),
        "baseline_mean_soc_t_c_per_ha": str(bsl_mean_stock),
        "monitoring_mean_soc_t_c_per_ha": str(mon_mean_stock),
        "baseline_soc_change_tco2e_yr": str(tot_bsl_co2),
        "project_soc_change_tco2e_yr": str(tot_proj_co2),
        "qa2_net_soc_effect_tco2e_yr": str(tot_net_co2),
        "sign_indicator": unc.sign_indicator,
        "total_variance_delta_soc": str(tot_var),
        "degrees_of_freedom": total_dof,
        "uncertainty_deduction_pct": str(unc.uncertainty_deduction_pct),
        "uncertainty_adjusted_soc_effect_tco2e_yr": str(unc.uncertainty_adjusted_soc_effect_tco2e_yr),
        "eq44_eq45_status": EQ44_EQ45_PARTIALLY_CONFIGURED_SOC_ONLY,
        "df_estimator": DEFAULT_STRATIFIED_RANDOM_DF_ESTIMATOR,
        "strata_results": [
            {
                "stratum_code": s.stratum_code,
                "area_ha": str(s.area_ha),
                "baseline_soc_change_tco2e_yr": str(s.baseline_soc_change_tco2e_yr),
                "project_soc_change_tco2e_yr": str(s.project_soc_change_tco2e_yr),
                "qa2_net_soc_effect_tco2e_yr": str(s.qa2_net_soc_effect_tco2e_yr),
                "stratum_variance_net": str(s.stratum_variance_net),
            }
            for s in strata_results
        ],
    }
    calc_hash = hashlib.sha256(json.dumps(hash_payload, sort_keys=True).encode("utf-8")).hexdigest()

    return ProjectSOCChangeOutput(
        total_project_area_ha=total_area,
        baseline_mean_soc_t_c_per_ha=bsl_mean_stock,
        monitoring_mean_soc_t_c_per_ha=mon_mean_stock,
        delta_soc_project_t_c_ha_yr=delta_soc_proj,
        delta_soc_baseline_t_c_ha_yr=delta_soc_bsl,
        delta_soc_net_t_c_ha_yr=delta_soc_net,
        delta_co2_project_tco2e_ha_yr=delta_co2_proj,
        delta_co2_baseline_tco2e_ha_yr=delta_co2_bsl,
        delta_co2_net_tco2e_ha_yr=delta_co2_net,
        baseline_soc_change_tco2e_yr=tot_bsl_co2,
        project_soc_change_tco2e_yr=tot_proj_co2,
        qa2_net_soc_effect_tco2e_yr=tot_net_co2,
        uncertainty_adjusted_soc_effect_tco2e_yr=unc.uncertainty_adjusted_soc_effect_tco2e_yr,
        sign_indicator=unc.sign_indicator,
        variance_delta_soc_project=weighted_var_proj,
        variance_delta_soc_baseline=weighted_var_bsl,
        total_variance_delta_soc=tot_var,
        uncertainty=unc,
        strata_results=strata_results,
        measurement_error_status=err_status,
        measurement_error_router=err_router,
        eq44_eq45_status=EQ44_EQ45_PARTIALLY_CONFIGURED_SOC_ONLY,
        df_estimator=DEFAULT_STRATIFIED_RANDOM_DF_ESTIMATOR,
        carbon_accounting_status="PARTIALLY_CONFIGURED_SOC_ONLY",
        project_net_tco2e="NOT_CONFIGURED",
        ledger_status="BLOCKED_FOR_AGRICULTURE",
        calculation_hash=calc_hash,
    )
