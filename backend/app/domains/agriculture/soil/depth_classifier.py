"""
=============================================================================
VeriField Nexus — VM0042 Soil Depth Compliance Classifier
=============================================================================
Authoritative enforcement of Verra VM0042 Section 8 & VMD0053 soil sampling depth rules:

1. Ex-Post SOC Quantification Requirement:
   Both QA1 model inputs and QA2 measured SOC values must meet the minimum 30 cm
   sampling-depth requirement (e.g., 0–30 cm continuous surface profile).
   -> EX_POST_QUANTIFICATION_ELIGIBLE

2. Shallow Data (< 30 cm, e.g. 15 cm / 20 cm Indian Soil Health Card):
   MUST NOT satisfy VM0042 project-specific ex-post SOC measurement requirements.
   Data shallower than 30 cm MAY be used for model calibration or validation under
   Quantification Approach 1 (VMD0053) ONLY where:
     Condition 1: Model output represents SOC stock change to at least 30 cm; AND
     Condition 2: The extrapolation method used to reach 30 cm is clearly and
                  transparently documented.
   If both conditions are satisfied:
     -> MODEL_CALIBRATION_ELIGIBLE (if designated for model calibration)
     -> MODEL_VALIDATION_ELIGIBLE (if designated for model validation)
   If either condition is absent:
     -> REFERENCE_ONLY (never silently extrapolated to 30 cm).

3. Stratified Subsurface Layers (e.g., 30–60 cm):
   -> REFERENCE_ONLY

4. Data Integrity Violations (missing coordinates, inverted depth, out-of-bounds SOC%):
   -> NON_COMPLIANT
=============================================================================
"""

from enum import Enum
from typing import Optional, Tuple


class SoilComplianceClassification(str, Enum):
    EX_POST_QUANTIFICATION_ELIGIBLE = "EX_POST_QUANTIFICATION_ELIGIBLE"
    MODEL_CALIBRATION_ELIGIBLE = "MODEL_CALIBRATION_ELIGIBLE"
    MODEL_VALIDATION_ELIGIBLE = "MODEL_VALIDATION_ELIGIBLE"
    REFERENCE_ONLY = "REFERENCE_ONLY"
    NON_COMPLIANT = "NON_COMPLIANT"


