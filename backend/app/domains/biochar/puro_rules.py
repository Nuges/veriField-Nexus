import math
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from app.domains.biochar.puro_models import (
        PuroEndUseCategory,
        PuroMethodologyVersion,
        PuroNormativeDependency,
        PuroRuleDefinition,
    )

# ---------------------------------------------------------------------------
# Puro.earth Biochar Edition 2025 V2 — Official Constants & Matrix Lookups
# Approved 27 November 2025
# ---------------------------------------------------------------------------

# Molar H/Corg Carbonization Degree Threshold (Rule 3.5.1)
# Must be strictly below 0.70 to be eligible for certification and crediting.
MAX_ELIGIBLE_MOLAR_H_C = 0.70

# Stoichiometric Conversion: Carbon (C) -> CO2
# 44/12 = 3.666667 (molecular weight ratio of CO2 to C)
CARBON_TO_CO2_FACTOR = Decimal("44") / Decimal("12")

# ---------------------------------------------------------------------------
# Official Table 6.1 Regression Parameters (Edition 2025 V2)
# Formula (Equation 6.4): PF (%) = M - a * (H/Corg)
# Valid for integer soil temperatures Ts from 7°C to 40°C.
# ---------------------------------------------------------------------------
PURO_TABLE_6_1_REGRESSION_PARAMETERS: Dict[int, Tuple[float, float]] = {
    7: (96.59, 11.28),
    8: (95.98, 13.44),
    9: (95.36, 15.66),
    10: (94.73, 17.92),
    11: (94.10, 20.15),
    12: (93.50, 22.31),
    13: (92.92, 24.38),
    14: (92.38, 26.33),
    15: (91.87, 28.16),
    16: (91.40, 29.84),
    17: (90.96, 31.39),
    18: (90.57, 32.81),
    19: (90.20, 34.11),
    20: (89.87, 35.29),
    21: (89.57, 36.36),
    22: (89.29, 37.35),
    23: (89.03, 38.26),
    24: (88.79, 39.09),
    25: (88.57, 39.87),
    26: (88.37, 40.59),
    27: (88.18, 41.27),
    28: (87.99, 41.91),
    29: (87.82, 42.52),
    30: (87.66, 43.10),
    31: (87.50, 43.67),
    32: (87.34, 44.21),
    33: (87.19, 44.74),
    34: (87.04, 45.26),
    35: (86.90, 45.77),
    36: (86.75, 46.27),
    37: (86.61, 46.77),
    38: (86.47, 47.27),
    39: (86.33, 47.76),
    40: (86.19, 48.25),
}

# ---------------------------------------------------------------------------
# Official Table 8.3 iLUC Factors (Edition 2025 V2)
# Units: kg CO2e per MJ
# ---------------------------------------------------------------------------
PURO_TABLE_8_3_ILUC_FACTORS: Dict[str, float] = {
    "CEREALS_AND_STARCH_CROPS": 0.012,  # kg CO2e / MJ
    "SUGAR_CROPS": 0.013,               # kg CO2e / MJ
    "OIL_CROPS": 0.055,                 # kg CO2e / MJ
}


def resolve_puro_soil_temperature(raw_temp_celsius: Optional[float]) -> Tuple[Optional[int], Dict[str, Any]]:
    """
    Resolves soil temperature per Rule 6.2.4:
    - Derived from (Lembrechts et al., 2022) SBIO1_Annual_Mean_Temperature_5_15cm.
    - Based on sub-national region of first use.
    - Minimum soil temperature conservatively set to 7°C.
    - Temperature data rounded to closest upper integer value (math.ceil).
    - Table 6.1 supported range: 7°C to 40°C (integer).
    - If the resolved integer temperature exceeds 40°C, the temperature is OUTSIDE
      the supported domain and quantification MUST NOT proceed. No silent clamping.

    Returns:
        Tuple of (effective_temp_or_None, provenance_dict).
        When the temperature is outside the supported range, effective_temp is None
        and provenance contains 'status': 'SOIL_TEMPERATURE_OUTSIDE_SUPPORTED_RANGE'.
    """
    if raw_temp_celsius is None:
        raw_val = 15.0
    else:
        raw_val = float(raw_temp_celsius)

    # Floor at 7°C (Rule 6.2.4: "The minimum soil temperature is conservatively set to 7°C")
    clamped_lower = max(7.0, raw_val)
    # Round to closest upper integer
    rounded_int = int(math.ceil(clamped_lower))

    # Fail closed if rounded temperature exceeds Table 6.1 supported range (7–40°C).
    # No silent clamping: the methodology does NOT authorize extrapolation beyond 40°C.
    if rounded_int > 40:
        provenance = {
            "raw_value_celsius": raw_val,
            "effective_integer_celsius": None,
            "clamped_to_minimum_7c": raw_val < 7.0,
            "rounded_upper_integer": rounded_int,
            "status": "SOIL_TEMPERATURE_OUTSIDE_SUPPORTED_RANGE",
            "dataset_reference": "Lembrechts et al., 2022 (SBIO1_Annual_Mean_Temperature_5_15cm)",
            "methodology_rule": "PURO-BIOCHAR-6.2.4",
            "notes": f"Resolved soil temperature {rounded_int}°C exceeds Table 6.1 maximum (40°C). "
                     "No official instruction authorizes extrapolation beyond the supported range. "
                     "Quantification cannot proceed — manual review required.",
        }
        return None, provenance

    effective_int = max(7, rounded_int)

    provenance = {
        "raw_value_celsius": raw_val,
        "effective_integer_celsius": effective_int,
        "clamped_to_minimum_7c": raw_val < 7.0,
        "rounded_upper_integer": rounded_int,
        "dataset_reference": "Lembrechts et al., 2022 (SBIO1_Annual_Mean_Temperature_5_15cm)",
        "methodology_rule": "PURO-BIOCHAR-6.2.4",
    }
    return effective_int, provenance


