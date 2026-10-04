"""
=============================================================================
VeriField Nexus — VM0042 Sampling Design & Statistical Allocation Engine
=============================================================================
Evaluates sampling design, stratification, spatial point allocation, and optional
power analysis pursuant to VM0042 v2.2 Section 8.

Methodology Normative Design:
- STRATIFIED RANDOM SAMPLING is the authoritative default standard method.
- MULTISTAGE_WITH_STRATIFIED_RANDOM_FINAL_STAGE is acceptable as standard-compliant.
- SIMPLE_RANDOM across entire project without stratification, SYSTEMATIC_GRID,
  and alternative designs require an approved VCS methodology deviation.
- Power Analysis is an optional advisory tool; parameter status is audited
  (normative example vs project-configured).
=============================================================================
"""

import math
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class SamplingDesignType(str, Enum):
    STRATIFIED_RANDOM = "STRATIFIED_RANDOM"
    MULTISTAGE_WITH_STRATIFIED_RANDOM_FINAL_STAGE = "MULTISTAGE_WITH_STRATIFIED_RANDOM_FINAL_STAGE"
    SIMPLE_RANDOM = "SIMPLE_RANDOM"
    SYSTEMATIC_GRID = "SYSTEMATIC_GRID"
    GRID_OR_LINEAR = "GRID_OR_LINEAR"
    ALTERNATIVE_DESIGN = "ALTERNATIVE_DESIGN"
    VT0014_DSM = "VT0014_DSM"


class SamplingDesignStandardStatus(str, Enum):
    STANDARD_METHOD = "STANDARD_METHOD"
    METHODOLOGY_DEVIATION_REQUIRED = "METHODOLOGY_DEVIATION_REQUIRED"
    NOT_RECOMMENDED = "NOT_RECOMMENDED"


class PowerAnalysisStatus(str, Enum):
    NOT_RUN = "NOT_RUN"
    RUN = "RUN"
    INSUFFICIENT_INPUT = "INSUFFICIENT_INPUT"
    RESULT_AVAILABLE = "RESULT_AVAILABLE"


class ParameterNormativeStatus(str, Enum):
    NORMATIVE_EXAMPLE = "NORMATIVE_EXAMPLE"
    PROJECT_CONFIGURED = "PROJECT_CONFIGURED"
    DERIVED = "DERIVED"


class DesignSufficiencyStatus(str, Enum):
    READY = "READY"
    READY_WITH_NONBLOCKING_ADVISORY = "READY_WITH_NONBLOCKING_ADVISORY"
    INCOMPLETE = "INCOMPLETE"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class PowerAnalysisParameterAudit:
    parameter_name: str
    parameter_value: float
    normative_status: str  # NORMATIVE_EXAMPLE, PROJECT_CONFIGURED, DERIVED
    official_source: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PowerAnalysisResult:
    status: str
    is_mandatory: bool
    calculated_sample_count: Optional[int]
    minimum_detectable_difference: Optional[float]
    expected_variance: Optional[float]
    confidence_level_pct: float
    statistical_power_pct: float
    alpha: float
    beta: float
    parameter_audit: List[PowerAnalysisParameterAudit]
    notes: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "is_mandatory": self.is_mandatory,
            "calculated_sample_count": self.calculated_sample_count,
            "minimum_detectable_difference": self.minimum_detectable_difference,
            "expected_variance": self.expected_variance,
            "confidence_level_pct": self.confidence_level_pct,
            "statistical_power_pct": self.statistical_power_pct,
            "alpha": self.alpha,
            "beta": self.beta,
            "parameter_audit": [p.to_dict() for p in self.parameter_audit],
            "notes": self.notes,
        }


