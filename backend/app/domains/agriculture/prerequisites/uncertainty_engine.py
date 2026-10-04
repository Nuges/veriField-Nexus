"""
=============================================================================
VeriField Nexus — Uncertainty Input Readiness & Estimator Routing Engine
=============================================================================
Routes future error-propagation estimators according to the active quantification
pathway and validates input readiness without computing premature deductions.
=============================================================================
"""

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class UncertaintyEstimatorType(str, Enum):
    STRATIFIED_SAMPLING_ANALYTICAL = "STRATIFIED_SAMPLING_ANALYTICAL"  # VM0042 Eq. 48/49 direct sampling
    VMD0053_MONTE_CARLO_MODEL = "VMD0053_MONTE_CARLO_MODEL"            # VMD0053 biogeochemical parameter error
    VT0014_SPATIAL_KRIGING = "VT0014_SPATIAL_KRIGING"                  # VT0014 spatial prediction variance
    IPCC_TIER1_QUADRATURE = "IPCC_TIER1_QUADRATURE"                    # Error propagation for default factors


@dataclass(frozen=True)
class UncertaintyInputReadiness:
    estimator_type: str
    required_inputs: List[str]
    available_inputs: List[str]
    missing_inputs: List[str]
    confidence_level_pct: float
    degrees_of_freedom: int
    is_ready: bool
    status: str  # READY, INCOMPLETE, NOT_CONFIGURED
    routing_reason: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_uncertainty_input_readiness(
    soc_approach: str,
    uses_dsm: bool,
    strata_counts: Dict[str, int],
    strata_variances: Dict[str, float],
    strata_weights: Dict[str, float],
    confidence_level_pct: float = 90.0,
) -> UncertaintyInputReadiness:
    """
    Evaluates whether all statistical inputs required for future Phase 3B
    uncertainty deduction equations are present.
    """
    if uses_dsm:
        estimator = UncertaintyEstimatorType.VT0014_SPATIAL_KRIGING.value
        req = ["Spatial prediction variance grid", "Covariate prediction covariance", "Leave-one-out cross-validation residuals"]
        reason = "Digital Soil Mapping requires spatial uncertainty propagation under VT0014."
    elif soc_approach == "APPROACH_1":
        estimator = UncertaintyEstimatorType.VMD0053_MONTE_CARLO_MODEL.value
        req = ["Biogeochemical model parameter covariance", "Weather sensitivity variance", "Validation site residual standard error"]
        reason = "Quantification Approach 1 uses VMD0053 model error propagation."
    else:
        estimator = UncertaintyEstimatorType.STRATIFIED_SAMPLING_ANALYTICAL.value
        req = ["Stratum sample counts (n_i)", "Stratum sample variances (s_i²)", "Stratum area weights (W_i)", "Degrees of freedom"]
        reason = "Quantification Approach 2 uses VM0042 stratified random sampling error equations."

    avail: List[str] = []
    missing: List[str] = []

    total_samples = sum(strata_counts.values())
    k_strata = max(1, len(strata_counts))
    dof = max(0, total_samples - k_strata)

    if estimator == UncertaintyEstimatorType.STRATIFIED_SAMPLING_ANALYTICAL.value:
        if strata_counts and all(c > 0 for c in strata_counts.values()):
            avail.append("Stratum sample counts (n_i)")
        else:
            missing.append("Stratum sample counts (n_i)")

        if strata_variances and all(v >= 0.0 for v in strata_variances.values()):
            avail.append("Stratum sample variances (s_i²)")
        else:
            missing.append("Stratum sample variances (s_i²)")

        if strata_weights and abs(sum(strata_weights.values()) - 1.0) < 0.01:
            avail.append("Stratum area weights (W_i)")
        else:
            missing.append("Stratum area weights (W_i)")

        if dof >= 2:
            avail.append("Degrees of freedom")
        else:
            missing.append("Degrees of freedom")

    is_ready = len(missing) == 0 and len(avail) > 0
    status = "READY" if is_ready else "INCOMPLETE"

    return UncertaintyInputReadiness(
        estimator_type=estimator,
        required_inputs=req,
        available_inputs=avail,
        missing_inputs=missing,
        confidence_level_pct=confidence_level_pct,
        degrees_of_freedom=dof,
        is_ready=is_ready,
        status=status,
        routing_reason=reason,
    )
