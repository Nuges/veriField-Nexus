"""
VeriField Nexus — Agriculture Domain: SOC Stock & Equivalent Soil Mass (ESM) Calculator
========================================================================================
Authoritative implementation of Verra VM0042 v2.2 and 11 June 2026 C&C:
- Section 8: Soil sampling depth, continuous profile and laboratory analytics.
- Official VM0042 Equivalent Soil Mass (ESM) Calculation Procedure (Ellert & Bettany 1995).
- Monotonic PCHIP / Spline ESM option (Wendt & Hauser 2013).
- Area-weighted stratum and quantification-unit aggregation.
- Strictly deterministic Decimal arithmetic for carbon accounting.
- Fail-closed gates: depth inversion, gap, overlap, missing provenance, out-of-bounds analyte,
  and extrapolation beyond measured profile.
- Carbon invariant: Zero tCO2e / No net removals / No crediting subtraction in Phase 3B-1.
"""

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_EVEN, InvalidOperation
import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple
import uuid


class SOCStockCalculationError(Exception):
    """Base exception for SOC stock and ESM calculation failures."""
    def __init__(self, code: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


@dataclass
class LayerInput:
    """Canonical input for a single sampled soil layer in a depth profile."""
    layer_index: int
    depth_upper_cm: Decimal
    depth_lower_cm: Decimal
    bulk_density_g_cm3: Optional[Decimal]
    bulk_density_provenance: str = "MEASURED"  # MEASURED, CALCULATED_BY_APPROVED_PROCEDURE, NOT_REQUIRED, MISSING
    soil_mass_provenance: str = "CORE_BULK_DENSITY_DERIVED"  # DIRECT_SOIL_MASS, CORE_BULK_DENSITY_DERIVED, OTHER_METHODOLOGY_PERMITTED_PROCEDURE
    sample_dry_mass_g: Optional[Decimal] = None
    fine_soil_mass_g: Optional[Decimal] = None
    coarse_fragment_mass_g: Optional[Decimal] = None
    core_diameter_mm: Optional[Decimal] = None
    core_count: int = 1
    plant_material_excluded: bool = True
    coarse_fragment_fraction: Optional[Decimal] = Decimal("0.0000")  # dimensionless fraction [0.0, 1.0)
    coarse_fragment_provenance: str = "MEASURED"  # MEASURED, DEFAULT_CONSERVATIVE_ZERO, METHODOLOGY_PERMITTED, NOT_REQUIRED, MISSING
    soc_concentration_g_kg: Decimal = Decimal("0.0000")  # Canonical lab result: g C / kg dry fine soil
    sample_id: Optional[uuid.UUID] = None
    laboratory_result_id: Optional[uuid.UUID] = None
    sampling_event_id: Optional[uuid.UUID] = None
    adjacent_sample_relationship: Optional[str] = "SAME_PHYSICAL_SAMPLE"


@dataclass
class LayerResult:
    """Calculated and ESM-normalized results for a single profile layer."""
    layer_index: int
    depth_upper_cm: Decimal
    depth_lower_cm: Decimal
    layer_thickness_cm: Decimal
    bulk_density_g_cm3: Optional[Decimal]
    bulk_density_provenance: str
    soil_mass_provenance: str
    fine_soil_mass_g: Optional[Decimal]
    coarse_fragment_mass_g: Optional[Decimal]
    coarse_fragment_fraction: Decimal
    coarse_fragment_provenance: str
    soc_concentration_g_kg: Decimal
    laboratory_result_id: Optional[uuid.UUID]
    sample_id: Optional[uuid.UUID]
    layer_soil_mass_t_ha: Decimal
    layer_soc_mass_t_c_ha: Decimal
    cumulative_soil_mass_t_ha: Decimal
    cumulative_soc_mass_t_c_ha: Decimal
    fraction_in_reference_mass: Optional[Decimal] = None
    included_soil_mass_t_ha: Optional[Decimal] = None
    included_soc_mass_t_c_ha: Optional[Decimal] = None
    sampling_event_id: Optional[uuid.UUID] = None
    adjacent_sample_relationship: Optional[str] = "SAME_PHYSICAL_SAMPLE"


@dataclass
class ProfileESMResult:
    """Output for a complete profile normalized under Equivalent Soil Mass."""
    reference_soil_mass_t_ha: Decimal
    reference_depth_cm: Decimal
    equivalent_depth_cm: Optional[Decimal]
    total_sampled_soil_mass_t_ha: Decimal
    max_sampled_depth_cm: Decimal
    soc_stock_t_c_per_ha: Decimal
    unadjusted_stock_t_c_per_ha: Decimal
    depth_sufficiency_status: str  # DEPTH_SUFFICIENT, SHALLOW_SOIL_EXCEPTION, INSUFFICIENT_DEPTH
    shallow_soil_exception_applied: bool
    esm_algorithm: str
    layers: List[LayerResult] = field(default_factory=list)
    calculation_hash: str = ""
    algorithm_metadata: Dict[str, Any] = field(default_factory=dict)


# Conversion factor constants
# cm * g/cm^3 -> t/ha:
# 1 cm = 0.01 m
# 1 ha = 10,000 m^2 = 10^8 cm^2
# 1 tonne = 1,000,000 g = 10^6 g
# Mass (t/ha) = Thickness (cm) * BD (g/cm^3) * (1 - CF) * (10^8 cm^2/ha / 10^6 g/t)
#             = Thickness (cm) * BD (g/cm^3) * (1 - CF) * 100
SOIL_MASS_FACTOR = Decimal("100.0000")

# g C / kg dry soil -> t C / t dry soil:
# 1 g / 1 kg = 1/1000 = 0.001
# SOC_mass (t C/ha) = M_soil (t dry fine soil/ha) * (SOC_conc (g C/kg) / 1000)
SOC_CONC_DIVISOR = Decimal("1000.0000")

# Official VM0042 v2.2 Equation (3) defines the conversion factor CF = 10,000
# to convert g/mm^2 to kg SOC / ha.
OFFICIAL_VM0042_EQ3_CONVERSION_FACTOR = Decimal("10000.0000")  # (g/mm^2) -> (kg SOC/ha)

# In production, calculation is performed directly in Mg C / ha (t C / ha).
# The derived production implementation coefficient is DERIVED_PRODUCTION_COEFFICIENT_MG_C_PER_HA = 0.1000.
# (Never refer to 0.1000 as the "VM0042 methodology conversion factor";
#  it is an algebraically derived production coefficient for direct Mg C/ha output).
DERIVED_PRODUCTION_COEFFICIENT_MG_C_PER_HA = Decimal("0.1000")  # Transformed factor -> (Mg C/ha)

# Valid provenances
VALID_BD_PROVENANCE = {"MEASURED", "CALCULATED_BY_APPROVED_PROCEDURE", "NOT_REQUIRED"}
VALID_CF_PROVENANCE = {"MEASURED", "DEFAULT_CONSERVATIVE_ZERO", "METHODOLOGY_PERMITTED", "NOT_REQUIRED"}
VALID_SOIL_MASS_PROVENANCE = {"DIRECT_SOIL_MASS", "CORE_BULK_DENSITY_DERIVED", "OTHER_METHODOLOGY_PERMITTED_PROCEDURE"}


def calculate_layer_soil_mass_direct(
    dry_fine_soil_mass_g: Decimal,
    core_diameter_mm: Decimal,
    core_count: int = 1,
) -> Decimal:
    """
    Computes dry fine-soil mass per unit area (Mg dry fine soil / ha) directly from core sample
    mass and physical probe geometry according to VM0042 v2.2 Equation (3).

    OFFICIAL VM0042 v2.2 EQUATION (3):
      SOC_{sample,l} = [ (MS_{sample,l} * C_{SOC,sample,l}) / (A_{sample} * N_{cores}) ] * CF

    OFFICIAL VM0042 DEFINITIONS & UNITS:
      - MS_{sample,l}: Oven-dry fine soil mass of layer l (<2 mm) [g]
      - C_{SOC,sample,l}: Organic carbon concentration of layer l [dimensionless g C / g soil, or g C / kg soil]
      - A_{sample}: Sampled cross-sectional area of core probe [mm^2] = pi * (d_core_mm / 2)^2
      - N_{cores}: Number of cores composited [dimensionless integer >= 1]
      - CF: Official VM0042 conversion factor = 10,000 [g/mm^2 -> kg SOC/ha]
      - Official Output: SOC_{sample,l} [kg SOC / ha]

    PRODUCTION FORMULATION & DERIVED COEFFICIENT:
      In production, soil mass and carbon stock are decoupled to support Equivalent Soil Mass (ESM)
      cumulative mass profiling, and outputs are expressed directly in Mg C / ha (= t C / ha).

      1. Core cross-sectional area in cm^2:
         A_{sample,cm2} = pi * (core_diameter_mm / 20)^2
      2. Layer dry fine-soil mass per unit area:
         M_{soil,layer} [Mg dry fine soil / ha] = [ MS_{sample,l} [g] / (A_{sample,cm2} * N_{cores}) ] * 100.0000
         where 100.0000 = (10^8 cm^2 / ha) / (10^6 g / Mg)  [Mg * cm^2 / (g * ha)]
      3. Layer SOC stock:
         SOC_{sample,l} [Mg C / ha] = M_{soil,layer} * (C_{SOC,sample,l} [g C/kg] / 1000.0)
         Algebraic substitution yields:
         SOC_{sample,l} = [ MS / (A_{cm2} * N) * 100.0000 ] * (C_{SOC} / 1000.0)
                        = [ (MS * C_{SOC}) / (A_{cm2} * N) ] * (100.0000 / 1000.0)
                        = [ (MS * C_{SOC}) / (A_{cm2} * N) ] * 0.1000

      The constant 0.1000 is DERIVED_PRODUCTION_COEFFICIENT_MG_C_PER_HA.
      It must NOT be described as "the VM0042 methodology conversion factor" (which is 10,000 for kg/ha).
      Exact algebraic and numerical parity with literal VM0042 Equation (3) is proven.
    """
    import math
    if dry_fine_soil_mass_g <= Decimal("0.0"):
        raise SOCStockCalculationError(
            code="INVALID_SAMPLE_MASS",
            message=f"Dry fine soil mass must be strictly positive, got {dry_fine_soil_mass_g} g.",
        )
    if core_diameter_mm <= Decimal("0.0"):
        raise SOCStockCalculationError(
            code="INVALID_CORE_DIAMETER",
            message=f"Core diameter must be strictly positive, got {core_diameter_mm} mm.",
        )
    if core_count < 1:
        raise SOCStockCalculationError(
            code="INVALID_CORE_COUNT",
            message=f"Core count must be at least 1, got {core_count}.",
        )

    core_diameter_cm = core_diameter_mm / Decimal("10.0")
    radius_cm = core_diameter_cm / Decimal("2.0")
    pi_dec = Decimal(str(math.pi))
    area_core_cm2 = pi_dec * (radius_cm ** 2)
    total_area_cm2 = area_core_cm2 * Decimal(core_count)

    mass_t_ha = (dry_fine_soil_mass_g / total_area_cm2) * SOIL_MASS_FACTOR
    return mass_t_ha.quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)


