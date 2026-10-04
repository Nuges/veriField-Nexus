"""
=============================================================================
VeriField Nexus — Component-Level Quantification Route & Tool Resolver
=============================================================================
Decomposes VM0042 v2.2 agricultural GHG sources and carbon pools into
canonical component-level routes pursuant to Table 5.
Enforces authoritative gating for:
- VMD0053 v2.1 (Biogeochemical model calibration & validation)
- VT0014 v1.0 + 16 Oct 2025 Corrections & Clarifications (Digital Soil Mapping)
- CDM AR-TOOL14 (Woody biomass estimation where included)
=============================================================================
"""

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class QuantificationApproach(str, Enum):
    APPROACH_1 = "APPROACH_1"      # Measure and Model (Biogeochemical simulation + periodic measurement)
    APPROACH_2 = "APPROACH_2"      # Measure and Re-measure (Direct soil measurement + baseline control sites)
    APPROACH_3 = "APPROACH_3"      # Default emission factors (Tier 1/2 equations)
    EXTERNAL_TOOL = "EXTERNAL_TOOL"  # Verified external methodology tool (e.g. CDM AR-TOOL14, fossil fuel tool)


class DSMPathwayMode(str, Enum):
    DSM_NOT_SELECTED = "DSM_NOT_SELECTED"
    DSM_QA1_INITIALIZATION = "DSM_QA1_INITIALIZATION"
    DSM_QA1_TRUE_UP = "DSM_QA1_TRUE_UP"
    DSM_QA2_SOC_MAPPING = "DSM_QA2_SOC_MAPPING"


class VM0042Table5Component(str, Enum):
    # CO2 Sources and Pools
    CO2_SOC = "CO2_SOC"
    CO2_WOODY_BIOMASS = "CO2_WOODY_BIOMASS"
    CO2_FOSSIL_FUEL = "CO2_FOSSIL_FUEL"
    CO2_LIMING = "CO2_LIMING"

    # CH4 Sources
    CH4_SOIL_METHANOGENESIS = "CH4_SOIL_METHANOGENESIS"
    CH4_ENTERIC_FERMENTATION = "CH4_ENTERIC_FERMENTATION"
    CH4_MANURE_DEPOSITION = "CH4_MANURE_DEPOSITION"  # Canonical VM0042 v2.2 Table 5: Methane emissions from manure deposition
    CH4_MANURE_MANAGEMENT = "CH4_MANURE_DEPOSITION"  # Internal legacy alias mapped to canonical source
    CH4_BIOMASS_BURNING = "CH4_BIOMASS_BURNING"

    # N2O Sources
    N2O_DIRECT_SOIL = "N2O_DIRECT_SOIL"
    N2O_INDIRECT_ATMOSPHERIC = "N2O_INDIRECT_ATMOSPHERIC"
    N2O_INDIRECT_LEACHING = "N2O_INDIRECT_LEACHING"
    N2O_NITROGEN_FIXING_SPECIES = "N2O_NITROGEN_FIXING_SPECIES"
    N2O_MANURE_DEPOSITION = "N2O_MANURE_DEPOSITION"
    N2O_BIOMASS_BURNING = "N2O_BIOMASS_BURNING"

    # Leakage
    LEAKAGE_PRODUCTION_DECLINE = "LEAKAGE_PRODUCTION_DECLINE"


# Exact canonical 15-component Table 5 inventory per VM0042 v2.2
CANONICAL_VM0042_TABLE_5_COMPONENTS: List[str] = [
    # CO2 Sources and Pools (4)
    "CO2_SOC",
    "CO2_WOODY_BIOMASS",
    "CO2_FOSSIL_FUEL",
    "CO2_LIMING",
    # CH4 Sources (4 canonical)
    "CH4_SOIL_METHANOGENESIS",
    "CH4_ENTERIC_FERMENTATION",
    "CH4_MANURE_DEPOSITION",
    "CH4_BIOMASS_BURNING",
    # N2O Sources (6 canonical)
    "N2O_DIRECT_SOIL",
    "N2O_INDIRECT_ATMOSPHERIC",
    "N2O_INDIRECT_LEACHING",
    "N2O_NITROGEN_FIXING_SPECIES",
    "N2O_MANURE_DEPOSITION",
    "N2O_BIOMASS_BURNING",
    # Leakage (1)
    "LEAKAGE_PRODUCTION_DECLINE",
]

