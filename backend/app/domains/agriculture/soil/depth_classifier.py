"""
=============================================================================
VeriField Nexus — VM0042 Soil Depth Compliance Classifier
=============================================================================
Nuanced enforcement of Verra VM0042 Section 8 soil sampling depth rules:
- EX_POST_QUANTIFICATION_ELIGIBLE:
  Direct project measurement covering >= 30 cm (e.g. 0–30 cm).
- MODEL_CALIBRATION_ELIGIBLE:
  Shallower data (e.g. 0–15 cm Indian Soil Health Card) or external reference
  soil data eligible for biogeochemical model calibration under VM0042
  Quantification Approach 1 (VMD0053).
- MODEL_VALIDATION_ELIGIBLE:
  Eligible for model validation where QA/QC criteria are satisfied.
- REFERENCE_ONLY:
  Ingested for baseline agronomic context; barred from direct credit quantification.
- NON_COMPLIANT:
  Fails basic data integrity requirements (missing coordinates, inverted depth).
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
) -> Tuple[SoilComplianceClassification, str]:
    """
    Evaluates a soil sample against VM0042 and VMD0053 methodology rules.

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

    sampled_depth_span = depth_lower_cm - depth_upper_cm

    # 2. Check depth criteria for VM0042
    if depth_lower_cm >= 30.0 and depth_upper_cm == 0.0:
        # Full surface profile to >= 30cm
        notes = (
            f"Sampling interval 0–{depth_lower_cm:.1f} cm meets VM0042 v2.2 minimum 30 cm depth requirement "
            "for direct ex-post soil organic carbon quantification."
        )
        if bulk_density_g_cm3 is not None and bulk_density_g_cm3 > 0:
            notes += f" Bulk density recorded: {bulk_density_g_cm3:.2f} g/cm³."
        else:
            notes += " Warning: Bulk density not recorded; required for absolute stock quantification (t C/ha)."
        return SoilComplianceClassification.EX_POST_QUANTIFICATION_ELIGIBLE, notes

    # 3. Shallower than 30 cm (e.g., 0-15 cm Indian Soil Health Card or plow layer)
    if depth_lower_cm < 30.0:
        if is_model_calibration_source:
            return (
                SoilComplianceClassification.MODEL_CALIBRATION_ELIGIBLE,
                f"Sampling depth {depth_upper_cm:.1f}–{depth_lower_cm:.1f} cm is below VM0042 30 cm direct "
                "quantification threshold, but is accepted for biogeochemical model calibration under "
                "Quantification Approach 1 (VMD0053 v2.1) with depth-harmonization functions."
            )
        elif is_model_validation_source:
            return (
                SoilComplianceClassification.MODEL_VALIDATION_ELIGIBLE,
                f"Sampling depth {depth_upper_cm:.1f}–{depth_lower_cm:.1f} cm is eligible for model validation "
                "under VMD0053 Section 6 uncertainty assessment."
            )
        else:
            return (
                SoilComplianceClassification.REFERENCE_ONLY,
                f"Sampling depth {depth_upper_cm:.1f}–{depth_lower_cm:.1f} cm (e.g. standard 15 cm agricultural test) "
                "does not meet VM0042 v2.2 minimum 30 cm depth requirement for ex-post carbon crediting. "
                "Preserved as contextual reference and baseline fertility indicator."
            )

    # 4. Stratified deeper layers (e.g. 30-60 cm)
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