def calculate_puro_persistence_fraction(
    molar_h_c: float,
    soil_temp_celsius: Optional[float],
) -> Dict[str, Any]:
    """
    Computes official Edition 2025 V2 Persistence Fraction PF (%) per Equation 6.4:
    PF = M - a * (H/Corg)
    
    Invariants:
    - Rule 3.5.1: Molar H/Corg must be strictly < 0.70. H/Corg >= 0.70 fails eligibility.
    - Rule 6.2.4 Remark: Non-soil applications use the exact same soil decay model (Eq. 6.4)
      and region of first use soil temperature.
    - Returns exact Table 6.1 regression parameters M and a.
    - Durability class is CORC200+ for all eligible biochars (extrapolated over 200 years).
    """
    if molar_h_c is None or molar_h_c <= 0.0:
        return {
            "status": "FAIL_CLOSED",
            "is_eligible": False,
            "persistence_fraction_pf": 0.0,
            "loss_fraction": 1.0,
            "durability_class": "INELIGIBLE",
            "regression_m": 0.0,
            "regression_a": 0.0,
            "effective_soil_temp_celsius": 0,
            "notes": "Molar H/Corg ratio is missing or non-positive; cannot evaluate carbonization.",
        }

    # Rule 3.5.1: strictly below 0.70
    if molar_h_c >= MAX_ELIGIBLE_MOLAR_H_C:
        return {
            "status": "FAIL_CLOSED",
            "is_eligible": False,
            "persistence_fraction_pf": 0.0,
            "loss_fraction": 1.0,
            "durability_class": "INELIGIBLE",
            "regression_m": 0.0,
            "regression_a": 0.0,
            "effective_soil_temp_celsius": 0,
            "notes": f"Molar H/Corg {molar_h_c:.4f} exceeds threshold ({MAX_ELIGIBLE_MOLAR_H_C}). Fails minimum carbonization (Rule 3.5.1).",
        }

    effective_temp, temp_prov = resolve_puro_soil_temperature(soil_temp_celsius)

    # Fail closed if soil temperature is outside the supported Table 6.1 range
    if effective_temp is None:
        return {
            "status": "SOIL_TEMPERATURE_OUTSIDE_SUPPORTED_RANGE",
            "is_eligible": False,
            "persistence_fraction_pf": 0.0,
            "loss_fraction": 1.0,
            "durability_class": "MANUAL_REVIEW_REQUIRED",
            "regression_m": 0.0,
            "regression_a": 0.0,
            "effective_soil_temp_celsius": None,
            "temperature_provenance": temp_prov,
            "notes": temp_prov.get("notes", "Soil temperature outside supported range (7–40°C)."),
            "rules": ["PURO-BIOCHAR-6.2.4"],
        }

    m, a = PURO_TABLE_6_1_REGRESSION_PARAMETERS[effective_temp]

    # Equation 6.4: PF = M - a * (H/Corg)
    pf_pct = m - (a * molar_h_c)
    # Clamp PF between 0.0% and 100.0%
    pf_pct = max(0.0, min(100.0, pf_pct))
    loss_fraction = (100.0 - pf_pct) / 100.0

    return {
        "status": "SUCCESS",
        "is_eligible": True,
        "persistence_fraction_pf": round(pf_pct, 4),
        "loss_fraction": round(loss_fraction, 6),
        "durability_class": "CORC200+",
        "regression_m": m,
        "regression_a": a,
        "effective_soil_temp_celsius": effective_temp,
        "temperature_provenance": temp_prov,
        "equation": f"PF = {m:.2f} - {a:.2f} * {molar_h_c:.4f} = {pf_pct:.4f}%",
        "rules": ["PURO-BIOCHAR-3.5.1", "PURO-BIOCHAR-6.2.2", "PURO-BIOCHAR-6.2.4"],
        "notes": f"PF quantified under Edition 2025 V2 Table 6.1 (Ts={effective_temp}°C, M={m}, a={a}) -> PF={pf_pct:.3f}%.",
    }


def get_puro_persistence_factor(
    molar_h_c: float,
    soil_temp_celsius: float,
    is_non_soil_durable: bool = False,
) -> Tuple[float, str]:
    """
    Backward-compatible helper returning (F_persistence, durability_class).
    Uses the official continuous Equation 6.4 decay model.
    Non-soil uses the same soil decay model per Rule 6.2.4 remark.
    """
    res = calculate_puro_persistence_fraction(molar_h_c, soil_temp_celsius)
    if not res["is_eligible"]:
        return 0.0, "INELIGIBLE"
    # Convert percentage (0-100) to factor (0.0-1.0)
    factor = res["persistence_fraction_pf"] / 100.0
    return factor, res["durability_class"]