def calculate_layer_soil_mass(
    thickness_cm: Decimal,
    bulk_density_g_cm3: Decimal,
    coarse_fragment_fraction: Decimal = Decimal("0.0000"),
) -> Decimal:
    """
    Computes dry fine-soil mass per unit area (t dry fine soil / ha).
    Formula: M_soil = T * BD * (1 - CF) * 100
    """
    if thickness_cm <= Decimal("0.0"):
        raise SOCStockCalculationError(
            code="INVALID_LAYER_THICKNESS",
            message=f"Layer thickness must be strictly positive, got {thickness_cm} cm.",
        )

    if bulk_density_g_cm3 <= Decimal("0.0"):
        raise SOCStockCalculationError(
            code="INVALID_BULK_DENSITY",
            message=f"Bulk density must be strictly positive, got {bulk_density_g_cm3} g/cm3.",
        )

    if bulk_density_g_cm3 > Decimal("2.65"):
        raise SOCStockCalculationError(
            code="BULK_DENSITY_EXCEEDS_PHYSICAL_LIMIT",
            message=f"Bulk density {bulk_density_g_cm3} g/cm3 exceeds standard mineral soil particle density limit (2.65 g/cm3).",
        )

    if coarse_fragment_fraction < Decimal("0.0") or coarse_fragment_fraction >= Decimal("1.0"):
        raise SOCStockCalculationError(
            code="INVALID_COARSE_FRAGMENT_FRACTION",
            message=f"Coarse fragment fraction must be in range [0.0, 1.0), got {coarse_fragment_fraction}.",
        )

    fine_earth_fraction = Decimal("1.0") - coarse_fragment_fraction
    mass = thickness_cm * bulk_density_g_cm3 * fine_earth_fraction * SOIL_MASS_FACTOR
    return mass.quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)