# Backward compatibility alias
GHGComponent = VM0042Table5Component

# Explicit mapping from internal/legacy broader terms to canonical VM0042 Table 5 sources (§9)
INTERNAL_TO_METHODOLOGY_COMPONENT_MAP: Dict[str, str] = {
    "CH4_MANURE_MANAGEMENT": "CH4_MANURE_DEPOSITION",
}


# Official VM0042 v2.2 Table 5 permitted approaches per component
TABLE_5_PERMITTED_APPROACHES: Dict[str, Set[str]] = {
    VM0042Table5Component.CO2_SOC.value: {
        QuantificationApproach.APPROACH_1.value,
        QuantificationApproach.APPROACH_2.value,
    },
    VM0042Table5Component.CO2_WOODY_BIOMASS.value: {
        QuantificationApproach.EXTERNAL_TOOL.value,
    },
    VM0042Table5Component.CO2_FOSSIL_FUEL.value: {
        QuantificationApproach.APPROACH_3.value,
        QuantificationApproach.EXTERNAL_TOOL.value,
    },
    VM0042Table5Component.CO2_LIMING.value: {
        QuantificationApproach.APPROACH_3.value,
    },
    VM0042Table5Component.CH4_SOIL_METHANOGENESIS.value: {
        QuantificationApproach.APPROACH_1.value,
        QuantificationApproach.APPROACH_3.value,
    },
    VM0042Table5Component.CH4_ENTERIC_FERMENTATION.value: {
        QuantificationApproach.APPROACH_1.value,
        QuantificationApproach.APPROACH_3.value,
    },
    VM0042Table5Component.CH4_MANURE_DEPOSITION.value: {
        QuantificationApproach.APPROACH_1.value,
        QuantificationApproach.APPROACH_3.value,
    },
    "CH4_MANURE_MANAGEMENT": {
        QuantificationApproach.APPROACH_1.value,
        QuantificationApproach.APPROACH_3.value,
    },
    VM0042Table5Component.CH4_BIOMASS_BURNING.value: {
        QuantificationApproach.APPROACH_3.value,
    },
    VM0042Table5Component.N2O_DIRECT_SOIL.value: {
        QuantificationApproach.APPROACH_1.value,
        QuantificationApproach.APPROACH_3.value,
    },
    VM0042Table5Component.N2O_INDIRECT_ATMOSPHERIC.value: {
        QuantificationApproach.APPROACH_1.value,
        QuantificationApproach.APPROACH_3.value,
    },
    VM0042Table5Component.N2O_INDIRECT_LEACHING.value: {
        QuantificationApproach.APPROACH_1.value,
        QuantificationApproach.APPROACH_3.value,
    },
    VM0042Table5Component.N2O_NITROGEN_FIXING_SPECIES.value: {
        QuantificationApproach.APPROACH_1.value,
        QuantificationApproach.APPROACH_3.value,
    },
    VM0042Table5Component.N2O_MANURE_DEPOSITION.value: {
        QuantificationApproach.APPROACH_1.value,
        QuantificationApproach.APPROACH_3.value,
    },
    VM0042Table5Component.N2O_BIOMASS_BURNING.value: {
        QuantificationApproach.APPROACH_3.value,
    },
    VM0042Table5Component.LEAKAGE_PRODUCTION_DECLINE.value: {
        QuantificationApproach.APPROACH_3.value,
    },
}