# ---------------------------------------------------------------------------
# Official Table 3.2 End-Use Categories (Puro Biochar Edition 2025 V2)
# Exactly 28 categories across 7 sectors
# ---------------------------------------------------------------------------
TABLE_3_2_CATEGORIES: List[Dict[str, Any]] = [
    {
        "category_code": "AF1",
        "category_name": "Soil amendment, applied pure and incorporated into topsoil (arable, grassland, forest land)",
        "sector": "Agriculture & Forestry",
        "product_type": "Soil amendment / improver",
        "pure_or_mixed": "PURE",
        "application_type": "FINAL",
        "is_corc_eligible": True,
        "min_environmental_quality": "WBC Agro",
        "default_durability_years": 200,
        "persistence_factor_non_soil": None,
        "reversal_rules": "Diversion risks proof as per rule 3.6.5. In-soil fire deemed not a threat.",
        "cascading_conditions": "Not applicable (direct final application).",
        "reversal_discount_factor_required": False,
        "required_evidence_types": ["DELIVERY_NOTE", "APPLICATION_ATTESTATION", "GPS_COORDINATES", "GEOTAGGED_PHOTOS"],
        "rule_references": ["PURO-BIOCHAR-3.2", "PURO-BIOCHAR-3.6.5"],
    },
    {
        "category_code": "AF2",
        "category_name": "Soil amendment, mixed with other amendments (compost, manure, fertilizers) prior to application",
        "sector": "Agriculture & Forestry",
        "product_type": "Soil amendment / blend",
        "pure_or_mixed": "MIXED",
        "application_type": "FINAL",
        "is_corc_eligible": True,
        "min_environmental_quality": "WBC Agro",
        "default_durability_years": 200,
        "persistence_factor_non_soil": None,
        "reversal_rules": "Diversion risks proof as per rule 3.6.5 or 3.6.6. In-soil fire deemed not a threat.",
        "cascading_conditions": "Not applicable (final blended soil application).",
        "reversal_discount_factor_required": False,
        "required_evidence_types": ["DELIVERY_NOTE", "BLENDING_RECORD", "APPLICATION_ATTESTATION", "GPS_COORDINATES"],
        "rule_references": ["PURO-BIOCHAR-3.2", "PURO-BIOCHAR-3.6.5", "PURO-BIOCHAR-3.6.6"],
    },
    {
        "category_code": "AF3",
        "category_name": "Cultivation substrate, pure or mixed (potting soil, growing media, horticulture)",
        "sector": "Agriculture & Forestry",
        "product_type": "Cultivation substrate",
        "pure_or_mixed": "PURE_OR_MIXED",
        "application_type": "CASCADING",
        "is_corc_eligible": True,
        "min_environmental_quality": "WBC Agro",
        "default_durability_years": 200,
        "persistence_factor_non_soil": None,
        "reversal_rules": "Evidence that spent cultivation substrates are discarded/used to preserve carbon (composting/soil amendment, no incineration).",
        "cascading_conditions": "Cascade risks applicable per rule 3.6.7.",
        "reversal_discount_factor_required": False,
        "required_evidence_types": ["DELIVERY_NOTE", "SUBSTRATE_MANAGEMENT_PLAN", "END_OF_LIFE_DISPOSITION"],
        "rule_references": ["PURO-BIOCHAR-3.2", "PURO-BIOCHAR-3.6.7"],
    },
    {
        "category_code": "AF4",
        "category_name": "Planting substrate for tree seedling and sapling production",
        "sector": "Agriculture & Forestry",
        "product_type": "Tree planting substrate",
        "pure_or_mixed": "PURE_OR_MIXED",
        "application_type": "CASCADING",
        "is_corc_eligible": True,
        "min_environmental_quality": "WBC Agro",
        "default_durability_years": 200,
        "persistence_factor_non_soil": None,
        "reversal_rules": "Evidence that unused or spent substrate and failed seedlings are managed to preserve carbon (re-use, composting, soil amendment).",
        "cascading_conditions": "Cascade risks applicable per rule 3.6.7.",
        "reversal_discount_factor_required": False,
        "required_evidence_types": ["DELIVERY_NOTE", "NURSERY_MANAGEMENT_ATTESTATION", "DISPOSITION_RECORD"],
        "rule_references": ["PURO-BIOCHAR-3.2", "PURO-BIOCHAR-3.6.7"],
    },
    {
        "category_code": "AF5",
        "category_name": "Seed coatings for seeds used in agricultural context (arable land)",
        "sector": "Agriculture & Forestry",
        "product_type": "Agricultural seed coating",
        "pure_or_mixed": "MIXED",
        "application_type": "CASCADING",
        "is_corc_eligible": True,
        "min_environmental_quality": "WBC Agro",
        "default_durability_years": 200,
        "persistence_factor_non_soil": None,
        "reversal_rules": "Evidence coated seeds reach arable land. Expired/damaged seeds assumed incinerated unless proven otherwise.",
        "cascading_conditions": "Cascade risks applicable per rule 3.6.7.",
        "reversal_discount_factor_required": False,
        "required_evidence_types": ["SEED_TREATMENT_MANIFEST", "SALES_RECORDS", "FIELD_APPLICATION_PROOF"],
        "rule_references": ["PURO-BIOCHAR-3.2", "PURO-BIOCHAR-3.6.5", "PURO-BIOCHAR-3.6.7"],
    },
    {
        "category_code": "AH1",
        "category_name": "Additive to manure in on-farm storages",
        "sector": "Animal Husbandry",
        "product_type": "Manure management additive",
        "pure_or_mixed": "PURE",
        "application_type": "CASCADING",
        "is_corc_eligible": True,
        "min_environmental_quality": "WBC Agro",
        "default_durability_years": 200,
        "persistence_factor_non_soil": None,
        "reversal_rules": "Evidence that manure is applied to land (direct, compost, or AD digestate) and not incinerated.",
        "cascading_conditions": "Cascade risks applicable per rule 3.6.7.",
        "reversal_discount_factor_required": False,
        "required_evidence_types": ["FARM_DELIVERY_RECEIPT", "MANURE_MANAGEMENT_ATTESTATION", "LAND_APPLICATION_RECORD"],
        "rule_references": ["PURO-BIOCHAR-3.2", "PURO-BIOCHAR-3.6.5", "PURO-BIOCHAR-3.6.7"],
    },
    {
        "category_code": "AH2",
        "category_name": "Additive to animal bedding",
        "sector": "Animal Husbandry",
        "product_type": "Animal bedding additive",
        "pure_or_mixed": "PURE",
        "application_type": "CASCADING",
        "is_corc_eligible": True,
        "min_environmental_quality": "WBC Premium",
        "default_durability_years": 200,
        "persistence_factor_non_soil": None,
        "reversal_rules": "Evidence that spent bedding is applied to land (composted or direct) and not incinerated.",
        "cascading_conditions": "Cascade risks applicable per rule 3.6.7.",
        "reversal_discount_factor_required": False,
        "required_evidence_types": ["FARM_DELIVERY_RECEIPT", "BEDDING_MANAGEMENT_RECORD", "LAND_APPLICATION_PROOF"],
        "rule_references": ["PURO-BIOCHAR-3.2", "PURO-BIOCHAR-3.6.5", "PURO-BIOCHAR-3.6.7"],
    },
    {
        "category_code": "AH3",
        "category_name": "Animal feed additive (at industrial scale; not retail pet feed)",
        "sector": "Animal Husbandry",
        "product_type": "Feed ingredient",
        "pure_or_mixed": "PURE_OR_MIXED",
        "application_type": "CASCADING",
        "is_corc_eligible": True,
        "min_environmental_quality": "WBC Premium",
        "default_durability_years": 200,
        "persistence_factor_non_soil": None,
        "reversal_rules": "Industrial feed tracking; manure subsequently land-applied.",
        "cascading_conditions": "Cascade risks applicable per rule 3.6.7.",
        "reversal_discount_factor_required": False,
        "required_evidence_types": ["FEED_MILL_DELIVERY", "VETERINARY_COMPLIANCE_CERT", "MANURE_FATE_ATTESTATION"],
        "rule_references": ["PURO-BIOCHAR-3.2", "PURO-BIOCHAR-3.6.7"],
    },
    {
        "category_code": "WM1",
        "category_name": "Additive to industrial composting or anaerobic digestion facilities",
        "sector": "Waste Management",
        "product_type": "Composting / AD additive",
        "pure_or_mixed": "PURE",
        "application_type": "CASCADING",
        "is_corc_eligible": True,
        "min_environmental_quality": "WBC Agro",
        "default_durability_years": 200,
        "persistence_factor_non_soil": None,
        "reversal_rules": "Compost or digestate must be land-applied without incineration.",
        "cascading_conditions": "Cascade risks applicable per rule 3.6.7.",
        "reversal_discount_factor_required": False,
        "required_evidence_types": ["FACILITY_DELIVERY_RECORD", "BATCH_PROCESS_LOG", "END_PRODUCT_SALES_RECORD"],
        "rule_references": ["PURO-BIOCHAR-3.2", "PURO-BIOCHAR-3.6.7"],
    },
    {
        "category_code": "WM2",
        "category_name": "Landfill intermediary or final cover material, mixed with soil/constituents",
        "sector": "Waste Management",
        "product_type": "Sanitary landfill cover",
        "pure_or_mixed": "PURE_OR_MIXED",
        "application_type": "FINAL",
        "is_corc_eligible": True,
        "min_environmental_quality": "WBC Material",
        "default_durability_years": 200,
        "persistence_factor_non_soil": None,
        "reversal_rules": "Sanitary landfill SOPs preventing intentional open-burning and minimizing unintentional fires.",
        "cascading_conditions": "Not applicable (final sanitary landfill placement).",
        "reversal_discount_factor_required": False,
        "required_evidence_types": ["LANDFILL_DELIVERY_RECEIPT", "COVER_SOP_COMPLIANCE", "SANITARY_PERMIT"],
        "rule_references": ["PURO-BIOCHAR-3.2", "PURO-BIOCHAR-3.6.5", "PURO-BIOCHAR-3.6.6"],
    },
    {
        "category_code": "EM1",
        "category_name": "Soil additive for remediation of contaminated soils",
        "sector": "Environmental Management",
        "product_type": "Remediation agent",
        "pure_or_mixed": "PURE_OR_MIXED",
        "application_type": "FINAL_OR_CASCADING",
        "is_corc_eligible": True,
        "min_environmental_quality": "WBC Agro",
        "default_durability_years": 200,
        "persistence_factor_non_soil": None,
        "reversal_rules": "Document remediation activity, legality, contaminant type, and subsequent use of remediated soil. In-situ remediation cascade risk low.",
        "cascading_conditions": "Documentation of subsequent remediated soil fate.",
        "reversal_discount_factor_required": False,
        "required_evidence_types": ["REMEDIATION_PLAN", "REGULATORY_AUTHORIZATION", "IN_SITU_CONFIRMATION"],
        "rule_references": ["PURO-BIOCHAR-3.2", "PURO-BIOCHAR-3.6.7"],
    },
    {
        "category_code": "EM2",
        "category_name": "Soil amendment for reclamation of mines and quarries",
        "sector": "Environmental Management",
        "product_type": "Reclamation substrate",
        "pure_or_mixed": "PURE_OR_MIXED",
        "application_type": "FINAL",
        "is_corc_eligible": True,
        "min_environmental_quality": "WBC Agro",
        "default_durability_years": 200,
        "persistence_factor_non_soil": None,
        "reversal_rules": "Legal authorization, max 50% v/v biochar blend, planned fate of reclaimed area.",
        "cascading_conditions": "Not applicable (final mine/quarry reclamation).",
        "reversal_discount_factor_required": False,
        "required_evidence_types": ["MINING_AUTHORITY_PERMIT", "RECLAMATION_LOG", "BLEND_RATIO_VERIFICATION"],
        "rule_references": ["PURO-BIOCHAR-3.2", "PURO-BIOCHAR-3.6.5", "PURO-BIOCHAR-3.6.6"],
    },
    {
        "category_code": "BE1",
        "category_name": "Urban soil, roadbeds or landscaping soil mixes (long-lived soil uses)",
        "sector": "Built Environment",
        "product_type": "Urban soil / landscaping mix",
        "pure_or_mixed": "PURE_OR_MIXED",
        "application_type": "CASCADING",
        "is_corc_eligible": True,
        "min_environmental_quality": "WBC Agro",
        "default_durability_years": 200,
        "persistence_factor_non_soil": None,
        "reversal_rules": "Long-lived soil placement; movement during construction remains in soil masses/landscaping.",
        "cascading_conditions": "Cascade risks deemed low by default.",
        "reversal_discount_factor_required": False,
        "required_evidence_types": ["MUNICIPAL_PROJECT_DELIVERY", "SITE_ENGINEERING_PLAN", "PROOF_OF_USE"],
        "rule_references": ["PURO-BIOCHAR-3.2", "PURO-BIOCHAR-3.6.5", "PURO-BIOCHAR-3.6.6"],
    },
    {
        "category_code": "BE2",
        "category_name": "Planting substrate in temporary/short-lived greenings (green roofs, walls, pots)",
        "sector": "Built Environment",
        "product_type": "Urban planting substrate",
        "pure_or_mixed": "PURE_OR_MIXED",
        "application_type": "CASCADING",
        "is_corc_eligible": True,
        "min_environmental_quality": "WBC Agro",
        "default_durability_years": 200,
        "persistence_factor_non_soil": None,
        "reversal_rules": "Product description, composition, average lifetime, end-of-life management demonstrating low risk.",
        "cascading_conditions": "Cascade risks applicable per rule 3.6.7.",
        "reversal_discount_factor_required": False,
        "required_evidence_types": ["PRODUCT_COMPOSITION_DOC", "END_OF_LIFE_SOP", "SALES_DISTRIBUTION_MANIFEST"],
        "rule_references": ["PURO-BIOCHAR-3.2", "PURO-BIOCHAR-3.6.7"],
    },
    {
        "category_code": "BE3",
        "category_name": "Long-lived construction material (concrete, bricks, cement mortar)",
        "sector": "Built Environment",
        "product_type": "Construction material blend",
        "pure_or_mixed": "MIXED",
        "application_type": "CASCADING",
        "is_corc_eligible": True,
        "min_environmental_quality": "WBC Material",
        "default_durability_years": 200,
        "persistence_factor_non_soil": None,
        "reversal_rules": "Concrete/brick recycling and aggregate demolition reuse do not pose reversal risks.",
        "cascading_conditions": "Cascade risks deemed low by default.",
        "reversal_discount_factor_required": False,
        "required_evidence_types": ["CONCRETE_BATCH_FORMULATION", "MANUFACTURER_DELIVERY", "PROOF_OF_USE"],
        "rule_references": ["PURO-BIOCHAR-3.2", "PURO-BIOCHAR-3.6.5", "PURO-BIOCHAR-3.6.6"],
    },
    {
        "category_code": "BE4",
        "category_name": "Road surfacing materials (biochar-containing asphalt) and assimilated",
        "sector": "Built Environment",
        "product_type": "Asphalt modifier",
        "pure_or_mixed": "MIXED",
        "application_type": "CASCADING",
        "is_corc_eligible": True,
        "min_environmental_quality": "WBC Material",
        "default_durability_years": 200,
        "persistence_factor_non_soil": None,
        "reversal_rules": "End-of-life road surfacing milled/recycled or covered; minimal wearing.",
        "cascading_conditions": "Cascade risks deemed low by default.",
        "reversal_discount_factor_required": False,
        "required_evidence_types": ["ASPHALT_MIX_DESIGN", "ROAD_CONTRACTOR_DELIVERY", "PAVING_RECORD"],
        "rule_references": ["PURO-BIOCHAR-3.2", "PURO-BIOCHAR-3.6.5", "PURO-BIOCHAR-3.6.6"],
    },
    {
        "category_code": "NE1",
        "category_name": "Soil amendment in natural/protected areas, high ecological value, wetlands, peatlands",
        "sector": "Natural Environment",
        "product_type": "Restoration amendment",
        "pure_or_mixed": "PURE_OR_MIXED",
        "application_type": "FINAL",
        "is_corc_eligible": True,
        "min_environmental_quality": "WBC Premium",
        "default_durability_years": 200,
        "persistence_factor_non_soil": None,
        "reversal_rules": "Eligible ONLY if formally authorized by competent environmental authorities as part of restoration project.",
        "cascading_conditions": "Not applicable (final protected area placement).",
        "reversal_discount_factor_required": False,
        "required_evidence_types": ["COMPETENT_AUTHORITY_PERMIT", "RESTORATION_MONITORING_PLAN", "APPLICATION_RECORD"],
        "rule_references": ["PURO-BIOCHAR-3.2", "PURO-BIOCHAR-3.6.5"],
    },
    {
        "category_code": "NE2",
        "category_name": "Addition to water systems (rivers, lakes, sea, oceans)",
        "sector": "Natural Environment",
        "product_type": "Aquatic addition",
        "pure_or_mixed": "PURE_OR_MIXED",
        "application_type": "FINAL",
        "is_corc_eligible": False,
        "min_environmental_quality": "NOT_APPLICABLE",
        "default_durability_years": 0,
        "persistence_factor_non_soil": None,
        "reversal_rules": "NOT ELIGIBLE AND NOT ALLOWED USE under Puro.earth framework due to unknown ecosystem effects.",
        "cascading_conditions": "Ineligible and prohibited use.",
        "reversal_discount_factor_required": False,
        "required_evidence_types": [],
        "rule_references": ["PURO-BIOCHAR-3.2"],
    },
    {
        "category_code": "R1",
        "category_name": "Retail to individuals: Pet feed supplement",
        "sector": "Retail to Individuals",
        "product_type": "Consumer pet supplement",
        "pure_or_mixed": "PURE_OR_MIXED",
        "application_type": "CASCADING",
        "is_corc_eligible": False,
        "min_environmental_quality": "WBC Premium",
        "default_durability_years": 0,
        "persistence_factor_non_soil": None,
        "reversal_rules": "Allowed use but NOT eligible for CORCs due to high risk of solid waste incineration and lack of traceability.",
        "cascading_conditions": "Ineligible for CORC issuance.",
        "reversal_discount_factor_required": False,
        "required_evidence_types": ["RETAIL_FEED_LABEL", "WBC_PREMIUM_CERT"],
        "rule_references": ["PURO-BIOCHAR-3.2"],
    },
    {
        "category_code": "R2",
        "category_name": "Retail to individuals: Consumer products (face masks, toothpaste, etc.)",
        "sector": "Retail to Individuals",
        "product_type": "Consumer cosmetics/goods",
        "pure_or_mixed": "MIXED",
        "application_type": "CASCADING",
        "is_corc_eligible": False,
        "min_environmental_quality": "WBC Premium",
        "default_durability_years": 0,
        "persistence_factor_non_soil": None,
        "reversal_rules": "Allowed use but NOT eligible for CORCs due to short product lifetimes and incineration.",
        "cascading_conditions": "Ineligible for CORC issuance.",
        "reversal_discount_factor_required": False,
        "required_evidence_types": ["CONSUMER_PRODUCT_FORMULATION"],
        "rule_references": ["PURO-BIOCHAR-3.2"],
    },
    {
        "category_code": "R3",
        "category_name": "Retail to individuals: Gardening products sold in store or direct to individuals",
        "sector": "Retail to Individuals",
        "product_type": "Consumer gardening soil",
        "pure_or_mixed": "PURE_OR_MIXED",
        "application_type": "FINAL_OR_CASCADING",
        "is_corc_eligible": True,
        "min_environmental_quality": "WBC Agro",
        "default_durability_years": 200,
        "persistence_factor_non_soil": None,
        "reversal_rules": "Eligible under conditions: formulation <=50% v/v or fine grinding (<10% >20mm) + 30% moisture; signed distributor agreements; country RDF applied to Cstored.",
        "cascading_conditions": "Distribution agreement with last tracked intermediary covering claims and geographical containment.",
        "reversal_discount_factor_required": True,
        "required_evidence_types": ["PACKAGING_LABEL_SPEC", "PARTICLE_MOISTURE_TEST", "DISTRIBUTOR_AGREEMENT", "COUNTRY_RDF_LOOKUP"],
        "rule_references": ["PURO-BIOCHAR-3.2", "PURO-BIOCHAR-3.6.16"],
    },
    {
        "category_code": "R4",
        "category_name": "Retail to individuals: Landscaping products applied by landscaping companies",
        "sector": "Retail to Individuals",
        "product_type": "Professional landscaping mix",
        "pure_or_mixed": "PURE_OR_MIXED",
        "application_type": "FINAL",
        "is_corc_eligible": True,
        "min_environmental_quality": "WBC Agro",
        "default_durability_years": 200,
        "persistence_factor_non_soil": None,
        "reversal_rules": "Traceable via landscaping company performing application on private property.",
        "cascading_conditions": "Not applicable (landscaping contractor final soil incorporation).",
        "reversal_discount_factor_required": False,
        "required_evidence_types": ["LANDSCAPING_WORK_ORDER", "CLIENT_JOB_SHEET", "SOIL_INCORPORATION_PROOF"],
        "rule_references": ["PURO-BIOCHAR-3.2", "PURO-BIOCHAR-3.6.5", "PURO-BIOCHAR-3.6.6"],
    },
    {
        "category_code": "IMF1",
        "category_name": "Filter media for water, wastewater or air",
        "sector": "Industrial Materials or Fuels",
        "product_type": "Filtration media",
        "pure_or_mixed": "PURE",
        "application_type": "CASCADING",
        "is_corc_eligible": True,
        "min_environmental_quality": "WBC Premium",
        "default_durability_years": 200,
        "persistence_factor_non_soil": None,
        "reversal_rules": "Eligible ONLY in rare cases where end-of-life preserves carbon (e.g. nutrient catching in soil). Incineration/reactivation ineligible.",
        "cascading_conditions": "Rigorous proof of end-of-life carbon preservation in soil.",
        "reversal_discount_factor_required": False,
        "required_evidence_types": ["FILTER_INSTALLATION_PROTOCOL", "SPENT_MEDIA_SOIL_INTEGRATION_LOG"],
        "rule_references": ["PURO-BIOCHAR-3.2", "PURO-BIOCHAR-3.6.7"],
    },
    {
        "category_code": "IMF2",
        "category_name": "Component for paints, plastics, composites, batteries, short-lived materials",
        "sector": "Industrial Materials or Fuels",
        "product_type": "Short-lived industrial component",
        "pure_or_mixed": "MIXED",
        "application_type": "CASCADING",
        "is_corc_eligible": False,
        "min_environmental_quality": "WBC Material",
        "default_durability_years": 0,
        "persistence_factor_non_soil": None,
        "reversal_rules": "Allowed use but NOT eligible for CORCs due to incineration/short life.",
        "cascading_conditions": "Ineligible for CORC issuance.",
        "reversal_discount_factor_required": False,
        "required_evidence_types": ["MATERIAL_FORMULATION_RECEIPT"],
        "rule_references": ["PURO-BIOCHAR-3.2"],
    },
    {
        "category_code": "IMF3",
        "category_name": "Fuel for energy production or reductant in industrial processes (e.g. steel)",
        "sector": "Industrial Materials or Fuels",
        "product_type": "Industrial reductant / fuel",
        "pure_or_mixed": "PURE",
        "application_type": "FINAL",
        "is_corc_eligible": False,
        "min_environmental_quality": "Industry Specific",
        "default_durability_years": 0,
        "persistence_factor_non_soil": None,
        "reversal_rules": "Allowed use but NOT eligible for CORCs as carbon storage is not preserved (combustion/reduction).",
        "cascading_conditions": "Ineligible for CORC issuance.",
        "reversal_discount_factor_required": False,
        "required_evidence_types": ["INDUSTRIAL_OFFTAKE_AGREEMENT"],
        "rule_references": ["PURO-BIOCHAR-3.2"],
    },
    {
        "category_code": "GEO1",
        "category_name": "Passive deposits: Injected in non-accessible underground formations",
        "sector": "Passive Deposits",
        "product_type": "Subsurface slurry injection",
        "pure_or_mixed": "PURE",
        "application_type": "FINAL",
        "is_corc_eligible": True,
        "min_environmental_quality": "WBC Material",
        "default_durability_years": 200,
        "persistence_factor_non_soil": None,
        "reversal_rules": "Eligible ONLY if authorized by competent authorities with defined environmental quality and injection site monitoring.",
        "cascading_conditions": "Not applicable (permanent deep geologic injection).",
        "reversal_discount_factor_required": False,
        "required_evidence_types": ["GEOLOGICAL_AUTHORITY_PERMIT", "INJECTION_WELL_LOG", "MONITORING_PROTOCOL"],
        "rule_references": ["PURO-BIOCHAR-3.2", "PURO-BIOCHAR-3.6.5"],
    },
    {
        "category_code": "GEO2",
        "category_name": "Passive deposits: Stored in accessible underground formations without mixing",
        "sector": "Passive Deposits",
        "product_type": "Underground mine storage (unmixed)",
        "pure_or_mixed": "PURE",
        "application_type": "FINAL",
        "is_corc_eligible": False,
        "min_environmental_quality": "Local Competent Authority",
        "default_durability_years": 0,
        "persistence_factor_non_soil": None,
        "reversal_rules": "NOT eligible for CORCs due to risk of future excavation without mineral mixing.",
        "cascading_conditions": "Ineligible for CORC issuance.",
        "reversal_discount_factor_required": False,
        "required_evidence_types": ["MINE_STORAGE_AUTHORIZATION"],
        "rule_references": ["PURO-BIOCHAR-3.2"],
    },
    {
        "category_code": "GEO3",
        "category_name": "Passive deposits: Below-ground burial (pits, trenches, abandoned mines) mixed with minerals/soil",
        "sector": "Passive Deposits",
        "product_type": "Mineral-stabilized burial",
        "pure_or_mixed": "PURE_OR_MIXED",
        "application_type": "FINAL",
        "is_corc_eligible": True,
        "min_environmental_quality": "WBC Agro",
        "default_durability_years": 200,
        "persistence_factor_non_soil": None,
        "reversal_rules": "Eligible only if mixed with minerals/soil ensuring no reversibility and preventing future excavation for combustion.",
        "cascading_conditions": "Not applicable (permanent mineral-stabilized burial).",
        "reversal_discount_factor_required": False,
        "required_evidence_types": ["BURIAL_SITE_PERMIT", "MINERAL_BLENDING_RECORD", "SITE_CLOSURE_REPORT"],
        "rule_references": ["PURO-BIOCHAR-3.2", "PURO-BIOCHAR-3.6.5"],
    },
]