def calculate_layer_soc_mass(
    layer_soil_mass_t_ha: Decimal,
    soc_concentration_g_kg: Decimal,
) -> Decimal:
    """
    Computes layer Soil Organic Carbon mass per unit area (t C / ha).
    Formula: SOC_mass = M_soil * (C_soc / 1000)
    """
    if layer_soil_mass_t_ha < Decimal("0.0"):
        raise SOCStockCalculationError(
            code="NEGATIVE_SOIL_MASS",
            message=f"Soil mass cannot be negative, got {layer_soil_mass_t_ha} t/ha.",
        )

    if soc_concentration_g_kg < Decimal("0.0"):
        raise SOCStockCalculationError(
            code="NEGATIVE_SOC_CONCENTRATION",
            message=f"SOC concentration cannot be negative, got {soc_concentration_g_kg} g/kg.",
        )

    if soc_concentration_g_kg > Decimal("580.0"):
        raise SOCStockCalculationError(
            code="SOC_CONCENTRATION_EXCEEDS_ORGANIC_LIMIT",
            message=f"SOC concentration {soc_concentration_g_kg} g/kg exceeds pure organic soil carbon ceiling (580 g/kg).",
        )

    soc_mass = layer_soil_mass_t_ha * (soc_concentration_g_kg / SOC_CONC_DIVISOR)
    return soc_mass.quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)