@dataclass(frozen=True)
class ComponentRouteDetail:
    component: str
    ghg_type: str  # CO2, CH4, N2O, LEAKAGE
    subtype: Optional[str]
    quantification_approach: str
    applicable_module: Optional[str]
    data_requirements: List[str]
    model_requirements: List[str]
    measurement_requirements: List[str]
    is_model_driven: bool
    is_included_in_boundary: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RouteMapResolution:
    component_routes: Dict[str, ComponentRouteDetail]
    table5_complete: bool
    table5_validation_errors: List[str]
    requires_vmd0053: bool
    vmd0053_status: str  # REQUIRED, NOT_APPLICABLE, COMPLETE, BLOCKED
    vmd0053_notes: str
    requires_vt0014: bool
    dsm_pathway_mode: str  # DSM_NOT_SELECTED, DSM_QA1_INITIALIZATION, DSM_QA1_TRUE_UP, DSM_QA2_SOC_MAPPING
    vt0014_status: str   # REQUIRED, NOT_APPLICABLE, COMPLETE, BLOCKED, RULESET_INCOMPLETE
    vt0014_notes: str
    includes_woody_biomass: bool
    woody_biomass_status: str
    soc_approach: str
    canonical_component_count: int = 15

    @property
    def canonical_component_routes(self) -> Dict[str, ComponentRouteDetail]:
        return {
            k: self.component_routes[k]
            for k in CANONICAL_VM0042_TABLE_5_COMPONENTS
            if k in self.component_routes
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_routes": {k: v.to_dict() for k, v in self.component_routes.items()},
            "canonical_component_routes": {k: v.to_dict() for k, v in self.canonical_component_routes.items()},
            "canonical_component_count": len(self.canonical_component_routes),
            "table5_complete": self.table5_complete,
            "table5_validation_errors": self.table5_validation_errors,
            "requires_vmd0053": self.requires_vmd0053,
            "vmd0053_status": self.vmd0053_status,
            "vmd0053_notes": self.vmd0053_notes,
            "requires_vt0014": self.requires_vt0014,
            "dsm_pathway_mode": self.dsm_pathway_mode,
            "vt0014_status": self.vt0014_status,
            "vt0014_notes": self.vt0014_notes,
            "includes_woody_biomass": self.includes_woody_biomass,
            "woody_biomass_status": self.woody_biomass_status,
            "soc_approach": self.soc_approach,
        }


def validate_table5_completeness(routes: Dict[str, ComponentRouteDetail]) -> Tuple[bool, List[str]]:
    """
    Validates that every official VM0042 Table 5 component is present exactly once
    and that assigned quantification approaches strictly comply with Table 5 rules.
    """
    errors: List[str] = []
    seen: Set[str] = set()

    for comp in VM0042Table5Component:
        c_val = comp.value
        if c_val not in routes:
            errors.append(f"MISSING_TABLE_5_SOURCE: Component '{c_val}' is absent from route map.")
            continue

        if c_val in seen:
            errors.append(f"DUPLICATE_TABLE_5_SOURCE: Component '{c_val}' appears multiple times.")
        seen.add(c_val)

        route = routes[c_val]
        assigned_approach = route.quantification_approach
        permitted = TABLE_5_PERMITTED_APPROACHES.get(c_val, set())

        if assigned_approach not in permitted:
            errors.append(
                f"IMPERMISSIBLE_APPROACH: Component '{c_val}' assigned approach '{assigned_approach}'. "
                f"Table 5 permits only: {sorted(list(permitted))}."
            )

    return (len(errors) == 0), errors


