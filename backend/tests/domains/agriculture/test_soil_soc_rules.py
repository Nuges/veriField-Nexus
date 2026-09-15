"""
=============================================================================
VeriField Nexus — Soil Organic Carbon (SOC) Rules & VT0014 DSM Tests
=============================================================================
Authoritative Tests:
1. VM0042 Minimum 30 cm depth rule:
   - 0–30 cm: EX_POST_QUANTIFICATION_ELIGIBLE (QA1 model inputs and QA2 measured values).
   - 0–15 cm / 0–20 cm (Indian Soil Health Card / standard plow layer):
     * REFERENCE_ONLY by default.
     * SHALL NOT qualify for ex-post carbon quantification.
     * SHALL NOT qualify for calibration/validation unless BOTH official conditions are met:
       (1) model output represents SOC stock change to at least 30 cm, AND
       (2) extrapolation method used to reach 30 cm is clearly and transparently documented.
     * NO invented conditions (e.g. bulk density + dry combustion alone does NOT grant eligibility).
     * Never silently extrapolate shallow data.
2. SOC stock calculation formula:
   - Stock (t C/ha) = SOC% * BD * depth_thickness_cm * (1 - coarse_frag/100)
3. VT0014 Digital Soil Mapping Engine:
   - Typed performance metrics (ModelPerformanceMetrics: R², RMSE, MAE).
   - Methodology-configured validation criteria (stratum densification triggered ONLY by configured criteria).
   - Explicit spatial uncertainty quantification (confidence level, SE, relative uncertainty %).
   - Mandatory Corrections and Clarifications effective 16 October 2025 applied.
=============================================================================
"""

import pytest

from app.domains.agriculture.soil.depth_classifier import (
    SoilComplianceClassification,
    classify_soil_sample_depth,
    compute_soc_stock_t_c_ha,
)
from app.domains.agriculture.soil.digital_soil_mapping import (
    VT0014SoilMappingEngine,
)


def test_soil_sample_depth_classification_vm0042_compliant():
    """Compliant 0–30 cm continuous surface profile meets ex-post direct quantification."""
    classification, notes = classify_soil_sample_depth(
        depth_upper_cm=0.0,
        depth_lower_cm=30.0,
        latitude=28.6139,
        longitude=77.2090,
        soc_stock_pct=1.45,
        bulk_density_g_cm3=1.32,
    )
    assert classification == SoilComplianceClassification.EX_POST_QUANTIFICATION_ELIGIBLE
    assert "minimum 30 cm depth requirement" in notes


def test_indian_soil_health_card_15cm_cannot_satisfy_ex_post_quantification():
    """Indian Soil Health Card at 15 cm MUST NOT satisfy ex-post quantification requirements."""
    classification, notes = classify_soil_sample_depth(
        depth_upper_cm=0.0,
        depth_lower_cm=15.0,
        latitude=28.6139,
        longitude=77.2090,
        soc_stock_pct=0.95,
        bulk_density_g_cm3=1.40,
        lab_method="DRY_COMBUSTION",
        has_lab_accreditation=True,
    )
    # Even with dry combustion and accredited lab, 15 cm CANNOT be ex-post quantification eligible
    assert classification != SoilComplianceClassification.EX_POST_QUANTIFICATION_ELIGIBLE
    assert classification == SoilComplianceClassification.REFERENCE_ONLY
    assert "does not meet the VM0042 v2.2 minimum 30 cm depth requirement" in notes
    assert "without silent extrapolation" in notes


def test_shallow_data_calibration_requires_both_vm0042_conditions():
    """
    Data shallower than 30 cm MAY be used for model calibration under QA1 (VMD0053) ONLY where:
    1. model output represents SOC stock change to at least 30 cm; AND
    2. extrapolation method used to reach 30 cm is clearly and transparently documented.
    """
    # Case A: Calibration requested, but extrapolation NOT documented -> REFERENCE_ONLY
    cls_no_extrap, notes_a = classify_soil_sample_depth(
        depth_upper_cm=0.0,
        depth_lower_cm=15.0,
        latitude=28.6139,
        longitude=77.2090,
        soc_stock_pct=0.95,
        is_model_calibration_source=True,
        model_represents_30cm=True,
        extrapolation_method=None,  # Missing!
    )
    assert cls_no_extrap == SoilComplianceClassification.REFERENCE_ONLY
    assert "extrapolation method to 30 cm is not documented" in notes_a

    # Case B: Calibration requested, but model does NOT represent change to >= 30 cm -> REFERENCE_ONLY
    cls_no_model30, notes_b = classify_soil_sample_depth(
        depth_upper_cm=0.0,
        depth_lower_cm=15.0,
        latitude=28.6139,
        longitude=77.2090,
        soc_stock_pct=0.95,
        is_model_calibration_source=True,
        model_represents_30cm=False,  # Fails condition 1!
        extrapolation_method="Equal-area quadratic spline model",
    )
    assert cls_no_model30 == SoilComplianceClassification.REFERENCE_ONLY
    assert "model does not represent SOC stock change to >= 30 cm" in notes_b

    # Case C: BOTH conditions satisfied -> MODEL_CALIBRATION_ELIGIBLE
    cls_cal_valid, notes_c = classify_soil_sample_depth(
        depth_upper_cm=0.0,
        depth_lower_cm=15.0,
        latitude=28.6139,
        longitude=77.2090,
        soc_stock_pct=0.95,
        is_model_calibration_source=True,
        model_represents_30cm=True,
        extrapolation_method="Equal-area quadratic spline with bulk density profile weighting (VMD0053 Section 5)",
    )
    assert cls_cal_valid == SoilComplianceClassification.MODEL_CALIBRATION_ELIGIBLE
    assert "accepted for biogeochemical model calibration" in notes_c

    # Case D: Validation source with BOTH conditions satisfied -> MODEL_VALIDATION_ELIGIBLE
    cls_val_valid, notes_d = classify_soil_sample_depth(
        depth_upper_cm=0.0,
        depth_lower_cm=15.0,
        latitude=28.6139,
        longitude=77.2090,
        soc_stock_pct=0.95,
        is_model_validation_source=True,
        model_represents_30cm=True,
        extrapolation_method="Pedotransfer spline function calibrated across regional soil survey",
    )
    assert cls_val_valid == SoilComplianceClassification.MODEL_VALIDATION_ELIGIBLE
    assert "eligible for model validation" in notes_d