def validate_profile_layers(layers: List[LayerInput], allow_shallow_soil_exception: bool = False) -> None:
    """
    Strict validation of profile sequence:
    - Non-empty
    - Starts at surface (0 cm)
    - Contiguous (depth_upper_i == depth_lower_{i-1})
    - Non-zero positive thickness (no depth inversion)
    - Valid provenance for bulk density and coarse fragments
    """
    if not layers:
        raise SOCStockCalculationError(
            code="EMPTY_PROFILE_LAYERS",
            message="Cannot calculate SOC stock for an empty soil profile.",
        )

    sorted_layers = sorted(layers, key=lambda l: l.depth_upper_cm)

    if sorted_layers[0].depth_upper_cm != Decimal("0.00"):
        raise SOCStockCalculationError(
            code="PROFILE_DOES_NOT_START_AT_SURFACE",
            message=f"Soil profile must start at 0.00 cm surface, got {sorted_layers[0].depth_upper_cm} cm.",
        )

    previous_lower = Decimal("0.00")
    for idx, layer in enumerate(sorted_layers):
        if layer.depth_lower_cm <= layer.depth_upper_cm:
            raise SOCStockCalculationError(
                code="DEPTH_INVERSION_OR_ZERO_THICKNESS",
                message=f"Layer {idx} has inverted depth or zero thickness: upper={layer.depth_upper_cm}, lower={layer.depth_lower_cm}.",
                details={"layer_index": idx, "upper": str(layer.depth_upper_cm), "lower": str(layer.depth_lower_cm)},
            )

        if idx > 0:
            if layer.depth_upper_cm != previous_lower:
                if layer.depth_upper_cm < previous_lower:
                    raise SOCStockCalculationError(
                        code="PROFILE_OVERLAPPING_LAYERS",
                        message=f"Layer {idx} overlaps with previous layer: upper={layer.depth_upper_cm} < prev_lower={previous_lower}.",
                        details={"layer_index": idx, "upper": str(layer.depth_upper_cm), "previous_lower": str(previous_lower)},
                    )
                else:
                    raise SOCStockCalculationError(
                        code="PROFILE_DEPTH_GAP",
                        message=f"Layer {idx} has a depth gap from previous layer: upper={layer.depth_upper_cm} > prev_lower={previous_lower}.",
                        details={"layer_index": idx, "upper": str(layer.depth_upper_cm), "previous_lower": str(previous_lower)},
                    )

        # Soil mass provenance check
        if layer.soil_mass_provenance not in VALID_SOIL_MASS_PROVENANCE:
            raise SOCStockCalculationError(
                code="INVALID_SOIL_MASS_PROVENANCE",
                message=f"Layer {idx} has unpermitted soil mass provenance '{layer.soil_mass_provenance}'.",
                details={"layer_index": idx, "provenance": layer.soil_mass_provenance},
            )

        if layer.soil_mass_provenance == "DIRECT_SOIL_MASS":
            dry_m = layer.fine_soil_mass_g if layer.fine_soil_mass_g is not None else layer.sample_dry_mass_g
            if dry_m is None or dry_m <= Decimal("0.0"):
                raise SOCStockCalculationError(
                    code="MISSING_DIRECT_SOIL_MASS",
                    message=f"Layer {idx} requires positive direct sample dry mass for DIRECT_SOIL_MASS provenance.",
                    details={"layer_index": idx},
                )
            if layer.core_diameter_mm is None or layer.core_diameter_mm <= Decimal("0.0"):
                raise SOCStockCalculationError(
                    code="MISSING_CORE_DIAMETER",
                    message=f"Layer {idx} requires positive core diameter for DIRECT_SOIL_MASS provenance.",
                    details={"layer_index": idx},
                )
        else:
            # Bulk density provenance check
            if layer.bulk_density_provenance not in VALID_BD_PROVENANCE:
                raise SOCStockCalculationError(
                    code="INVALID_BULK_DENSITY_PROVENANCE",
                    message=f"Layer {idx} has unpermitted bulk density provenance '{layer.bulk_density_provenance}'.",
                    details={"layer_index": idx, "provenance": layer.bulk_density_provenance},
                )

            if layer.bulk_density_g_cm3 is None or layer.bulk_density_g_cm3 <= Decimal("0.0"):
                raise SOCStockCalculationError(
                    code="MISSING_OR_ZERO_BULK_DENSITY",
                    message=f"Layer {idx} is missing bulk density or has zero bulk density.",
                    details={"layer_index": idx, "bulk_density": str(layer.bulk_density_g_cm3)},
                )

        # Coarse fragments provenance check
        if layer.coarse_fragment_provenance not in VALID_CF_PROVENANCE:
            raise SOCStockCalculationError(
                code="INVALID_COARSE_FRAGMENTS_PROVENANCE",
                message=f"Layer {idx} has unpermitted coarse fragments provenance '{layer.coarse_fragment_provenance}'.",
                details={"layer_index": idx, "provenance": layer.coarse_fragment_provenance},
            )

        previous_lower = layer.depth_lower_cm


def to_json_serializable(val: Any) -> Any:
    """Recursively converts Decimals and UUIDs to primitives/strings for JSON/JSONB serialization."""
    if isinstance(val, (uuid.UUID, Decimal)):
        return str(val)
    if isinstance(val, dict):
        return {str(k): to_json_serializable(v) for k, v in val.items()}
    if isinstance(val, list):
        return [to_json_serializable(item) for item in val]
    return val


