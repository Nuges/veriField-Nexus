"""
=============================================================================
VeriField Nexus — Soil Organic Carbon (SOC) Rules & VT0014 DSM Tests
=============================================================================
Tests:
1. VM0042 Minimum 30 cm depth rule:
   - 0-30 cm: EX_POST_QUANTIFICATION_ELIGIBLE
   - 0-15 cm (Indian Soil Health Card / standard plow layer):
     * REFERENCE_ONLY by default (barred from ex-post quantification)
     * MODEL_CALIBRATION_ELIGIBLE when flagged for biogeochemical calibration (VMD0053 QA1)
     * MODEL_VALIDATION_ELIGIBLE when flagged for validation
   - Inverted depth or missing coordinates: NON_COMPLIANT
2. SOC stock calculation formula:
   - Stock (t C/ha) = SOC% * BD * depth_thickness_cm * (1 - coarse_frag/100)
3. VT0014 Digital Soil Mapping Engine:
   - Statistical regression with environmental covariates (NDVI, elevation, slope)
   - Cross-validation metrics (R², RMSE, MAE)
   - MANDATORY INVARIANT: Explicit spatial uncertainty raster summary
     (A prediction product is incomplete without its uncertainty companion).
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
    # Compliant 0-30 cm sample with coordinates and bulk density
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


def test_soil_sample_depth_classification_15cm_nuanced_rules():
    # 0-15 cm Indian Soil Health Card data (reference by default)
    cls_ref, notes_ref = classify_soil_sample_depth(
        depth_upper_cm=0.0,
        depth_lower_cm=15.0,
        latitude=28.6139,
        longitude=77.2090,
        soc_stock_pct=0.95,
        bulk_density_g_cm3=1.40,
    )
    assert cls_ref == SoilComplianceClassification.REFERENCE_ONLY
    assert "does not meet VM0042 v2.2 minimum 30 cm depth requirement" in notes_ref

    # 0-15 cm used for biogeochemical model calibration (VMD0053 QA1)
    cls_cal, notes_cal = classify_soil_sample_depth(
        depth_upper_cm=0.0,
        depth_lower_cm=15.0,
        latitude=28.6139,
        longitude=77.2090,
        soc_stock_pct=0.95,
        bulk_density_g_cm3=1.40,
        is_model_calibration_source=True,
    )
    assert cls_cal == SoilComplianceClassification.MODEL_CALIBRATION_ELIGIBLE
    assert "accepted for biogeochemical model calibration" in notes_cal

    # 0-15 cm used for model validation
    cls_val, notes_val = classify_soil_sample_depth(
        depth_upper_cm=0.0,
        depth_lower_cm=15.0,
        latitude=28.6139,
        longitude=77.2090,
        soc_stock_pct=0.95,
        bulk_density_g_cm3=1.40,
        is_model_validation_source=True,
    )
    assert cls_val == SoilComplianceClassification.MODEL_VALIDATION_ELIGIBLE


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
    # Synthetic calibration ground points
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

    res = VT0014SoilMappingEngine.run_mapping(
        sample_points=sample_points,
        covariate_features=["ndvi", "elevation", "slope"],
        prediction_grid_coords=prediction_grid,
    )

    assert res["status"] == "COMPLETED"
    assert res["model_name"] == "VT0014_DIGITAL_SOIL_MAPPING"
    assert res["version"] == "1.0"

    # Performance metrics
    assert "r2" in res["performance_metrics"]
    assert "rmse" in res["performance_metrics"]

    # Invariant: Explicit spatial uncertainty MUST be quantified
    assert res["spatial_uncertainty"]["is_uncertainty_quantified"] is True
    assert res["spatial_uncertainty"]["mean_standard_error_t_c_ha"] > 0
    assert res["spatial_uncertainty"]["relative_uncertainty_pct"] > 0
    assert res["spatial_uncertainty"]["confidence_level"] == "90%"

    # Provenance
    assert len(res["provenance_hash"]) == 64