# ---------------------------------------------------------------------------
# Normative External Dependencies
# ---------------------------------------------------------------------------
NORMATIVE_DEPENDENCIES = [
    {
        "code": "PURO_GENERAL_RULES_V4",
        "title": "Puro Standard General Rules v4.0",
        "version": "4.0",
        "document_type": "NORMATIVE_STANDARD",
        "status": "ACTIVE",
        "effective_date": date(2025, 1, 1),
        "source_reference": "https://puro.earth/standards/general-rules/",
        "required_by_rules": ["PURO-BIOCHAR-2.1", "PURO-BIOCHAR-2.2", "PURO-BIOCHAR-11.1"],
        "implementation_state": "DEPENDENCY_REQUIRED",
    },
    {
        "code": "PURO_BIOMASS_SOURCING_CRITERIA_2025",
        "title": "Puro.earth Biomass Sourcing Criteria Edition 2025",
        "version": "2025",
        "document_type": "CRITERIA",
        "status": "ACTIVE",
        "effective_date": date(2025, 1, 1),
        "source_reference": "https://puro.earth/standards/biomass-sourcing-criteria/",
        "required_by_rules": ["PURO-BIOCHAR-3.1", "PURO-BIOCHAR-3.5"],
        "implementation_state": "DEPENDENCY_REQUIRED",
    },
    {
        "code": "PURO_ADDITIONALITY_QUESTIONNAIRE_2025",
        "title": "Puro.earth Baseline and Additionality Assessment Requirements",
        "version": "2025",
        "document_type": "QUESTIONNAIRE",
        "status": "ACTIVE",
        "effective_date": date(2025, 1, 1),
        "source_reference": "https://puro.earth/standards/additionality/",
        "required_by_rules": ["PURO-BIOCHAR-3.3", "PURO-BIOCHAR-3.4"],
        "implementation_state": "DEPENDENCY_REQUIRED",
    },
    {
        "code": "PURO_AUDITOR_REQUIREMENTS_2025",
        "title": "Puro.earth Auditor Requirements and Verification Body Guidelines",
        "version": "2025",
        "document_type": "NORMATIVE_STANDARD",
        "status": "ACTIVE",
        "effective_date": date(2025, 1, 1),
        "source_reference": "https://puro.earth/standards/auditor-requirements/",
        "required_by_rules": ["PURO-BIOCHAR-10.1", "PURO-BIOCHAR-11.1", "PURO-BIOCHAR-11.2"],
        "implementation_state": "DEPENDENCY_REQUIRED",
    },
    {
        "code": "PURO_ARTICLE_6_PROCEDURES",
        "title": "Puro.earth Article 6 & Corresponding Adjustment Procedures",
        "version": "2025",
        "document_type": "PROCEDURE",
        "status": "ACTIVE",
        "effective_date": date(2025, 1, 1),
        "source_reference": "https://puro.earth/standards/article-6/",
        "required_by_rules": ["PURO-BIOCHAR-2.3"],
        "implementation_state": "DEPENDENCY_REQUIRED",
    },
]