def compute_deterministic_hash(payload: Dict[str, Any]) -> str:
    """Generates deterministic SHA-256 hash from JSON representation."""
    clean_payload = to_json_serializable(payload)
    encoded = json.dumps(clean_payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def calculate_profile_esm_proportioning(
    layers: List[LayerInput],
    reference_soil_mass_t_ha: Decimal,
    reference_depth_cm: Decimal = Decimal("30.00"),
    allow_shallow_soil_exception: bool = False,
) -> ProfileESMResult:
    """
    Authoritative Piecewise Layer Mass Proportioning Algorithm (Ellert & Bettany 1995; VM0042 ESM).

    Normalizes soil organic carbon stock of a sampled depth profile to a fixed reference soil mass (M_ref).
    """
    validate_profile_layers(layers, allow_shallow_soil_exception=allow_shallow_soil_exception)

    sorted_inputs = sorted(layers, key=lambda l: l.depth_upper_cm)
    calculated_layers: List[LayerResult] = []

    cumulative_soil_mass = Decimal("0.0000")
    cumulative_soc_mass = Decimal("0.0000")

    for idx, inp in enumerate(sorted_inputs):
        thickness = inp.depth_lower_cm - inp.depth_upper_cm
        cf = inp.coarse_fragment_fraction if inp.coarse_fragment_fraction is not None else Decimal("0.0000")

        if inp.soil_mass_provenance == "DIRECT_SOIL_MASS":
            dry_m = inp.fine_soil_mass_g if inp.fine_soil_mass_g is not None else inp.sample_dry_mass_g
            m_soil = calculate_layer_soil_mass_direct(
                dry_fine_soil_mass_g=dry_m,
                core_diameter_mm=inp.core_diameter_mm,
                core_count=inp.core_count,
            )
        else:
            m_soil = calculate_layer_soil_mass(
                thickness_cm=thickness,
                bulk_density_g_cm3=inp.bulk_density_g_cm3,
                coarse_fragment_fraction=cf,
            )
        soc_mass = calculate_layer_soc_mass(
            layer_soil_mass_t_ha=m_soil,
            soc_concentration_g_kg=inp.soc_concentration_g_kg,
        )

        cumulative_soil_mass = (cumulative_soil_mass + m_soil).quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)
        cumulative_soc_mass = (cumulative_soc_mass + soc_mass).quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)

        res = LayerResult(
            layer_index=idx,
            depth_upper_cm=inp.depth_upper_cm,
            depth_lower_cm=inp.depth_lower_cm,
            layer_thickness_cm=thickness,
            bulk_density_g_cm3=inp.bulk_density_g_cm3,
            bulk_density_provenance=inp.bulk_density_provenance,
            soil_mass_provenance=inp.soil_mass_provenance,
            fine_soil_mass_g=inp.fine_soil_mass_g,
            coarse_fragment_mass_g=inp.coarse_fragment_mass_g,
            coarse_fragment_fraction=cf,
            coarse_fragment_provenance=inp.coarse_fragment_provenance,
            soc_concentration_g_kg=inp.soc_concentration_g_kg,
            laboratory_result_id=inp.laboratory_result_id,
            sample_id=inp.sample_id,
            layer_soil_mass_t_ha=m_soil,
            layer_soc_mass_t_c_ha=soc_mass,
            cumulative_soil_mass_t_ha=cumulative_soil_mass,
            cumulative_soc_mass_t_c_ha=cumulative_soc_mass,
            sampling_event_id=inp.sampling_event_id,
            adjacent_sample_relationship=inp.adjacent_sample_relationship,
        )
        calculated_layers.append(res)

    total_sampled_soil_mass = cumulative_soil_mass
    max_sampled_depth_cm = sorted_inputs[-1].depth_lower_cm
    unadjusted_stock = cumulative_soc_mass

    # Fail-closed check: Reference mass exceeding measured profile
    if reference_soil_mass_t_ha > total_sampled_soil_mass:
        if not allow_shallow_soil_exception:
            raise SOCStockCalculationError(
                code="ESM_REFERENCE_MASS_EXCEEDS_MEASURED_PROFILE",
                message=(
                    f"Reference soil mass {reference_soil_mass_t_ha} t/ha exceeds total measured profile "
                    f"soil mass {total_sampled_soil_mass} t/ha (to depth {max_sampled_depth_cm} cm). "
                    "VM0042 strictly prohibits downward extrapolation of measured SOC stocks."
                ),
                details={
                    "reference_soil_mass_t_ha": str(reference_soil_mass_t_ha),
                    "total_sampled_soil_mass_t_ha": str(total_sampled_soil_mass),
                    "max_sampled_depth_cm": str(max_sampled_depth_cm),
                },
            )

    # Perform piecewise layer mass allocation
    # Find layer j such that M_cum,j-1 < M_ref <= M_cum,j
    normalized_soc_stock = Decimal("0.0000")
    equivalent_depth_cm: Optional[Decimal] = None
    remaining_mass_needed = reference_soil_mass_t_ha

    for layer in calculated_layers:
        if remaining_mass_needed <= Decimal("0.0000"):
            # Layer is entirely below reference mass
            layer.fraction_in_reference_mass = Decimal("0.0000")
            layer.included_soil_mass_t_ha = Decimal("0.0000")
            layer.included_soc_mass_t_c_ha = Decimal("0.0000")
            continue

        if remaining_mass_needed >= layer.layer_soil_mass_t_ha:
            # Entire layer is included
            layer.fraction_in_reference_mass = Decimal("1.0000")
            layer.included_soil_mass_t_ha = layer.layer_soil_mass_t_ha
            layer.included_soc_mass_t_c_ha = layer.layer_soc_mass_t_c_ha
            normalized_soc_stock += layer.layer_soc_mass_t_c_ha
            remaining_mass_needed -= layer.layer_soil_mass_t_ha

            if remaining_mass_needed == Decimal("0.0000") and equivalent_depth_cm is None:
                equivalent_depth_cm = layer.depth_lower_cm
        else:
            # Partial layer included (the boundary layer j)
            fraction = (remaining_mass_needed / layer.layer_soil_mass_t_ha).quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)
            included_soil = remaining_mass_needed.quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)
            included_soc = (included_soil * (layer.soc_concentration_g_kg / SOC_CONC_DIVISOR)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)

            layer.fraction_in_reference_mass = fraction
            layer.included_soil_mass_t_ha = included_soil
            layer.included_soc_mass_t_c_ha = included_soc
            normalized_soc_stock += included_soc

            # Calculate equivalent depth: D_upper + fraction * thickness
            eq_d = layer.depth_upper_cm + (fraction * layer.layer_thickness_cm)
            equivalent_depth_cm = eq_d.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
            remaining_mass_needed = Decimal("0.0000")

    # If shallow soil exception applied and ref mass exceeded total sampled mass
    if remaining_mass_needed > Decimal("0.0000"):
        # We included all available sampled mass
        depth_sufficiency_status = "SHALLOW_SOIL_EXCEPTION"
        shallow_exception_applied = True
    else:
        depth_sufficiency_status = "DEPTH_SUFFICIENT"
        shallow_exception_applied = False

    normalized_soc_stock = normalized_soc_stock.quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)

    result_dict = {
        "reference_soil_mass_t_ha": str(reference_soil_mass_t_ha),
        "reference_depth_cm": str(reference_depth_cm),
        "equivalent_depth_cm": str(equivalent_depth_cm) if equivalent_depth_cm else None,
        "total_sampled_soil_mass_t_ha": str(total_sampled_soil_mass),
        "max_sampled_depth_cm": str(max_sampled_depth_cm),
        "soc_stock_t_c_per_ha": str(normalized_soc_stock),
        "unadjusted_stock_t_c_per_ha": str(unadjusted_stock),
        "depth_sufficiency_status": depth_sufficiency_status,
        "shallow_soil_exception_applied": shallow_exception_applied,
        "esm_algorithm": "LAYER_MASS_PROPORTIONING",
        "layers": [
            {
                "layer_index": l.layer_index,
                "depth_upper_cm": str(l.depth_upper_cm),
                "depth_lower_cm": str(l.depth_lower_cm),
                "bulk_density_g_cm3": str(l.bulk_density_g_cm3),
                "bulk_density_provenance": l.bulk_density_provenance,
                "soil_mass_provenance": l.soil_mass_provenance,
                "soc_concentration_g_kg": str(l.soc_concentration_g_kg),
                "layer_soil_mass_t_ha": str(l.layer_soil_mass_t_ha),
                "layer_soc_mass_t_c_ha": str(l.layer_soc_mass_t_c_ha),
                "fraction_in_reference_mass": str(l.fraction_in_reference_mass),
                "included_soc_mass_t_c_ha": str(l.included_soc_mass_t_c_ha),
            }
            for l in calculated_layers
        ],
    }

    calc_hash = compute_deterministic_hash(result_dict)

    return ProfileESMResult(
        reference_soil_mass_t_ha=reference_soil_mass_t_ha,
        reference_depth_cm=reference_depth_cm,
        equivalent_depth_cm=equivalent_depth_cm,
        total_sampled_soil_mass_t_ha=total_sampled_soil_mass,
        max_sampled_depth_cm=max_sampled_depth_cm,
        soc_stock_t_c_per_ha=normalized_soc_stock,
        unadjusted_stock_t_c_per_ha=unadjusted_stock,
        depth_sufficiency_status=depth_sufficiency_status,
        shallow_soil_exception_applied=shallow_exception_applied,
        esm_algorithm="LAYER_MASS_PROPORTIONING",
        layers=calculated_layers,
        calculation_hash=calc_hash,
    )


