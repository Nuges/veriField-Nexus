"""
=============================================================================
VeriField Nexus — Baseline / Monitoring Pairing & Method Consistency Engine
=============================================================================
Evaluates temporal measurement pairing readiness between baseline and monitoring
campaigns without calculating SOC deltas or carbon quantities.
=============================================================================
"""

from dataclasses import asdict, dataclass
from datetime import date
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class MethodConsistencyStatus(str, Enum):
    CONSISTENT = "CONSISTENT"
    ALLOWED_TRANSITION = "ALLOWED_TRANSITION"
    REQUIRES_RECONCILIATION = "REQUIRES_RECONCILIATION"
    INCOMPATIBLE = "INCOMPATIBLE"


@dataclass(frozen=True)
class BaselineMonitoringPair:
    pair_id: str
    quantification_unit_id: str
    stratum_id: str
    baseline_campaign_id: str
    monitoring_campaign_id: str
    baseline_period_end: str
    monitoring_period_end: str
    baseline_sample_count: int
    monitoring_sample_count: int
    measurement_method: str
    methodology_route: str
    method_consistency: str
    is_pairing_eligible: bool
    reconciliation_notes: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_method_consistency(
    baseline_meta: Dict[str, Any],
    monitoring_meta: Dict[str, Any],
) -> Tuple[MethodConsistencyStatus, str]:
    """
    Evaluates methodological consistency between baseline and monitoring campaigns.
    """
    b_tech = (baseline_meta.get("analysis_method") or baseline_meta.get("lab_method") or "DRY_COMBUSTION").upper()
    m_tech = (monitoring_meta.get("analysis_method") or monitoring_meta.get("lab_method") or "DRY_COMBUSTION").upper()

    b_depth_max = float(baseline_meta.get("max_depth_cm") or 30.0)
    m_depth_max = float(monitoring_meta.get("max_depth_cm") or 30.0)

    # Identical
    if b_tech == m_tech and abs(b_depth_max - m_depth_max) < 1.0:
        return MethodConsistencyStatus.CONSISTENT, "Identical analytical method and sampling depth horizon across both periods."

    # Allowed transitions under VM0042 (e.g. Walkley-Black baseline converted via local calibration factor to Dry Combustion)
    if b_tech in ("WALKLEY_BLACK", "WET_OXIDATION") and m_tech in ("DRY_COMBUSTION", "ELEMENTAL_ANALYSIS"):
        has_calibration = bool(monitoring_meta.get("walkley_black_calibration_factor"))
        if has_calibration:
            return (
                MethodConsistencyStatus.ALLOWED_TRANSITION,
                "Transition from wet oxidation to automated dry combustion supported by verified local calibration curve.",
            )
        else:
            return (
                MethodConsistencyStatus.REQUIRES_RECONCILIATION,
                "Analytical method change requires documented local calibration curve between Walkley-Black and Dry Combustion.",
            )

    # Depth mismatch
    if abs(b_depth_max - m_depth_max) >= 1.0:
        return (
            MethodConsistencyStatus.REQUIRES_RECONCILIATION,
            f"Depth mismatch: Baseline sampled to {b_depth_max:.1f} cm, monitoring to {m_depth_max:.1f} cm. ESM mass-spline reconciliation required.",
        )

    return MethodConsistencyStatus.INCOMPATIBLE, f"Incompatible measurement systems: {b_tech} vs {m_tech} without cross-calibration."


def evaluate_baseline_monitoring_pairing(
    quantification_unit_id: str,
    stratum_id: str,
    baseline_campaign: Dict[str, Any],
    monitoring_campaign: Dict[str, Any],
    baseline_samples: List[Dict[str, Any]],
    monitoring_samples: List[Dict[str, Any]],
    methodology_route: str = "VM0042_QA2_DIRECT",
) -> BaselineMonitoringPair:
    """
    Constructs an authoritative baseline/monitoring pair contract for future calculation.
    """
    b_id = str(baseline_campaign.get("id") or "BASELINE_CAMPAIGN")
    m_id = str(monitoring_campaign.get("id") or "MONITORING_CAMPAIGN")

    pair_id = f"PAIR_{b_id[:8]}_{m_id[:8]}_{stratum_id[:8]}"

    b_meta = {
        "analysis_method": baseline_samples[0].get("analysis_method") if baseline_samples else "DRY_COMBUSTION",
        "max_depth_cm": max((s.get("depth_lower_cm", 30.0) for s in baseline_samples), default=30.0),
    }
    m_meta = {
        "analysis_method": monitoring_samples[0].get("analysis_method") if monitoring_samples else "DRY_COMBUSTION",
        "max_depth_cm": max((s.get("depth_lower_cm", 30.0) for s in monitoring_samples), default=30.0),
        "walkley_black_calibration_factor": monitoring_campaign.get("walkley_black_calibration_factor"),
    }

    consistency, notes = evaluate_method_consistency(b_meta, m_meta)
    is_eligible = (
        len(baseline_samples) > 0
        and len(monitoring_samples) > 0
        and consistency in (MethodConsistencyStatus.CONSISTENT, MethodConsistencyStatus.ALLOWED_TRANSITION)
    )

    return BaselineMonitoringPair(
        pair_id=pair_id,
        quantification_unit_id=str(quantification_unit_id),
        stratum_id=str(stratum_id),
        baseline_campaign_id=b_id,
        monitoring_campaign_id=m_id,
        baseline_period_end=str(baseline_campaign.get("end_date") or ""),
        monitoring_period_end=str(monitoring_campaign.get("end_date") or ""),
        baseline_sample_count=len(baseline_samples),
        monitoring_sample_count=len(monitoring_samples),
        measurement_method=b_meta["analysis_method"],
        methodology_route=methodology_route,
        method_consistency=consistency.value,
        is_pairing_eligible=is_eligible,
        reconciliation_notes=notes,
    )