@dataclass(frozen=True)
class SamplingDesignAssessment:
    design_type: str
    design_compliance: str  # STANDARD_METHOD, METHODOLOGY_DEVIATION_REQUIRED, NOT_RECOMMENDED
    is_standard_default: bool
    has_approved_methodology_deviation: bool
    is_design_defined: bool
    is_stratification_defined: bool
    is_point_selection_documented: bool
    is_variance_basis_available: bool
    is_minimum_depth_ready: bool
    is_baseline_monitoring_linked: bool
    total_intended_points: int
    total_actual_points: int
    variance_estimate: Optional[float]
    power_analysis: PowerAnalysisResult
    overall_status: str
    advisories: List[str]
    blocking_defects: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "design_type": self.design_type,
            "design_compliance": self.design_compliance,
            "is_standard_default": self.is_standard_default,
            "has_approved_methodology_deviation": self.has_approved_methodology_deviation,
            "is_design_defined": self.is_design_defined,
            "is_stratification_defined": self.is_stratification_defined,
            "is_point_selection_documented": self.is_point_selection_documented,
            "is_variance_basis_available": self.is_variance_basis_available,
            "is_minimum_depth_ready": self.is_minimum_depth_ready,
            "is_baseline_monitoring_linked": self.is_baseline_monitoring_linked,
            "total_intended_points": self.total_intended_points,
            "total_actual_points": self.total_actual_points,
            "variance_estimate": self.variance_estimate,
            "power_analysis": self.power_analysis.to_dict(),
            "overall_status": self.overall_status,
            "advisories": self.advisories,
            "blocking_defects": self.blocking_defects,
        }


def audit_power_parameters(
    confidence_level_pct: float,
    statistical_power_pct: float,
) -> Tuple[float, float, List[PowerAnalysisParameterAudit]]:
    """
    Audits alpha and power/beta parameters against VM0042 Section 8 normative examples.
    """
    alpha = (100.0 - confidence_level_pct) / 100.0
    beta = (100.0 - statistical_power_pct) / 100.0

    # VM0042 Section 8.2: alpha = 0.05 (two-sided) and power = 90% (beta = 0.10) are cited examples.
    alpha_status = (
        ParameterNormativeStatus.NORMATIVE_EXAMPLE.value
        if math.isclose(alpha, 0.05, abs_tol=1e-4)
        else ParameterNormativeStatus.PROJECT_CONFIGURED.value
    )
    power_status = (
        ParameterNormativeStatus.NORMATIVE_EXAMPLE.value
        if math.isclose(statistical_power_pct, 90.0, abs_tol=1e-4)
        else ParameterNormativeStatus.PROJECT_CONFIGURED.value
    )

    audit_list = [
        PowerAnalysisParameterAudit(
            parameter_name="alpha (significance_level)",
            parameter_value=alpha,
            normative_status=alpha_status,
            official_source="VM0042 v2.2 Section 8.2 (t_alpha two-sided critical value; 0.05 normative example)",
        ),
        PowerAnalysisParameterAudit(
            parameter_name="power (1 - beta)",
            parameter_value=statistical_power_pct / 100.0,
            normative_status=power_status,
            official_source="VM0042 v2.2 Section 8.2 (t_beta one-sided Type II term; 90% power / 0.10 beta normative example)",
        ),
        PowerAnalysisParameterAudit(
            parameter_name="t_alpha_critical",
            parameter_value=1.960 if confidence_level_pct >= 95.0 else 1.645,
            normative_status=ParameterNormativeStatus.DERIVED.value,
            official_source="Student's t-distribution two-sided approximation",
        ),
        PowerAnalysisParameterAudit(
            parameter_name="t_beta_critical",
            parameter_value=1.282 if statistical_power_pct >= 90.0 else 0.842,
            normative_status=ParameterNormativeStatus.DERIVED.value,
            official_source="Student's t-distribution one-sided Type II error approximation",
        ),
    ]

    return alpha, beta, audit_list