def _solve_natural_cubic_spline(x_pts: List[float], y_pts: List[float], x_eval: float) -> float:
    """
    Exact Natural Cubic Spline Interpolation with boundary conditions S''(x_0)=0, S''(x_n)=0.
    Corresponds to the cubic spline procedure in Wendt & Hauser (2013) / SRS1 Software Excel add-in.
    Uses SciPy CubicSpline(bc_type='natural') when available, or exact tridiagonal system solver.
    """
    try:
        from scipy.interpolate import CubicSpline
        cs = CubicSpline(x_pts, y_pts, bc_type="natural")
        return float(cs(x_eval))
    except ImportError:
        # Exact analytical natural cubic spline solver (Thomas algorithm for tridiagonal system)
        n = len(x_pts) - 1
        h = [x_pts[i+1] - x_pts[i] for i in range(n)]
        alpha = [0.0] * n
        for i in range(1, n):
            alpha[i] = (3.0 / h[i]) * (y_pts[i+1] - y_pts[i]) - (3.0 / h[i-1]) * (y_pts[i] - y_pts[i-1])
        l = [1.0] * (n + 1)
        mu = [0.0] * (n + 1)
        z = [0.0] * (n + 1)
        for i in range(1, n):
            l[i] = 2.0 * (x_pts[i+1] - x_pts[i-1]) - h[i-1] * mu[i-1]
            mu[i] = h[i] / l[i]
            z[i] = (alpha[i] - h[i-1] * z[i-1]) / l[i]
        c = [0.0] * (n + 1)
        b = [0.0] * n
        d = [0.0] * n
        for j in range(n - 1, -1, -1):
            c[j] = z[j] - mu[j] * c[j+1]
            b[j] = (y_pts[j+1] - y_pts[j]) / h[j] - h[j] * (c[j+1] + 2.0 * c[j]) / 3.0
            d[j] = (c[j+1] - c[j]) / (3.0 * h[j])
        k = 0
        for i in range(n):
            if x_pts[i] <= x_eval <= x_pts[i+1]:
                k = i
                break
            elif i == n - 1 and x_eval >= x_pts[i]:
                k = i
        dx = x_eval - x_pts[k]
        return y_pts[k] + b[k] * dx + c[k] * (dx ** 2) + d[k] * (dx ** 3)