# ---------------------------------------------------------------------------
# Full Methodology Rules Catalog (All 11 Chapters)
# ---------------------------------------------------------------------------
METHODOLOGY_RULES_CATALOG = [
    # Chapter 1: Introduction & Scope
    {
        "section_number": 1,
        "section_title": "Introduction, Scope and Activity Boundaries",
        "rule_number": "PURO-BIOCHAR-1.1",
        "rule_title": "Scope of Application and Eligible Carbon Removal Output",
        "applicability_condition": "All Biochar Production and Utilization Projects",
        "requirement_type": "ELIGIBILITY",
        "implementation_handler": "verify_methodology_scope",
        "required_evidence_types": ["PROJECT_DESIGN_DOCUMENT", "METHODOLOGY_DECLARATION"],
        "is_blocking": True,
    },
    # Chapter 2: Supplier, Legal Authority & Claim Rights
    {
        "section_number": 2,
        "section_title": "CO2 Removal Supplier & Exclusive Claim Rights",
        "rule_number": "PURO-BIOCHAR-2.1",
        "rule_title": "Supplier Legal Entity Registration & Recognized Role",
        "applicability_condition": "Mandatory for all project facilities",
        "requirement_type": "ELIGIBILITY",
        "implementation_handler": "verify_supplier_role_and_entity",
        "required_evidence_types": ["SUPPLIER_REGISTRATION_CERTIFICATE", "OPERATIONAL_AGREEMENT"],
        "is_blocking": True,
    },
    {
        "section_number": 2,
        "section_title": "CO2 Removal Supplier & Exclusive Claim Rights",
        "rule_number": "PURO-BIOCHAR-2.2",
        "rule_title": "Exclusive CORC Claim Rights & Double Claiming Prohibition",
        "applicability_condition": "Mandatory before any CORC quantification",
        "requirement_type": "ELIGIBILITY",
        "implementation_handler": "verify_exclusive_claim_rights",
        "required_evidence_types": ["RIGHTS_DECLARATION_DOCUMENT", "SOLE_OWNERSHIP_CONTRACT"],
        "is_blocking": True,
    },
    # Chapter 3: Facility Classification, Baseline, Additionality & Sourcing
    {
        "section_number": 3,
        "section_title": "Production Facility, Baseline, Additionality & Biomass Sourcing",
        "rule_number": "PURO-BIOCHAR-3.1",
        "rule_title": "Stationary vs Mobile Facility Classification and Geographic Containment",
        "applicability_condition": "Mandatory for all production facilities",
        "requirement_type": "ELIGIBILITY",
        "implementation_handler": "verify_facility_classification_and_containment",
        "required_evidence_types": ["FACILITY_PROFILE", "GEOGRAPHIC_BOUNDARY_EVIDENCE"],
        "is_blocking": True,
    },
    {
        "section_number": 3,
        "section_title": "Production Facility, Baseline, Additionality & Biomass Sourcing",
        "rule_number": "PURO-BIOCHAR-3.2",
        "rule_title": "Crediting Period 10-Year Duration & Renewal Audit Constraint",
        "applicability_condition": "Mandatory for project crediting lifecycle",
        "requirement_type": "ELIGIBILITY",
        "implementation_handler": "verify_crediting_period_rules",
        "required_evidence_types": ["CREDITING_PERIOD_REGISTRATION", "AUDIT_RENEWAL_CERTIFICATE"],
        "is_blocking": True,
    },
    {
        "section_number": 3,
        "section_title": "Production Facility, Baseline, Additionality & Biomass Sourcing",
        "rule_number": "PURO-BIOCHAR-3.3",
        "rule_title": "Baseline Scenario Selection (New, Retrofit, Charcoal Repurpose)",
        "applicability_condition": "Mandatory at initial facility audit",
        "requirement_type": "ELIGIBILITY",
        "implementation_handler": "verify_baseline_scenario_and_lock",
        "required_evidence_types": ["HISTORICAL_PRODUCTION_AUDIT", "BASELINE_ASSESSMENT_DOSSIER"],
        "is_blocking": True,
    },
    {
        "section_number": 3,
        "section_title": "Production Facility, Baseline, Additionality & Biomass Sourcing",
        "rule_number": "PURO-BIOCHAR-3.4",
        "rule_title": "Three-Pillar Additionality (Carbon, Regulatory, Financial)",
        "applicability_condition": "Mandatory before project registration",
        "requirement_type": "ELIGIBILITY",
        "implementation_handler": "verify_three_pillar_additionality",
        "required_evidence_types": ["FINANCIAL_ADDITIONALITY_MODEL", "REGULATORY_COMPLIANCE_OPINION"],
        "is_blocking": True,
    },
    {
        "section_number": 3,
        "section_title": "Production Facility, Baseline, Additionality & Biomass Sourcing",
        "rule_number": "PURO-BIOCHAR-3.5",
        "rule_title": "Biomass Sourcing Criteria & Declared Source Validity",
        "applicability_condition": "Mandatory for all received feedstock lots",
        "requirement_type": "ELIGIBILITY",
        "implementation_handler": "verify_biomass_sourcing_compliance",
        "required_evidence_types": ["SOURCING_DECLARATION", "SUSTAINABILITY_CERTIFICATE"],
        "is_blocking": True,
    },
    # Chapter 4: Reversals, Environmental & Social Safeguards
    {
        "section_number": 4,
        "section_title": "Reversal Risks, Environmental & Social Safeguards",
        "rule_number": "PURO-BIOCHAR-4.1",
        "rule_title": "Pre-Issuance and Post-Issuance Reversal Risk Management",
        "applicability_condition": "All batches in storage, transit, or terminal application",
        "requirement_type": "SAFEGUARDS",
        "implementation_handler": "verify_reversal_risk_controls",
        "required_evidence_types": ["REVERSAL_ASSESSMENT", "STORAGE_LOSS_LOG"],
        "is_blocking": True,
    },
    {
        "section_number": 4,
        "section_title": "Reversal Risks, Environmental & Social Safeguards",
        "rule_number": "PURO-BIOCHAR-4.2",
        "rule_title": "Environmental Permits, Local Statutory Compliance & EIA Verification",
        "applicability_condition": "Mandatory for production facility",
        "requirement_type": "SAFEGUARDS",
        "implementation_handler": "verify_environmental_safeguards",
        "required_evidence_types": ["ENVIRONMENTAL_PERMIT", "EMISSIONS_COMPLIANCE_CERTIFICATE"],
        "is_blocking": True,
    },
    # Chapter 5: Quantification Principles & Net CORC Formula
    {
        "section_number": 5,
        "section_title": "CORC Quantification Core Equation",
        "rule_number": "PURO-BIOCHAR-5.1",
        "rule_title": "Deterministic Net CORC Quantification Equation (CORCs = Cstored - Cbaseline - Closs - Eproject - Eleakage)",
        "applicability_condition": "Mandatory calculation for credit issuance",
        "requirement_type": "QUANTIFICATION",
        "implementation_handler": "execute_puro_corc_quantification",
        "required_evidence_types": ["LAB_ANALYSIS", "PRODUCTION_RUN_RECORD", "LOGISTICS_LEDGER"],
        "is_blocking": True,
    },
    # Chapter 6: Stored Carbon, Moisture & Persistence
    {
        "section_number": 6,
        "section_title": "Stored Carbon, Dry Mass & Persistence Modeling",
        "rule_number": "PURO-BIOCHAR-6.1",
        "rule_title": "Eligible Dry Mass Determination and Impurities Adjustment (Equation 6.1)",
        "applicability_condition": "Mandatory for each quantified biochar batch",
        "requirement_type": "QUANTIFICATION",
        "implementation_handler": "calculate_eligible_dry_mass",
        "required_evidence_types": ["MOISTURE_LAB_TEST", "WEIGHBRIDGE_TICKET"],
        "is_blocking": True,
    },
    {
        "section_number": 6,
        "section_title": "Stored Carbon, Dry Mass & Persistence Modeling",
        "rule_number": "PURO-BIOCHAR-6.2",
        "rule_title": "Molar H/Corg Maximum Carbonization Threshold (< 0.70) for CORC200+",
        "applicability_condition": "Mandatory for all lab analyses",
        "requirement_type": "QUANTIFICATION",
        "implementation_handler": "verify_molar_h_c_and_permanence",
        "required_evidence_types": ["ACCREDITED_LAB_REPORT_ISO_17025"],
        "is_blocking": True,
    },
    {
        "section_number": 6,
        "section_title": "Stored Carbon, Dry Mass & Persistence Modeling",
        "rule_number": "PURO-BIOCHAR-6.3",
        "rule_title": "Edition 2025 V2 Decay Model with Table 6.1 Regression Parameters (Closs = Cstored * (100 - PF) / 100)",
        "applicability_condition": "Mandatory calculation of Closs",
        "requirement_type": "QUANTIFICATION",
        "implementation_handler": "calculate_storage_loss_closs",
        "required_evidence_types": ["SOIL_TEMPERATURE_EVIDENCE", "REGIONAL_CLIMATE_RECORD"],
        "is_blocking": True,
    },
    # Chapter 7: Project Emissions
    {
        "section_number": 7,
        "section_title": "Project Emissions Accounting",
        "rule_number": "PURO-BIOCHAR-7.1",
        "rule_title": "Full Life Cycle Project Emissions (Eproject = Eops + Eemb) and LHV Co-Product Allocation",
        "applicability_condition": "Mandatory for production run",
        "requirement_type": "QUANTIFICATION",
        "implementation_handler": "calculate_project_emissions",
        "required_evidence_types": ["LCA_MODEL_DOSSIER", "LCI_DATABASE_EXPORT", "ENERGY_METER_DATA"],
        "is_blocking": True,
    },
    # Chapter 8: Leakage
    {
        "section_number": 8,
        "section_title": "Leakage Assessment",
        "rule_number": "PURO-BIOCHAR-8.1",
        "rule_title": "Leakage Emissions Quantification (Eleakage = LECO + LMA + iLUC)",
        "applicability_condition": "Mandatory before final quantification",
        "requirement_type": "QUANTIFICATION",
        "implementation_handler": "evaluate_leakage_mitigation",
        "required_evidence_types": ["BIOMASS_AVAILABILITY_STUDY", "BASELINE_DISPLACEMENT_JUSTIFICATION"],
        "is_blocking": True,
    },
    # Chapter 9: Monitoring Plan & Frequency
    {
        "section_number": 9,
        "section_title": "Operational Monitoring Plan",
        "rule_number": "PURO-BIOCHAR-9.1",
        "rule_title": "Approved Facility Monitoring Plan & Parameter Frequency Adherence",
        "applicability_condition": "Active facility operational lifecycle",
        "requirement_type": "MONITORING",
        "implementation_handler": "verify_monitoring_plan_and_records",
        "required_evidence_types": ["VALIDATED_MONITORING_PLAN", "CALIBRATION_LOGS"],
        "is_blocking": True,
    },
    # Chapter 10: Sampling, Testing, Quality Control & Uncertainty
    {
        "section_number": 10,
        "section_title": "Sampling, Quality Control & Measurement Uncertainty",
        "rule_number": "PURO-BIOCHAR-10.1",
        "rule_title": "Representative Sampling Plan (ISO 18135) and Chain of Custody",
        "applicability_condition": "Mandatory for each production batch",
        "requirement_type": "MONITORING",
        "implementation_handler": "verify_sampling_plan_execution",
        "required_evidence_types": ["SAMPLING_CERTIFICATE", "LAB_CHAIN_OF_CUSTODY"],
        "is_blocking": True,
    },
    {
        "section_number": 10,
        "section_title": "Sampling, Quality Control & Measurement Uncertainty",
        "rule_number": "PURO-BIOCHAR-10.2",
        "rule_title": "Environmental Quality Limits: Potentially Toxic Elements (PTEs) & PAHs",
        "applicability_condition": "Mandatory parameter limits on biochar testing",
        "requirement_type": "ELIGIBILITY",
        "implementation_handler": "verify_environmental_quality_limits",
        "required_evidence_types": ["LAB_ANALYSIS_HEAVY_METALS_PAH"],
        "is_blocking": True,
    },
    {
        "section_number": 10,
        "section_title": "Sampling, Quality Control & Measurement Uncertainty",
        "rule_number": "PURO-BIOCHAR-10.3",
        "rule_title": "Combined Measurement Uncertainty Estimation and Reporting (x ± U%) per ISO GUM",
        "applicability_condition": "Mandatory uncertainty calculation and reporting",
        "requirement_type": "QUANTIFICATION",
        "implementation_handler": "calculate_uncertainty_and_deductions",
        "required_evidence_types": ["MEASUREMENT_UNCERTAINTY_BUDGET"],
        "is_blocking": True,
    },
    # Chapter 11: Output Reporting, Audits & Readiness
    {
        "section_number": 11,
        "section_title": "Output Reporting, Auditing & Registry Issuance Readiness",
        "rule_number": "PURO-BIOCHAR-11.1",
        "rule_title": "Production Facility Audit & Output Audit Completion Prior to Issuance",
        "applicability_condition": "Mandatory for credit issuance",
        "requirement_type": "AUDIT",
        "implementation_handler": "verify_audit_workflows_status",
        "required_evidence_types": ["FACILITY_AUDIT_REPORT", "OUTPUT_AUDIT_STATEMENT"],
        "is_blocking": True,
    },
    {
        "section_number": 11,
        "section_title": "Output Reporting, Auditing & Registry Issuance Readiness",
        "rule_number": "PURO-BIOCHAR-11.2",
        "rule_title": "Cryptographic Manifest Sealing of Puro Output Report and CORC Package",
        "applicability_condition": "Mandatory seal before registry submission",
        "requirement_type": "AUDIT",
        "implementation_handler": "seal_output_report_package",
        "required_evidence_types": ["OUTPUT_REPORT_MANIFEST", "LEDGER_SIGNATURE"],
        "is_blocking": True,
    },
]