def test_soil_sample_invalid_non_compliant():
    # Inverted depths
    cls_inv, _ = classify_soil_sample_depth(depth_upper_cm=30.0, depth_lower_cm=10.0, latitude=20.0, longitude=75.0, soc_stock_pct=1.0)
    assert cls_inv == SoilComplianceClassification.NON_COMPLIANT

    # Missing coordinates
    cls_nocoord, _ = classify_soil_sample_depth(depth_upper_cm=0.0, depth_lower_cm=30.0, latitude=None, longitude=None, soc_stock_pct=1.0)
    assert cls_nocoord == SoilComplianceClassification.NON_COMPLIANT

    # Invalid SOC %
    cls_bad_soc, _ = classify_soil_sample_depth(depth_upper_cm=0.0, depth_lower_cm=30.0, latitude=20.0, longitude=75.0, soc_stock_pct=-5.0)
    assert cls_bad_soc == SoilComplianceClassification.NON_COMPLIANT


def test_soc_stock_calculation_formula():
    # 1.5% SOC, 1.3 g/cm3 BD, 30 cm depth, 10% coarse fragments
    # Expected: 1.5 * 1.3 * 30 * (1 - 0.10) = 52.65 t C/ha
    stock = compute_soc_stock_t_c_ha(
        soc_pct=1.5,
        bulk_density_g_cm3=1.3,
        depth_thickness_cm=30.0,
        coarse_fragments_pct=10.0,
    )
    assert stock == 52.65


def test_vt0014_digital_soil_mapping_and_spatial_uncertainty():
    sample_points = [
        {"lat": 28.50, "lon": 77.10, "soc_stock_t_c_ha": 38.5, "covariates": {"ndvi": 0.65, "elevation": 215.0, "slope": 2.1}},
        {"lat": 28.52, "lon": 77.12, "soc_stock_t_c_ha": 44.2, "covariates": {"ndvi": 0.78, "elevation": 208.0, "slope": 1.5}},
        {"lat": 28.54, "lon": 77.14, "soc_stock_t_c_ha": 29.8, "covariates": {"ndvi": 0.42, "elevation": 230.0, "slope": 4.2}},
        {"lat": 28.56, "lon": 77.16, "soc_stock_t_c_ha": 33.1, "covariates": {"ndvi": 0.55, "elevation": 222.0, "slope": 3.0}},
        {"lat": 28.58, "lon": 77.18, "soc_stock_t_c_ha": 40.7, "covariates": {"ndvi": 0.72, "elevation": 211.0, "slope": 1.8}},
    ]

    prediction_grid = [
        {"covariates": {"ndvi": 0.68, "elevation": 214.0, "slope": 2.0}},
        {"covariates": {"ndvi": 0.50, "elevation": 225.0, "slope": 3.5}},
    ]

    # Test with configurable validation criteria and 90% confidence level
    res = VT0014SoilMappingEngine.run_mapping(
        sample_points=sample_points,
        covariate_features=["ndvi", "elevation", "slope"],
        prediction_grid_coords=prediction_grid,
        validation_criteria={
            "min_r2": 0.30,
            "max_relative_uncertainty_pct": 25.0,
            "require_densification_on_uncertainty": True,
        },
        uncertainty_config={"confidence_level": "90%"},
    )

    assert res["status"] == "COMPLETED"
    assert res["model_name"] == "VT0014_DIGITAL_SOIL_MAPPING"
    assert res["version"] == "1.0"
    assert any("16 October 2025" in c for c in res["corrections_applied"])

    # Typed performance metrics
    metrics = res["performance_metrics"]
    assert "r2" in metrics
    assert "rmse" in metrics
    assert "sample_count" in metrics
    assert metrics["validation_status"] in ["PASS", "FLAGGED", "EVALUATED"]

    # Invariant: Explicit spatial uncertainty MUST be quantified
    assert res["spatial_uncertainty"]["is_uncertainty_quantified"] is True
    assert res["spatial_uncertainty"]["mean_standard_error_t_c_ha"] > 0
    assert res["spatial_uncertainty"]["relative_uncertainty_pct"] > 0
    assert res["spatial_uncertainty"]["confidence_level"] == "90%"

    # Provenance hash
    assert len(res["provenance_hash"]) == 64