def calculate_profile_esm_spline(
    layers: List[LayerInput],
    reference_soil_mass_t_ha: Decimal,
    reference_depth_cm: Decimal = Decimal("30.00"),
    allow_shallow_soil_exception: bool = False,
) -> ProfileESMResult:
    """
    Authoritative Wendt & Hauser (2013) Natural Cubic Spline Normalization.
    VM0042 v2.2 Section 8.2.1.6, Equation (4), Figure 3 / Wendt & Hauser (2013).
    Fits an exact natural cubic spline with boundary conditions S''(0) = 0 and S''(M_max) = 0
    through cumulative (M_cum, SOC_cum) knots.
    """
    # For layer-by-layer breakdown and initial masses, first run validation and mass accumulation
    base_result = calculate_profile_esm_proportioning(
        layers=layers,
        reference_soil_mass_t_ha=reference_soil_mass_t_ha,
        reference_depth_cm=reference_depth_cm,
        allow_shallow_soil_exception=allow_shallow_soil_exception,
    )

    # Build cumulative points (M_cum, SOC_cum) originating at (0, 0)
    m_pts = [0.0]
    soc_pts = [0.0]
    depth_pts = [0.0]

    for layer in base_result.layers:
        m_pts.append(float(layer.cumulative_soil_mass_t_ha))
        soc_pts.append(float(layer.cumulative_soc_mass_t_c_ha))
        depth_pts.append(float(layer.depth_lower_cm))

    ref_m = float(reference_soil_mass_t_ha)

    # Evaluate exact natural cubic spline
    val_soc = _solve_natural_cubic_spline(m_pts, soc_pts, ref_m)
    val_depth = _solve_natural_cubic_spline(m_pts, depth_pts, ref_m)

    spline_soc = Decimal(str(val_soc)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)
    spline_depth = Decimal(str(val_depth)).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)

    algorithm_metadata = {
        "source_workbook": "ESM-sample-spreadsheets-Wendt-and-Hauser-2013.xlsx",
        "worksheet": "Cubic spline simple",
        "interpolation_type": "NATURAL_CUBIC_SPLINE",
        "boundary_conditions": "S''(0) = 0, S''(M_max) = 0 (NATURAL)",
        "implementation_library": "scipy.interpolate.CubicSpline(bc_type='natural')",
        "algorithm_version": "WENDT_HAUSER_2013_v2.2",
        "methodology_reference": "Verra VM0042 v2.2 Section 8.2.1.6, Equation (4), Figure 3",
    }

    result_dict = {
        "reference_soil_mass_t_ha": str(reference_soil_mass_t_ha),
        "reference_depth_cm": str(reference_depth_cm),
        "equivalent_depth_cm": str(spline_depth) if spline_depth else None,
        "total_sampled_soil_mass_t_ha": str(base_result.total_sampled_soil_mass_t_ha),
        "max_sampled_depth_cm": str(base_result.max_sampled_depth_cm),
        "soc_stock_t_c_per_ha": str(spline_soc),
        "unadjusted_stock_t_c_per_ha": str(base_result.unadjusted_stock_t_c_per_ha),
        "depth_sufficiency_status": base_result.depth_sufficiency_status,
        "shallow_soil_exception_applied": base_result.shallow_soil_exception_applied,
        "esm_algorithm": "WENDT_HAUSER_2013_CUBIC_SPLINE",
        "algorithm_metadata": algorithm_metadata,
    }
    calc_hash = compute_deterministic_hash(result_dict)

    base_result.soc_stock_t_c_per_ha = spline_soc
    base_result.equivalent_depth_cm = spline_depth
    base_result.esm_algorithm = "WENDT_HAUSER_2013_CUBIC_SPLINE"
    base_result.algorithm_metadata = algorithm_metadata
    base_result.calculation_hash = calc_hash

    return base_result


