"""
VeriField Nexus — Agriculture Soil Engine Package
"""

from app.domains.agriculture.soil.depth_classifier import (
    SoilComplianceClassification,
    classify_soil_sample_depth,
    compute_soc_stock_t_c_ha,
)
from app.domains.agriculture.soil.digital_soil_mapping import VT0014SoilMappingEngine
from app.domains.agriculture.soil.soc_stock_calculator import (
    LayerInput,
    LayerResult,
    ProfileESMResult,
    SOCStockCalculationError,
    calculate_layer_soil_mass,
    calculate_layer_soc_mass,
    calculate_profile_esm_proportioning,
    calculate_profile_esm_spline,
    aggregate_stratum_soc_stock,
    aggregate_project_area_weighted_soc_stock,
)

__all__ = [
    "SoilComplianceClassification",
    "classify_soil_sample_depth",
    "compute_soc_stock_t_c_ha",
    "VT0014SoilMappingEngine",
    "LayerInput",
    "LayerResult",
    "ProfileESMResult",
    "SOCStockCalculationError",
    "calculate_layer_soil_mass",
    "calculate_layer_soc_mass",
    "calculate_profile_esm_proportioning",
    "calculate_profile_esm_spline",
    "aggregate_stratum_soc_stock",
    "aggregate_project_area_weighted_soc_stock",
]