def classify_soil_sample_depth(
    depth_upper_cm: float,
    depth_lower_cm: float,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    soc_stock_pct: Optional[float] = None,
    bulk_density_g_cm3: Optional[float] = None,
    lab_method: Optional[str] = None,
    has_lab_accreditation: bool = False,
    is_model_calibration_source: bool = False,
    is_model_validation_source: bool = False,
    model_represents_30cm: bool = False,
    extrapolation_method: Optional[str] = None,
) -> Tuple[SoilComplianceClassification, str]:
    """
    Evaluates a soil sample against VM0042 Section 8 and VMD0053 methodology rules.

    Returns:
        (SoilComplianceClassification, explanation_notes)
    """
    # 1. Basic integrity check
    if depth_upper_cm is None or depth_lower_cm is None:
        return (
            SoilComplianceClassification.NON_COMPLIANT,
            "Sampling depth bounds cannot be null."
        )

    if depth_upper_cm < 0 or depth_lower_cm <= depth_upper_cm:
        return (
            SoilComplianceClassification.NON_COMPLIANT,
            f"Invalid depth interval: [{depth_upper_cm}, {depth_lower_cm}] cm. Lower depth must exceed upper depth."
        )

    if latitude is None or longitude is None:
        return (
            SoilComplianceClassification.NON_COMPLIANT,
            "Spatial coordinates (latitude, longitude) are required for MRV traceability."
        )

    if not (-90.0 <= latitude <= 90.0) or not (-180.0 <= longitude <= 180.0):
        return (
            SoilComplianceClassification.NON_COMPLIANT,
            f"Coordinates out of bounds: ({latitude}, {longitude})."
        )

    if soc_stock_pct is None or soc_stock_pct < 0.0 or soc_stock_pct > 100.0:
        return (
            SoilComplianceClassification.NON_COMPLIANT,
            f"Invalid SOC percentage: {soc_stock_pct}%. Must be between 0.0 and 100.0."
        )

    # 2. Minimum 30 cm depth check for direct ex-post quantification
    if depth_lower_cm >= 30.0 and depth_upper_cm == 0.0:
        notes = (
            f"Sampling interval 0–{depth_lower_cm:.1f} cm meets VM0042 v2.2 minimum 30 cm depth requirement "
            "for direct ex-post soil organic carbon quantification (applicable to QA1 model inputs and QA2 measured values)."
        )
        if bulk_density_g_cm3 is not None and bulk_density_g_cm3 > 0:
            notes += f" Bulk density recorded: {bulk_density_g_cm3:.2f} g/cm³."
        else:
            notes += " Notice: Bulk density measurement required for absolute stock quantification in t C/ha."
        return SoilComplianceClassification.EX_POST_QUANTIFICATION_ELIGIBLE, notes

    # 3. Shallower than 30 cm (e.g. 0-15 cm Indian Soil Health Card or plow layer)
    if depth_lower_cm < 30.0:
        has_valid_extrapolation = bool(extrapolation_method and extrapolation_method.strip())

        # Check VM0042 Section 8 conditions:
        # (1) model output represents SOC stock change to at least 30 cm, AND
        # (2) extrapolation method used to reach 30 cm is clearly and transparently documented.
        if model_represents_30cm and has_valid_extrapolation:
            if is_model_calibration_source:
                return (
                    SoilComplianceClassification.MODEL_CALIBRATION_ELIGIBLE,
                    f"Sampling depth {depth_upper_cm:.1f}–{depth_lower_cm:.1f} cm (e.g. Indian Soil Health Card test) "
                    "is below the VM0042 30 cm ex-post direct quantification threshold, but is accepted for "
                    "biogeochemical model calibration under Quantification Approach 1 (VMD0053): model represents "
                    f"SOC stock change to >= 30 cm and extrapolation method is documented ('{extrapolation_method.strip()}')."
                )
            elif is_model_validation_source:
                return (
                    SoilComplianceClassification.MODEL_VALIDATION_ELIGIBLE,
                    f"Sampling depth {depth_upper_cm:.1f}–{depth_lower_cm:.1f} cm is eligible for model validation "
                    f"under VMD0053 Section 6: model represents SOC stock change to >= 30 cm and extrapolation "
                    f"method is documented ('{extrapolation_method.strip()}')."
                )

        # If conditions are not satisfied or sample was not designated for calibration/validation:
        reasons = []
        if not model_represents_30cm:
            reasons.append("model does not represent SOC stock change to >= 30 cm")
        if not has_valid_extrapolation:
            reasons.append("extrapolation method to 30 cm is not documented")

        reason_str = "; ".join(reasons) if reasons else "not designated for model calibration/validation"
        return (
            SoilComplianceClassification.REFERENCE_ONLY,
            f"Sampling depth {depth_upper_cm:.1f}–{depth_lower_cm:.1f} cm (e.g. Indian Soil Health Card at 15/20 cm) "
            f"does not meet the VM0042 v2.2 minimum 30 cm depth requirement for ex-post carbon crediting. "
            f"Cannot be used for QA1 model calibration/validation because {reason_str}. "
            "Data preserved as contextual reference and baseline fertility indicator without silent extrapolation."
        )

    # 4. Stratified subsurface layers (e.g. 30–60 cm)
    return (
        SoilComplianceClassification.REFERENCE_ONLY,
        f"Subsurface layer {depth_upper_cm:.1f}–{depth_lower_cm:.1f} cm preserved as reference layer."
    )


def compute_soc_stock_t_c_ha(
    soc_pct: float,
    bulk_density_g_cm3: float,
    depth_thickness_cm: float,
    coarse_fragments_pct: float = 0.0,
) -> float:
    """
    Computes Soil Organic Carbon (SOC) stock in t C/ha:
    Stock (t C/ha) = SOC(%) / 100 * BD(g/cm³) * Depth(cm) * (1 - CoarseFrag/100) * 100
    Simplifies to: SOC(%) * BD * Depth(cm) * (1 - CoarseFrag/100)
    """
    if soc_pct is None or bulk_density_g_cm3 is None or depth_thickness_cm is None:
        return 0.0
    if soc_pct < 0 or bulk_density_g_cm3 <= 0 or depth_thickness_cm <= 0:
        return 0.0

    coarse_factor = max(0.0, 1.0 - (coarse_fragments_pct / 100.0))
    stock_t_c_ha = soc_pct * bulk_density_g_cm3 * depth_thickness_cm * coarse_factor
    return round(stock_t_c_ha, 3)