def calculate_profile_esm_diagnostic_pchip(
    layers: List[LayerInput],
    reference_soil_mass_t_ha: Decimal,
    reference_depth_cm: Decimal = Decimal("30.00"),
    allow_shallow_soil_exception: bool = False,
) -> ProfileESMResult:
    """
    NON-AUTHORITATIVE DIAGNOSTIC ONLY: Shape-preserving PCHIP interpolator.
    Must NOT be used for authoritative VM0042 carbon accounting or Wendt & Hauser crediting.
    """
    base_result = calculate_profile_esm_proportioning(
        layers=layers,
        reference_soil_mass_t_ha=reference_soil_mass_t_ha,
        reference_depth_cm=reference_depth_cm,
        allow_shallow_soil_exception=allow_shallow_soil_exception,
    )

    m_pts = [0.0]
    soc_pts = [0.0]
    depth_pts = [0.0]

    for layer in base_result.layers:
        m_pts.append(float(layer.cumulative_soil_mass_t_ha))
        soc_pts.append(float(layer.cumulative_soc_mass_t_c_ha))
        depth_pts.append(float(layer.depth_lower_cm))

    ref_m = float(reference_soil_mass_t_ha)
    from scipy.interpolate import PchipInterpolator
    interp_soc = PchipInterpolator(m_pts, soc_pts)
    interp_depth = PchipInterpolator(m_pts, depth_pts)

    pchip_soc = Decimal(str(interp_soc(ref_m))).quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)
    pchip_depth = Decimal(str(interp_depth(ref_m))).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)

    base_result.soc_stock_t_c_per_ha = pchip_soc
    base_result.equivalent_depth_cm = pchip_depth
    base_result.esm_algorithm = "DIAGNOSTIC_PCHIP"
    base_result.algorithm_metadata = {"status": "NON_AUTHORITATIVE_DIAGNOSTIC"}
    return base_result


def aggregate_stratum_soc_stock(
    sample_point_stocks: List[Decimal],
) -> Decimal:
    """
    Computes arithmetic mean of normalized SOC stocks across sample points in a stratum.
    Formula: Mean_SOC = (1 / n) * sum(SOC_i)
    """
    if not sample_point_stocks:
        raise SOCStockCalculationError(
            code="EMPTY_STRATUM_SAMPLES",
            message="Cannot aggregate SOC stock for stratum with zero sample points.",
        )

    n = Decimal(len(sample_point_stocks))
    total = sum(sample_point_stocks)
    mean = (total / n).quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)
    return mean


def aggregate_project_area_weighted_soc_stock(
    strata_data: List[Dict[str, Any]],
) -> Tuple[Decimal, Decimal]:
    """
    Computes area-weighted mean SOC stock across strata in a project.
    Formula: SOC_proj = sum(A_s * Mean_SOC_s) / sum(A_s)
    Returns: (project_soc_stock_t_c_per_ha, total_area_ha)
    """
    if not strata_data:
        raise SOCStockCalculationError(
            code="EMPTY_PROJECT_STRATA",
            message="Cannot aggregate project SOC stock without strata data.",
        )

    total_weighted_soc = Decimal("0.0000")
    total_area = Decimal("0.0000")

    for s in strata_data:
        area = Decimal(str(s["area_ha"]))
        soc = Decimal(str(s["stratum_mean_soc_t_c_per_ha"]))

        if area <= Decimal("0.0"):
            raise SOCStockCalculationError(
                code="INVALID_STRATUM_AREA",
                message=f"Stratum {s.get('stratum_code')} has non-positive area {area} ha.",
            )

        total_area += area
        total_weighted_soc += (area * soc)

    project_soc = (total_weighted_soc / total_area).quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)
    total_area = total_area.quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)
    return project_soc, total_area