def calculate_vm0042_power_analysis(
    expected_variance: float,
    minimum_detectable_difference: float,
    confidence_level_pct: float = 95.0,  # Default to 95% (alpha = 0.05) per Section 8 example
    statistical_power_pct: float = 90.0,  # Default to 90% (beta = 0.10) per Section 8 example
) -> PowerAnalysisResult:
    """
    Computes sample size from VM0042 Section 8.2 statistical power formulation:
        N = ((t_alpha/2 + t_beta)^2 * s^2) / (MDD^2)
    """
    alpha, beta, param_audit = audit_power_parameters(confidence_level_pct, statistical_power_pct)

    if expected_variance <= 0.0 or minimum_detectable_difference <= 0.0:
        return PowerAnalysisResult(
            status=PowerAnalysisStatus.INSUFFICIENT_INPUT.value,
            is_mandatory=False,
            calculated_sample_count=None,
            minimum_detectable_difference=minimum_detectable_difference,
            expected_variance=expected_variance,
            confidence_level_pct=confidence_level_pct,
            statistical_power_pct=statistical_power_pct,
            alpha=alpha,
            beta=beta,
            parameter_audit=param_audit,
            notes="Variance and minimum detectable difference must be strictly positive.",
        )

    t_alpha = 1.960 if confidence_level_pct >= 95.0 else 1.645
    t_beta = 1.282 if statistical_power_pct >= 90.0 else 0.842

    numerator = ((t_alpha + t_beta) ** 2) * expected_variance
    denominator = minimum_detectable_difference ** 2

    n_exact = numerator / denominator
    n_recommended = max(3, math.ceil(n_exact))

    return PowerAnalysisResult(
        status=PowerAnalysisStatus.RESULT_AVAILABLE.value,
        is_mandatory=False,  # VM0042 §8: Project is NOT required to take the power analysis count
        calculated_sample_count=n_recommended,
        minimum_detectable_difference=float(minimum_detectable_difference),
        expected_variance=float(expected_variance),
        confidence_level_pct=float(confidence_level_pct),
        statistical_power_pct=float(statistical_power_pct),
        alpha=alpha,
        beta=beta,
        parameter_audit=param_audit,
        notes=(
            f"Power analysis advisory: {n_recommended} samples based on MDD={minimum_detectable_difference} "
            f"and s²={expected_variance}. Advisory only; project is not methodologically required to take this exact count."
        ),
    )