# ---------------------------------------------------------------------------
# Idempotent Normative Metadata Seed Function
# ---------------------------------------------------------------------------
async def seed_puro_biochar_normative_metadata(db: AsyncSession) -> Any:
    """
    Seeds normative Puro.earth Biochar Edition 2025 V2 rules, Table 3.2 categories (all 28),
    and external normative dependencies into the database idempotently.
    DOES NOT create fake production activity or fake CORCs.
    """
    from app.domains.biochar.puro_models import (
        PuroEndUseCategory,
        PuroMethodologyVersion,
        PuroNormativeDependency,
        PuroRuleDefinition,
    )

    # 1. Upsert PuroMethodologyVersion
    stmt_v = select(PuroMethodologyVersion).where(PuroMethodologyVersion.code == "PURO_BIOCHAR_2025_V2")
    res_v = await db.execute(stmt_v)
    meth_version = res_v.scalar_one_or_none()
    if not meth_version:
        meth_version = PuroMethodologyVersion(
            code="PURO_BIOCHAR_2025_V2",
            name="Puro.earth Biochar Methodology Edition 2025 Version 2",
            edition="Edition 2025 v2",
            approval_date=date(2025, 11, 27),
            effective_date=date(2025, 11, 27),
            status="ACTIVE",
            source_url="https://puro.earth/biochar/",
            metadata_json={
                "credit_unit": "CORC",
                "durability_framework": "CORC200+",
                "persistence_model": "EDITION_2025_V2_TABLE_6_1_DECAY",
                "max_crediting_period_years": 30,
            },
        )
        db.add(meth_version)
        await db.flush()

    # 2. Seed Normative Dependencies
    for dep_data in NORMATIVE_DEPENDENCIES:
        stmt_dep = select(PuroNormativeDependency).where(PuroNormativeDependency.code == dep_data["code"])
        res_dep = await db.execute(stmt_dep)
        existing_dep = res_dep.scalar_one_or_none()
        if not existing_dep:
            dep = PuroNormativeDependency(
                code=dep_data["code"],
                title=dep_data["title"],
                version=dep_data["version"],
                document_type=dep_data["document_type"],
                status=dep_data["status"],
                effective_date=dep_data["effective_date"],
                source_reference=dep_data["source_reference"],
                required_by_rules=dep_data["required_by_rules"],
                implementation_state=dep_data["implementation_state"],
            )
            db.add(dep)
        else:
            existing_dep.title = dep_data["title"]
            existing_dep.required_by_rules = dep_data["required_by_rules"]

    # 3. Seed Rule Definitions
    for r_data in METHODOLOGY_RULES_CATALOG:
        stmt_r = select(PuroRuleDefinition).where(PuroRuleDefinition.rule_number == r_data["rule_number"])
        res_r = await db.execute(stmt_r)
        existing_r = res_r.scalar_one_or_none()
        if not existing_r:
            rule = PuroRuleDefinition(
                methodology_version_id=meth_version.id,
                section_number=r_data["section_number"],
                section_title=r_data["section_title"],
                rule_number=r_data["rule_number"],
                rule_title=r_data["rule_title"],
                applicability_condition=r_data["applicability_condition"],
                requirement_type=r_data["requirement_type"],
                implementation_handler=r_data["implementation_handler"],
                required_evidence_types=r_data["required_evidence_types"],
                is_blocking=r_data["is_blocking"],
            )
            db.add(rule)
        else:
            existing_r.rule_title = r_data["rule_title"]
            existing_r.required_evidence_types = r_data["required_evidence_types"]

    # 4. Clean up any stale legacy category codes not in official Table 3.2
    valid_cat_codes = {cat_data["category_code"] for cat_data in TABLE_3_2_CATEGORIES}
    stmt_stale = select(PuroEndUseCategory).where(~PuroEndUseCategory.category_code.in_(valid_cat_codes))
    res_stale = await db.execute(stmt_stale)
    for stale_cat in res_stale.scalars().all():
        await db.delete(stale_cat)

    # 5. Seed all 28 Table 3.2 End Use Categories
    for cat_data in TABLE_3_2_CATEGORIES:
        stmt_cat = select(PuroEndUseCategory).where(PuroEndUseCategory.category_code == cat_data["category_code"])
        res_cat = await db.execute(stmt_cat)
        existing_cat = res_cat.scalar_one_or_none()
        if not existing_cat:
            cat = PuroEndUseCategory(
                category_code=cat_data["category_code"],
                category_name=cat_data["category_name"],
                sector=cat_data["sector"],
                product_type=cat_data["product_type"],
                pure_or_mixed=cat_data["pure_or_mixed"],
                application_type=cat_data.get("application_type", "FINAL"),
                is_corc_eligible=cat_data["is_corc_eligible"],
                min_environmental_quality=cat_data.get("min_environmental_quality", "WBC Agro"),
                default_durability_years=cat_data["default_durability_years"],
                persistence_factor_non_soil=None,
                reversal_rules=cat_data.get("reversal_rules"),
                cascading_conditions=cat_data.get("cascading_conditions"),
                reversal_discount_factor_required=cat_data.get("reversal_discount_factor_required", False),
                required_evidence_types=cat_data["required_evidence_types"],
                rule_references=cat_data["rule_references"],
            )
            db.add(cat)
        else:
            existing_cat.category_name = cat_data["category_name"]
            existing_cat.sector = cat_data["sector"]
            existing_cat.product_type = cat_data["product_type"]
            existing_cat.pure_or_mixed = cat_data["pure_or_mixed"]
            if hasattr(existing_cat, "application_type"):
                existing_cat.application_type = cat_data.get("application_type", "FINAL")
            if hasattr(existing_cat, "min_environmental_quality"):
                existing_cat.min_environmental_quality = cat_data.get("min_environmental_quality", "WBC Agro")
            existing_cat.is_corc_eligible = cat_data["is_corc_eligible"]
            existing_cat.default_durability_years = cat_data["default_durability_years"]
            existing_cat.persistence_factor_non_soil = None
            if hasattr(existing_cat, "reversal_rules"):
                existing_cat.reversal_rules = cat_data.get("reversal_rules")
            if hasattr(existing_cat, "cascading_conditions"):
                existing_cat.cascading_conditions = cat_data.get("cascading_conditions")
            if hasattr(existing_cat, "reversal_discount_factor_required"):
                existing_cat.reversal_discount_factor_required = cat_data.get("reversal_discount_factor_required", False)
            existing_cat.required_evidence_types = cat_data["required_evidence_types"]
            existing_cat.rule_references = cat_data["rule_references"]

    await db.commit()
    return meth_version