def resolve_quantification_routes(
    project_config: Dict[str, Any],
    sampling_plan_config: Optional[Dict[str, Any]] = None,
    model_run_evidence: Optional[Dict[str, Any]] = None,
    dsm_run_evidence: Optional[Dict[str, Any]] = None,
) -> RouteMapResolution:
    """
    Resolves component-level quantification approaches and tool applicability
    pursuant to the complete VM0042 v2.2 Table 5 inventory.
    """
    p_cfg = project_config or {}
    sp_cfg = sampling_plan_config or {}
    meth_meta = p_cfg.get("locked_methodology_version") or p_cfg

    # 1. Primary SOC Approach (§8, §9)
    raw_soc_approach = (meth_meta.get("quantification_approach") or "APPROACH_2").upper()
    if raw_soc_approach in ("APPROACH_1", "MEASURE_AND_MODEL", "MODELING"):
        soc_approach = QuantificationApproach.APPROACH_1.value
    else:
        soc_approach = QuantificationApproach.APPROACH_2.value

    # Check boundaries and activity subtypes
    has_woody = bool(p_cfg.get("include_woody_biomass", False))
    has_rice = bool(p_cfg.get("has_paddy_rice", False) or "RICE" in str(p_cfg.get("crop_types", [])).upper())
    has_livestock = bool(p_cfg.get("has_livestock", False) or p_cfg.get("include_enteric_fermentation", False))
    has_burning = bool(p_cfg.get("has_biomass_burning", False))
    has_legumes = bool(p_cfg.get("has_nitrogen_fixing_crops", True))

    routes: Dict[str, ComponentRouteDetail] = {}

    # ─────────────────────────────────────────────────────────────────────────
    # CO2 Sources and Pools
    # ─────────────────────────────────────────────────────────────────────────
    # 1. Soil Organic Carbon
    if soc_approach == QuantificationApproach.APPROACH_1.value:
        routes[VM0042Table5Component.CO2_SOC.value] = ComponentRouteDetail(
            component=VM0042Table5Component.CO2_SOC.value,
            ghg_type="CO2",
            subtype=None,
            quantification_approach=QuantificationApproach.APPROACH_1.value,
            applicable_module="VMD0053_V2.1",
            data_requirements=["Soil physical properties", "Weather time-series", "Management history time-series", "Calibration SOC samples"],
            model_requirements=["Process-based model (e.g. DayCent, DNDC)", "VMD0053 calibration/validation report", "IME sign-off"],
            measurement_requirements=["Periodic soil sampling on project sites to validate model trajectory"],
            is_model_driven=True,
            is_included_in_boundary=True,
        )
    else:
        routes[VM0042Table5Component.CO2_SOC.value] = ComponentRouteDetail(
            component=VM0042Table5Component.CO2_SOC.value,
            ghg_type="CO2",
            subtype=None,
            quantification_approach=QuantificationApproach.APPROACH_2.value,
            applicable_module="VM0042_DIRECT_ESM",
            data_requirements=["Baseline soil samples", "Monitoring soil samples", "Bulk density / core volume", "Depth intervals"],
            model_requirements=[],
            measurement_requirements=["Direct soil sampling on project and linked baseline control sites normalized on ESM basis"],
            is_model_driven=False,
            is_included_in_boundary=True,
        )

    # 2. Woody Biomass (CDM AR-TOOL14) (§12)
    routes[VM0042Table5Component.CO2_WOODY_BIOMASS.value] = ComponentRouteDetail(
        component=VM0042Table5Component.CO2_WOODY_BIOMASS.value,
        ghg_type="CO2",
        subtype="SHRUB_AND_TREE_BIOMASS" if has_woody else None,
        quantification_approach=QuantificationApproach.EXTERNAL_TOOL.value,
        applicable_module="CDM_AR_TOOL14" if has_woody else None,
        data_requirements=["Allometric equations", "Stem diameter / crown area measurements", "Species inventory"] if has_woody else [],
        model_requirements=[],
        measurement_requirements=["Field dendrometric plots or approved airborne lidar inventory"] if has_woody else [],
        is_model_driven=False,
        is_included_in_boundary=has_woody,
    )

    # 3. Fossil Fuel CO2
    fuel_app = (p_cfg.get("fossil_fuel_approach") or "APPROACH_3").upper()
    routes[VM0042Table5Component.CO2_FOSSIL_FUEL.value] = ComponentRouteDetail(
        component=VM0042Table5Component.CO2_FOSSIL_FUEL.value,
        ghg_type="CO2",
        subtype="FARM_MACHINERY_AND_IRRIGATION",
        quantification_approach=fuel_app if fuel_app in (QuantificationApproach.APPROACH_3.value, QuantificationApproach.EXTERNAL_TOOL.value) else QuantificationApproach.APPROACH_3.value,
        applicable_module="IPCC_2006_TIER_1",
        data_requirements=["Fuel consumption logs (diesel, gasoline, electricity)", "Fuel emission factors"],
        model_requirements=[],
        measurement_requirements=["Operational fuel meter / invoice audit logs"],
        is_model_driven=False,
        is_included_in_boundary=True,
    )

    # 4. Liming CO2
    routes[VM0042Table5Component.CO2_LIMING.value] = ComponentRouteDetail(
        component=VM0042Table5Component.CO2_LIMING.value,
        ghg_type="CO2",
        subtype="AGRICULTURAL_LIME",
        quantification_approach=QuantificationApproach.APPROACH_3.value,
        applicable_module="VM0042_LIMING_STOICHIOMETRY",
        data_requirements=["Liming application mass", "Lime purity factor (CaCO3 / MgCO3 fraction)"],
        model_requirements=[],
        measurement_requirements=["Delivery receipts and farm application records"],
        is_model_driven=False,
        is_included_in_boundary=True,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # CH4 Sources (§11)
    # ─────────────────────────────────────────────────────────────────────────
    # 5. Soil Methanogenesis (Methodology Canonical Name; rice cultivation as subtype)
    ch4_app = QuantificationApproach.APPROACH_1.value if soc_approach == QuantificationApproach.APPROACH_1.value else QuantificationApproach.APPROACH_3.value
    routes[VM0042Table5Component.CH4_SOIL_METHANOGENESIS.value] = ComponentRouteDetail(
        component=VM0042Table5Component.CH4_SOIL_METHANOGENESIS.value,
        ghg_type="CH4",
        subtype="RICE_CULTIVATION" if has_rice else "UPLAND_SOILS_ZERO_FLUX",
        quantification_approach=ch4_app,
        applicable_module="VMD0053_V2.1" if (ch4_app == QuantificationApproach.APPROACH_1.value and has_rice) else "IPCC_2019_RICE_FLOODING",
        data_requirements=["Water regime duration", "Organic amendment rates", "Cultivar maturity duration"] if has_rice else [],
        model_requirements=["Anaerobic methane simulation"] if (ch4_app == QuantificationApproach.APPROACH_1.value and has_rice) else [],
        measurement_requirements=["Water level log and field draining records"] if has_rice else [],
        is_model_driven=(ch4_app == QuantificationApproach.APPROACH_1.value and has_rice),
        is_included_in_boundary=has_rice,
    )

    # 6. Enteric Fermentation
    routes[VM0042Table5Component.CH4_ENTERIC_FERMENTATION.value] = ComponentRouteDetail(
        component=VM0042Table5Component.CH4_ENTERIC_FERMENTATION.value,
        ghg_type="CH4",
        subtype="GRAZING_RUMINANTS" if has_livestock else None,
        quantification_approach=QuantificationApproach.APPROACH_3.value,
        applicable_module="IPCC_2019_TIER_2_LIVESTOCK" if has_livestock else None,
        data_requirements=["Livestock head count", "Average weight", "Feed intake and quality"] if has_livestock else [],
        model_requirements=[],
        measurement_requirements=["Herd registry and feed purchase documentation"] if has_livestock else [],
        is_model_driven=False,
        is_included_in_boundary=has_livestock,
    )

    # 7. Manure Deposition / Manure Management (CH4) (§9)
    # VM0042 v2.2 Table 5 exact methodology source: Methane emissions from manure deposition
    ch4_manure_detail = ComponentRouteDetail(
        component=VM0042Table5Component.CH4_MANURE_DEPOSITION.value,
        ghg_type="CH4",
        subtype="MANURE_DEPOSITION_ON_PASTURE_AND_MANAGEMENT" if has_livestock else None,
        quantification_approach=QuantificationApproach.APPROACH_3.value,
        applicable_module="IPCC_2019_MANURE_TIER_2" if has_livestock else None,
        data_requirements=["Manure deposition and management system type", "Storage duration", "Temperature"] if has_livestock else [],
        model_requirements=[],
        measurement_requirements=["Storage facility inspection logs and herd distribution records"] if has_livestock else [],
        is_model_driven=False,
        is_included_in_boundary=has_livestock,
    )
    routes[VM0042Table5Component.CH4_MANURE_DEPOSITION.value] = ch4_manure_detail
    routes["CH4_MANURE_MANAGEMENT"] = ch4_manure_detail

    # 8. Biomass Burning (CH4)
    routes[VM0042Table5Component.CH4_BIOMASS_BURNING.value] = ComponentRouteDetail(
        component=VM0042Table5Component.CH4_BIOMASS_BURNING.value,
        ghg_type="CH4",
        subtype="RESIDUE_BURNING" if has_burning else None,
        quantification_approach=QuantificationApproach.APPROACH_3.value,
        applicable_module="IPCC_2006_BURNING" if has_burning else None,
        data_requirements=["Burned area", "Fuel biomass loading", "Combustion completeness"] if has_burning else [],
        model_requirements=[],
        measurement_requirements=["Fire incident logs and remote sensing burn scar verification"] if has_burning else [],
        is_model_driven=False,
        is_included_in_boundary=has_burning,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # N2O Sources
    # ─────────────────────────────────────────────────────────────────────────
    # 9. Direct Soil N2O (Nitrogen Fertilizers)
    n2o_app = QuantificationApproach.APPROACH_1.value if soc_approach == QuantificationApproach.APPROACH_1.value else QuantificationApproach.APPROACH_3.value
    routes[VM0042Table5Component.N2O_DIRECT_SOIL.value] = ComponentRouteDetail(
        component=VM0042Table5Component.N2O_DIRECT_SOIL.value,
        ghg_type="N2O",
        subtype="SYNTHETIC_AND_ORGANIC_FERTILIZER",
        quantification_approach=n2o_app,
        applicable_module="VMD0053_V2.1" if n2o_app == QuantificationApproach.APPROACH_1.value else "IPCC_2019_REFINEMENT_TIER_1",
        data_requirements=["Synthetic and organic N application rates", "Soil texture", "Precipitation"],
        model_requirements=["Biogeochemical nitrification/denitrification simulation"] if n2o_app == QuantificationApproach.APPROACH_1.value else [],
        measurement_requirements=["Fertilizer purchase and application logs"],
        is_model_driven=(n2o_app == QuantificationApproach.APPROACH_1.value),
        is_included_in_boundary=True,
    )

    # 10. Indirect N2O - Atmospheric Deposition
    routes[VM0042Table5Component.N2O_INDIRECT_ATMOSPHERIC.value] = ComponentRouteDetail(
        component=VM0042Table5Component.N2O_INDIRECT_ATMOSPHERIC.value,
        ghg_type="N2O",
        subtype="VOLATILIZATION_NH3_NOX",
        quantification_approach=n2o_app,
        applicable_module="VMD0053_V2.1" if n2o_app == QuantificationApproach.APPROACH_1.value else "IPCC_2019_EF4",
        data_requirements=["Fertilizer N type", "Volatilization fractions FracGASF / FracGASM"],
        model_requirements=["Gas emission flux simulation"] if n2o_app == QuantificationApproach.APPROACH_1.value else [],
        measurement_requirements=["Application records"],
        is_model_driven=(n2o_app == QuantificationApproach.APPROACH_1.value),
        is_included_in_boundary=True,
    )

    # 11. Indirect N2O - Leaching and Runoff
    routes[VM0042Table5Component.N2O_INDIRECT_LEACHING.value] = ComponentRouteDetail(
        component=VM0042Table5Component.N2O_INDIRECT_LEACHING.value,
        ghg_type="N2O",
        subtype="NITRATE_LEACHING",
        quantification_approach=n2o_app,
        applicable_module="VMD0053_V2.1" if n2o_app == QuantificationApproach.APPROACH_1.value else "IPCC_2019_EF5",
        data_requirements=["Water balance", "Leaching fraction FracLEACH"],
        model_requirements=["Hydrological drainage simulation"] if n2o_app == QuantificationApproach.APPROACH_1.value else [],
        measurement_requirements=["Irrigation and rainfall logs"],
        is_model_driven=(n2o_app == QuantificationApproach.APPROACH_1.value),
        is_included_in_boundary=True,
    )

    # 12. Nitrogen-Fixing Species
    routes[VM0042Table5Component.N2O_NITROGEN_FIXING_SPECIES.value] = ComponentRouteDetail(
        component=VM0042Table5Component.N2O_NITROGEN_FIXING_SPECIES.value,
        ghg_type="N2O",
        subtype="LEGUMINOUS_CROPS_AND_FORAGES" if has_legumes else None,
        quantification_approach=n2o_app,
        applicable_module="VMD0053_V2.1" if n2o_app == QuantificationApproach.APPROACH_1.value else "IPCC_2019_TIER_1_RESIDUES",
        data_requirements=["Legume harvest yield", "Dry matter fraction", "Residue N content"] if has_legumes else [],
        model_requirements=["Biological N fixation simulation"] if (n2o_app == QuantificationApproach.APPROACH_1.value and has_legumes) else [],
        measurement_requirements=["Harvest and acreage records"] if has_legumes else [],
        is_model_driven=(n2o_app == QuantificationApproach.APPROACH_1.value and has_legumes),
        is_included_in_boundary=has_legumes,
    )

    # 13. Manure Deposition on Pastures (N2O)
    routes[VM0042Table5Component.N2O_MANURE_DEPOSITION.value] = ComponentRouteDetail(
        component=VM0042Table5Component.N2O_MANURE_DEPOSITION.value,
        ghg_type="N2O",
        subtype="PRP_PASTURE_RANGE_PADDOCK" if has_livestock else None,
        quantification_approach=n2o_app,
        applicable_module="VMD0053_V2.1" if n2o_app == QuantificationApproach.APPROACH_1.value else "IPCC_2019_EF3PRP",
        data_requirements=["Grazing days", "Animal head count", "Excretion rates"] if has_livestock else [],
        model_requirements=["Excreta N deposition dynamics"] if (n2o_app == QuantificationApproach.APPROACH_1.value and has_livestock) else [],
        measurement_requirements=["Pasture rotation logs"] if has_livestock else [],
        is_model_driven=(n2o_app == QuantificationApproach.APPROACH_1.value and has_livestock),
        is_included_in_boundary=has_livestock,
    )

    # 14. Biomass Burning (N2O)
    routes[VM0042Table5Component.N2O_BIOMASS_BURNING.value] = ComponentRouteDetail(
        component=VM0042Table5Component.N2O_BIOMASS_BURNING.value,
        ghg_type="N2O",
        subtype="RESIDUE_BURNING" if has_burning else None,
        quantification_approach=QuantificationApproach.APPROACH_3.value,
        applicable_module="IPCC_2006_BURNING" if has_burning else None,
        data_requirements=["Burned area", "Biomass loading", "N2O emission ratio"] if has_burning else [],
        model_requirements=[],
        measurement_requirements=["Fire activity logs"] if has_burning else [],
        is_model_driven=False,
        is_included_in_boundary=has_burning,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Leakage
    # ─────────────────────────────────────────────────────────────────────────
    # 15. Leakage from Production Decline (June 2026 C&C mandatory formula)
    routes[VM0042Table5Component.LEAKAGE_PRODUCTION_DECLINE.value] = ComponentRouteDetail(
        component=VM0042Table5Component.LEAKAGE_PRODUCTION_DECLINE.value,
        ghg_type="LEAKAGE",
        subtype="ACTIVITY_SHIFTING_PRODUCTION_DISPLACEMENT",
        quantification_approach=QuantificationApproach.APPROACH_3.value,
        applicable_module="VM0042_CC_20260611_LEAKAGE",
        data_requirements=["Project crop yields", "Baseline control crop yields", "Displacement emission factor"],
        model_requirements=[],
        measurement_requirements=["Annual harvest logs and weighbridge receipts"],
        is_model_driven=False,
        is_included_in_boundary=True,
    )

    # Table 5 Completeness Validation (§10, §37)
    table5_ok, table5_errors = validate_table5_completeness(routes)

    # ─────────────────────────────────────────────────────────────────────────
    # VMD0053 Gating (§8, §12, §13)
    # ─────────────────────────────────────────────────────────────────────────
    requires_vmd0053 = any(r.is_model_driven for r in routes.values())
    if not requires_vmd0053:
        vmd0053_status = "NOT_APPLICABLE"
        vmd0053_notes = "Project utilizes direct measurement (Quantification Approach 2); VMD0053 model calibration is not applicable."
    else:
        has_model_evidence = False
        if model_run_evidence:
            has_ime = bool(model_run_evidence.get("independent_expert_report"))
            has_validation = bool(model_run_evidence.get("validation_report"))
            has_model_id = bool(model_run_evidence.get("model_identifier"))
            has_model_evidence = has_ime and has_validation and has_model_id

        if has_model_evidence:
            vmd0053_status = "COMPLETE"
            vmd0053_notes = f"VMD0053 v2.1 compliance established for model '{model_run_evidence.get('model_identifier')}'; IME report and validation certified."
        else:
            vmd0053_status = "BLOCKED"
            vmd0053_notes = "Quantification Approach 1 configured but required VMD0053 v2.1 biogeochemical model validation/IME evidence is missing or incomplete."

    # ─────────────────────────────────────────────────────────────────────────
    # VT0014 Gating (§14, §15, §41)
    # ─────────────────────────────────────────────────────────────────────────
    # Resolve DSM Pathway Mode
    raw_dsm_mode = str(
        p_cfg.get("dsm_pathway_mode")
        or sp_cfg.get("dsm_pathway_mode")
        or ("VT0014_DSM" if (p_cfg.get("use_digital_soil_mapping") or sp_cfg.get("spatial_interpolation_method") == "VT0014_DSM") else "DSM_NOT_SELECTED")
    ).upper()

    if raw_dsm_mode in ("DSM_NOT_SELECTED", "NONE", "FALSE", "DIRECT_SAMPLING"):
        dsm_mode = DSMPathwayMode.DSM_NOT_SELECTED.value
    elif raw_dsm_mode in ("DSM_QA1_INITIALIZATION", "QA1_INITIALIZATION", "INITIALIZATION"):
        dsm_mode = DSMPathwayMode.DSM_QA1_INITIALIZATION.value
    elif raw_dsm_mode in ("DSM_QA1_TRUE_UP", "QA1_TRUE_UP", "TRUE_UP"):
        dsm_mode = DSMPathwayMode.DSM_QA1_TRUE_UP.value
    elif raw_dsm_mode in ("DSM_QA2_SOC_MAPPING", "QA2_MAPPING", "QA2_SOC_MAPPING", "MAPPED_PREDICTIONS", "VT0014_DSM"):
        dsm_mode = DSMPathwayMode.DSM_QA2_SOC_MAPPING.value
    else:
        dsm_mode = DSMPathwayMode.DSM_NOT_SELECTED.value

    requires_vt0014 = (dsm_mode != DSMPathwayMode.DSM_NOT_SELECTED.value)

    if not requires_vt0014:
        vt0014_status = "NOT_APPLICABLE"
        vt0014_notes = "Direct measured SOC without DSM configured; VT0014 is not applicable."
    else:
        # Check VT0014 C&C lock (16 October 2025 C&C) (§15, §41)
        vt0014_meta = p_cfg.get("vt0014_configuration") or {}
        cc_applied = (
            str(vt0014_meta.get("corrections_clarifications_version") or "").strip() == "2025-10-16"
            or bool(p_cfg.get("has_vt0014_october_2025_cc"))
            or bool(dsm_run_evidence and dsm_run_evidence.get("has_october_2025_cc"))
        )

        if not cc_applied:
            vt0014_status = "RULESET_INCOMPLETE"
            vt0014_notes = "VT0014 Digital Soil Mapping selected, but mandatory 16 October 2025 Corrections & Clarifications are not applied."
        else:
            has_dsm_evidence = False
            if dsm_run_evidence:
                pts_count = int(dsm_run_evidence.get("sample_points_count", 0))
                has_uncert = bool(dsm_run_evidence.get("spatial_uncertainty_mapped"))
                has_metrics = bool(dsm_run_evidence.get("metrics"))
                has_dsm_evidence = pts_count >= 3 and has_uncert and has_metrics

            if has_dsm_evidence:
                vt0014_status = "COMPLETE"
                vt0014_notes = f"VT0014 v1.0 (with 16 Oct 2025 C&C) certified under pathway '{dsm_mode}' with {dsm_run_evidence.get('sample_points_count')} points and uncertainty maps."
            else:
                vt0014_status = "BLOCKED"
                vt0014_notes = f"VT0014 Digital Soil Mapping pathway '{dsm_mode}' configured, but required validation evidence (min 3 points, spatial uncertainty map, performance metrics) is missing or incomplete."

    # ─────────────────────────────────────────────────────────────────────────
    # Woody Biomass Tool Readiness (§12)
    # ─────────────────────────────────────────────────────────────────────────
    if not has_woody:
        woody_status = "NOT_APPLICABLE"
    else:
        wb_evidence = p_cfg.get("woody_biomass_evidence") or {}
        if wb_evidence.get("cdm_ar_tool14_applied"):
            woody_status = "COMPLETE"
        else:
            woody_status = "INCOMPLETE"

    return RouteMapResolution(
        component_routes=routes,
        table5_complete=table5_ok,
        table5_validation_errors=table5_errors,
        requires_vmd0053=requires_vmd0053,
        vmd0053_status=vmd0053_status,
        vmd0053_notes=vmd0053_notes,
        requires_vt0014=requires_vt0014,
        dsm_pathway_mode=dsm_mode,
        vt0014_status=vt0014_status,
        vt0014_notes=vt0014_notes,
        includes_woody_biomass=has_woody,
        woody_biomass_status=woody_status,
        soc_approach=soc_approach,
    )