def evaluate_sampling_design(
    plan_version: Dict[str, Any],
    actual_points_count: int,
    strata_count: int,
    variance_basis: Optional[float] = None,
    run_power_analysis: bool = False,
    mdd: Optional[float] = None,
    has_minimum_depth_ready: bool = True,
    has_baseline_monitoring_linked: bool = True,
    has_approved_methodology_deviation: bool = False,
    deviation_justification: Optional[str] = None,
) -> SamplingDesignAssessment:
    """
    Evaluates sampling design sufficiency pursuant to VM0042 Section 8.
    """
    p_meta = plan_version or {}
    raw_design = str(p_meta.get("sampling_design_type") or p_meta.get("design_type") or "STRATIFIED_RANDOM").upper()
    intended_points = int(p_meta.get("target_sample_count") or p_meta.get("intended_points_count") or actual_points_count)

    # Classify design compliance (§7, §8, §39)
    if raw_design in ("STRATIFIED_RANDOM", "STRATIFIED_RANDOM_SAMPLING"):
        design_str = SamplingDesignType.STRATIFIED_RANDOM.value
        compliance = SamplingDesignStandardStatus.STANDARD_METHOD.value
        is_standard = True
    elif raw_design in (
        "MULTISTAGE_WITH_STRATIFIED_RANDOM_FINAL_STAGE",
        "MULTISTAGE_STRATIFIED",
        "TWO_STAGE_STRATIFIED",
    ):
        design_str = SamplingDesignType.MULTISTAGE_WITH_STRATIFIED_RANDOM_FINAL_STAGE.value
        compliance = SamplingDesignStandardStatus.STANDARD_METHOD.value
        is_standard = True
    elif raw_design in ("SIMPLE_RANDOM", "SIMPLE_RANDOM_SAMPLING", "COMPLETELY_RANDOM"):
        design_str = SamplingDesignType.SIMPLE_RANDOM.value
        compliance = SamplingDesignStandardStatus.METHODOLOGY_DEVIATION_REQUIRED.value
        is_standard = False
    elif raw_design in ("SYSTEMATIC_GRID", "GRID", "GRID_OR_LINEAR", "LINEAR_TRANSECT"):
        design_str = SamplingDesignType.GRID_OR_LINEAR.value
        compliance = SamplingDesignStandardStatus.NOT_RECOMMENDED.value
        is_standard = False
    elif raw_design in ("VT0014_DSM", "DSM"):
        design_str = SamplingDesignType.VT0014_DSM.value
        compliance = SamplingDesignStandardStatus.STANDARD_METHOD.value
        is_standard = True
    else:
        design_str = SamplingDesignType.ALTERNATIVE_DESIGN.value
        compliance = SamplingDesignStandardStatus.METHODOLOGY_DEVIATION_REQUIRED.value
        is_standard = False

    is_defined = bool(raw_design)
    is_strat_defined = strata_count > 0
    is_selection_documented = bool(p_meta.get("point_allocation_method") or p_meta.get("randomization_seed") or p_meta.get("is_locked"))
    is_variance_avail = variance_basis is not None and variance_basis > 0.0

    advisories: List[str] = []
    blocking: List[str] = []

    if not is_defined:
        blocking.append("SAMPLING_DESIGN_UNDOCUMENTED: No sampling design type configured.")

    # Stratification requirement for standard design
    if not is_strat_defined and is_standard:
        blocking.append("STRATIFICATION_UNDEFINED: At least one analytical stratum must be configured for stratified random design.")

    if actual_points_count == 0:
        blocking.append("SAMPLING_POINTS_MISSING: Zero actual sampling points recorded.")

    # Alternative design gating (§8, §39)
    if not is_standard:
        if not has_approved_methodology_deviation:
            blocking.append(
                f"METHODOLOGY_DEVIATION_REQUIRED: Design '{design_str}' is not the VM0042 default standard method. "
                "Requires approved VCS methodology deviation and scientific justification."
            )
        else:
            advisories.append(
                f"Methodology deviation active for sampling design '{design_str}'. Justification: {deviation_justification or 'Approved by VVB'}"
            )

    # Power Analysis Evaluation (§9, §40)
    if run_power_analysis and is_variance_avail and mdd and mdd > 0.0:
        power_res = calculate_vm0042_power_analysis(
            expected_variance=variance_basis,
            minimum_detectable_difference=mdd,
        )
        advisories.append(f"Power analysis completed: estimated {power_res.calculated_sample_count} samples for MDD={mdd}.")
    else:
        _, _, param_audit = audit_power_parameters(confidence_level_pct=95.0, statistical_power_pct=90.0)
        power_res = PowerAnalysisResult(
            status=PowerAnalysisStatus.NOT_RUN.value,
            is_mandatory=False,
            calculated_sample_count=None,
            minimum_detectable_difference=None,
            expected_variance=variance_basis,
            confidence_level_pct=95.0,
            statistical_power_pct=90.0,
            alpha=0.05,
            beta=0.10,
            parameter_audit=param_audit,
            notes="Power analysis not executed. Under VM0042 Section 8, power analysis is optional and absence does not block compliance.",
        )
        advisories.append("POWER_ANALYSIS_NOT_RUN: Statistical power analysis was not conducted. Project relies on variance basis and stratum allocation.")

    if not is_variance_avail:
        advisories.append("VARIANCE_BASIS_UNAVAILABLE: Pre-sampling variance basis not recorded. Allocation uncertainty may increase during deduction calculation.")

    if actual_points_count < intended_points:
        advisories.append(f"Sample shortfall advisory: {actual_points_count} points collected vs {intended_points} intended points.")

    # Determine overall status
    if blocking:
        overall = DesignSufficiencyStatus.BLOCKED.value
    elif not is_selection_documented or actual_points_count < 3:
        overall = DesignSufficiencyStatus.INCOMPLETE.value
    elif advisories:
        overall = DesignSufficiencyStatus.READY_WITH_NONBLOCKING_ADVISORY.value
    else:
        overall = DesignSufficiencyStatus.READY.value

    return SamplingDesignAssessment(
        design_type=design_str,
        design_compliance=compliance,
        is_standard_default=is_standard,
        has_approved_methodology_deviation=has_approved_methodology_deviation,
        is_design_defined=is_defined,
        is_stratification_defined=is_strat_defined,
        is_point_selection_documented=is_selection_documented,
        is_variance_basis_available=is_variance_avail,
        is_minimum_depth_ready=has_minimum_depth_ready,
        is_baseline_monitoring_linked=has_baseline_monitoring_linked,
        total_intended_points=intended_points,
        total_actual_points=actual_points_count,
        variance_estimate=variance_basis,
        power_analysis=power_res,
        overall_status=overall,
        advisories=advisories,
        blocking_defects=blocking,
    )
