"""
VeriField Nexus — Canonical Operating Sectors Platform Taxonomy
Authoritative, centralized definition of the 5 canonical operating sectors.
Platform taxonomy is NOT derived from database rows, test fixtures, or methodology families.

Canonical Sectors:
1. COOKSTOVES -> Clean Cookstoves
2. HYBRID_ENERGY -> Hybrid Energy & Mini-grids
3. BIOCHAR -> Biochar Carbon Removal
4. EV_MOBILITY -> EV Mobility
5. AGRICULTURE_LAND_USE -> Agriculture & Land Use
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid


class CanonicalSector(str, Enum):
    COOKSTOVES = "COOKSTOVES"
    HYBRID_ENERGY = "HYBRID_ENERGY"
    BIOCHAR = "BIOCHAR"
    EV_MOBILITY = "EV_MOBILITY"
    AGRICULTURE_LAND_USE = "AGRICULTURE_LAND_USE"


CANONICAL_SECTOR_CODES: List[str] = [
    CanonicalSector.COOKSTOVES.value,
    CanonicalSector.HYBRID_ENERGY.value,
    CanonicalSector.BIOCHAR.value,
    CanonicalSector.EV_MOBILITY.value,
    CanonicalSector.AGRICULTURE_LAND_USE.value,
]

CANONICAL_SECTOR_SET: Set[str] = set(CANONICAL_SECTOR_CODES)

CANONICAL_SECTOR_LABELS: Dict[CanonicalSector, str] = {
    CanonicalSector.COOKSTOVES: "Clean Cookstoves",
    CanonicalSector.HYBRID_ENERGY: "Hybrid Energy & Mini-grids",
    CanonicalSector.BIOCHAR: "Biochar Carbon Removal",
    CanonicalSector.EV_MOBILITY: "EV Mobility",
    CanonicalSector.AGRICULTURE_LAND_USE: "Agriculture & Land Use",
}

CANONICAL_SECTOR_ORDER: List[CanonicalSector] = [
    CanonicalSector.COOKSTOVES,
    CanonicalSector.HYBRID_ENERGY,
    CanonicalSector.BIOCHAR,
    CanonicalSector.EV_MOBILITY,
    CanonicalSector.AGRICULTURE_LAND_USE,
]

# Known PostgreSQL UUIDs for canonical sectors in methodology_families
CANONICAL_SECTOR_UUID_MAP: Dict[str, CanonicalSector] = {
    "ab748cb8-3b7c-4e07-aec7-d1dc5f3dcf3a": CanonicalSector.COOKSTOVES,
    "15fa60cc-d06a-4ef1-ae14-0359e1bd3674": CanonicalSector.HYBRID_ENERGY,
    "d77b6543-f0f1-4784-a840-cd77e0876a91": CanonicalSector.BIOCHAR,
    "ab17ade7-8938-44b1-a24d-bc797a65e056": CanonicalSector.EV_MOBILITY,
    "9a7a4370-71e6-44f5-9870-975823b8ccb9": CanonicalSector.AGRICULTURE_LAND_USE,
}

# Explicit aliases that safely map to canonical sectors
_CANONICAL_ALIASES: Dict[str, CanonicalSector] = {
    # Cookstoves
    "cookstoves": CanonicalSector.COOKSTOVES,
    "cookstove": CanonicalSector.COOKSTOVES,
    "clean_cookstoves": CanonicalSector.COOKSTOVES,
    "clean cookstoves": CanonicalSector.COOKSTOVES,
    "clean_cooking": CanonicalSector.COOKSTOVES,
    "clean cooking": CanonicalSector.COOKSTOVES,
    # Hybrid energy
    "hybrid_energy": CanonicalSector.HYBRID_ENERGY,
    "hybrid energy": CanonicalSector.HYBRID_ENERGY,
    "hybrid energy & mini-grids": CanonicalSector.HYBRID_ENERGY,
    "hybrid energy and mini-grids": CanonicalSector.HYBRID_ENERGY,
    "mini_grids": CanonicalSector.HYBRID_ENERGY,
    "mini-grids": CanonicalSector.HYBRID_ENERGY,
    # Biochar
    "biochar": CanonicalSector.BIOCHAR,
    "biochar_carbon_removal": CanonicalSector.BIOCHAR,
    "biochar carbon removal": CanonicalSector.BIOCHAR,
    # EV mobility
    "ev_mobility": CanonicalSector.EV_MOBILITY,
    "ev mobility": CanonicalSector.EV_MOBILITY,
    "electric_mobility": CanonicalSector.EV_MOBILITY,
    "electric mobility": CanonicalSector.EV_MOBILITY,
    # Agriculture
    "agriculture_land_use": CanonicalSector.AGRICULTURE_LAND_USE,
    "agriculture & land use": CanonicalSector.AGRICULTURE_LAND_USE,
    "agriculture and land use": CanonicalSector.AGRICULTURE_LAND_USE,
    "agriculture": CanonicalSector.AGRICULTURE_LAND_USE,
    "afolu": CanonicalSector.AGRICULTURE_LAND_USE,
}

# Explicitly disallowed family and test strings that must NEVER be accepted as operating sectors
DISALLOWED_SECTOR_STRINGS: Set[str] = {
    "test family",
    "biochar removal family",
    "fam-",
    "biochar_fam_lock",
    "test_family",
}


def normalize_to_canonical_sector(value: Optional[str]) -> Optional[CanonicalSector]:
    """
    Normalizes a sector input string or UUID string to a CanonicalSector enum member.
    Returns None if the value cannot be recognized as a valid canonical sector.
    """
    if not value or not isinstance(value, str):
        return None

    raw = value.strip()
    if not raw:
        return None

    raw_lower = raw.lower()

    # Reject known disallowed test fixture strings immediately
    for disallowed in DISALLOWED_SECTOR_STRINGS:
        if disallowed in raw_lower:
            return None

    # Check direct canonical code (e.g. 'COOKSTOVES')
    raw_upper = raw.upper()
    if raw_upper in CANONICAL_SECTOR_SET:
        return CanonicalSector(raw_upper)

    # Check known UUID
    try:
        parsed_uuid = str(uuid.UUID(raw)).lower()
        if parsed_uuid in CANONICAL_SECTOR_UUID_MAP:
            return CANONICAL_SECTOR_UUID_MAP[parsed_uuid]
    except (ValueError, TypeError, AttributeError):
        pass

    # Check explicit aliases
    if raw_lower in _CANONICAL_ALIASES:
        return _CANONICAL_ALIASES[raw_lower]

    return None


def is_canonical_sector(value: Optional[str]) -> bool:
    """Returns True if the value represents a canonical sector."""
    return normalize_to_canonical_sector(value) is not None


def get_canonical_sector_label(sector: CanonicalSector) -> str:
    """Returns the user-facing label for a canonical sector."""
    return CANONICAL_SECTOR_LABELS.get(sector, sector.value)


# Stale / legacy UUID aliases mapped to stable canonical methodology codes
STALE_METHODOLOGY_UUID_ALIASES: Dict[str, str] = {
    "ec739cc0-517a-4fa0-9ff3-ed4cc6d17667": "VM0042",
    "61114e85-8b39-470f-8c4a-70b7ae098009": "VM0044",
    "61114e85-8b39-470f-8c4a-70b7ae098007": "PURO_BIOCHAR_2025",
    "fe2f48fe-e99b-44eb-8b2b-72b330317e6a": "VM0042",
    "a7fb17ce-1d2c-4eca-99f2-3c69beff96bd": "VM0050",
    "1beee93b-1960-4acd-92b4-60d2cef61daf": "VM0050",
}


class VeriFieldSupportState(str, Enum):
    FULL = "FULL"                    # Full project onboarding + monitoring + verified calculation engine
    MRV_ONLY = "MRV_ONLY"            # Project onboarding + monitoring supported; calculation engine gated/unimplemented
    CATALOG_ONLY = "CATALOG_ONLY"    # Available in catalog for discovery/applicability; workflow not implemented
    PLANNED = "PLANNED"              # Known methodology, implementation scheduled
    LEGACY = "LEGACY"                # Grandfathered projects only


# Global Authoritative Methodology Catalog (15 primary methodologies across 5 canonical sectors)
GLOBAL_METHODOLOGY_CATALOG: Dict[str, Dict[str, Any]] = {
    # -------------------------------------------------------------------------
    # 1. Agriculture & Land Use (AGRICULTURE_LAND_USE)
    # -------------------------------------------------------------------------
    "VM0042": {
        "id": "f238258b-f8ec-4e5a-91cf-7537422796d3",
        "code": "VM0042",
        "name": "Improved Agricultural Land Management",
        "registry_code": "VERRA",
        "registry_name": "Verra (VCS)",
        "document_type": "METHODOLOGY",
        "version": "2.2",
        "supported_versions": ["2.2", "2.1"],
        "historical_versions": ["2.0", "1.0"],
        "valid_from": "2023-11-20",
        "selectable_for_new_projects": True,
        "official_source_url": "https://verra.org/methodologies/vm0042-improved-agricultural-land-management-v2-2/",
        "source_authority": "Verra",
        "last_verified_at": "2026-10-11",
        "sector": CanonicalSector.AGRICULTURE_LAND_USE,
        "subsector": "Cropland / Soil Carbon / Improved Agricultural Land Management",
        "registry_status": "ACTIVE",
        "verifield_support_state": VeriFieldSupportState.FULL,
        "calculation_support_status": "ENABLED",
        "mrv_support_status": "ENABLED",
        "applicability_summary": "Quantifies GHG reductions and SOC removals from improved agricultural practices (e.g., reduced tillage, cover crops, improved nutrient management, organic amendments) on croplands and grasslands.",
        "stable_identifier": "VERRA:VM0042:2.2",
        "description": "Quantifies greenhouse gas emission reductions and carbon dioxide removals resulting from the adoption of improved agricultural land management practices.",
        "associated_modules": ["VT0014", "VMD0053", "VMD0054"],
    },
    "VM0051": {
        "id": "615f5d40-f86a-4fdb-af23-d9f79d90d159",
        "code": "VM0051",
        "name": "Improved Management in Rice Production Systems",
        "registry_code": "VERRA",
        "registry_name": "Verra (VCS)",
        "document_type": "METHODOLOGY",
        "version": "1.1",
        "supported_versions": ["1.1"],
        "historical_versions": ["1.0"],
        "valid_from": "2024-06-27",
        "selectable_for_new_projects": True,
        "official_source_url": "https://verra.org/methodologies/vm0051-improved-management-in-rice-production-systems-v1-1/",
        "source_authority": "Verra",
        "last_verified_at": "2026-10-11",
        "sector": CanonicalSector.AGRICULTURE_LAND_USE,
        "subsector": "Rice Cultivation / Flooded Rice Water Management",
        "registry_status": "ACTIVE",
        "verifield_support_state": VeriFieldSupportState.MRV_ONLY,
        "calculation_support_status": "NOT_IMPLEMENTED",
        "mrv_support_status": "ENABLED",
        "applicability_summary": "Flooded rice systems implementing improved water regimes (e.g., alternate wetting and drying — AWD, multiple drainage) and organic residue management.",
        "stable_identifier": "VERRA:VM0051:1.1",
        "description": "Quantifies emission reductions from reduced methane emissions in flooded rice production through water management and straw practices.",
    },
    "VM0047": {
        "id": "9cc408db-c2bd-4df3-b488-44e8cff7fb73",
        "code": "VM0047",
        "name": "Afforestation, Reforestation, and Revegetation",
        "registry_code": "VERRA",
        "registry_name": "Verra (VCS)",
        "document_type": "METHODOLOGY",
        "version": "1.1",
        "supported_versions": ["1.1"],
        "historical_versions": ["1.0"],
        "valid_from": "2024-09-05",
        "selectable_for_new_projects": True,
        "official_source_url": "https://verra.org/methodologies/vm0047-afforestation-reforestation-and-revegetation-v1-1/",
        "source_authority": "Verra",
        "last_verified_at": "2026-10-11",
        "sector": CanonicalSector.AGRICULTURE_LAND_USE,
        "subsector": "ARR / Afforestation, Reforestation & Revegetation",
        "registry_status": "ACTIVE",
        "verifield_support_state": VeriFieldSupportState.MRV_ONLY,
        "calculation_support_status": "NOT_IMPLEMENTED",
        "mrv_support_status": "ENABLED",
        "applicability_summary": "ARR and revegetation activities establishing forest cover on non-forest land meeting minimum crown cover, tree height, and national forest definition criteria.",
        "stable_identifier": "VERRA:VM0047:1.1",
        "description": "Afforestation, reforestation, and revegetation on eligible non-wetland lands.",
    },
    "VM0032": {
        "id": "d6956c93-80ea-4763-9354-b7c6a84e7bbc",
        "code": "VM0032",
        "name": "Methodology for the Adoption of Sustainable Grasslands through Adjustment of Fire and Grazing",
        "registry_code": "VERRA",
        "registry_name": "Verra (VCS)",
        "document_type": "METHODOLOGY",
        "version": "1.0",
        "supported_versions": ["1.0"],
        "historical_versions": [],
        "valid_from": "2015-09-24",
        "selectable_for_new_projects": True,
        "official_source_url": "https://verra.org/methodologies/vm0032-methodology-for-the-adoption-of-sustainable-grasslands-v1-0/",
        "source_authority": "Verra",
        "last_verified_at": "2026-10-11",
        "sector": CanonicalSector.AGRICULTURE_LAND_USE,
        "subsector": "Grasslands / Fire & Grazing Management",
        "registry_status": "ACTIVE",
        "verifield_support_state": VeriFieldSupportState.CATALOG_ONLY,
        "calculation_support_status": "NOT_IMPLEMENTED",
        "mrv_support_status": "PLANNED",
        "applicability_summary": "Applicable to grassland systems where fire regime (frequency, timing, intensity) and livestock grazing pressure are adjusted to increase carbon stocks and reduce emissions.",
        "stable_identifier": "VERRA:VM0032:1.0",
        "description": "Adoption of sustainable grassland practices through adjustment of fire and grazing regimes.",
    },

    # -------------------------------------------------------------------------
    # 2. Biochar Carbon Removal (BIOCHAR)
    # -------------------------------------------------------------------------
    "VM0044": {
        "id": "cd093f0e-0353-449e-a56b-484398ea0f9e",
        "code": "VM0044",
        "name": "Biochar Utilization in Soil and Non-Soil Applications",
        "registry_code": "VERRA",
        "registry_name": "Verra (VCS)",
        "document_type": "METHODOLOGY",
        "version": "1.2",
        "supported_versions": ["1.2", "1.1.0"],
        "historical_versions": ["1.0"],
        "valid_from": "2024-08-15",
        "selectable_for_new_projects": True,
        "official_source_url": "https://verra.org/methodologies/vm0044-methodology-for-biochar-utilization-in-soil-and-non-soil-applications-v1-2/",
        "source_authority": "Verra",
        "last_verified_at": "2026-10-11",
        "sector": CanonicalSector.BIOCHAR,
        "subsector": "Biomass Pyrolysis / Soil & Material Sequestration",
        "registry_status": "ACTIVE",
        "verifield_support_state": VeriFieldSupportState.FULL,
        "calculation_support_status": "ENABLED",
        "mrv_support_status": "ENABLED",
        "applicability_summary": "Biochar carbon removal through sustainable biomass pyrolysis and durable soil or non-soil utilization.",
        "stable_identifier": "VERRA:VM0044:1.2",
        "description": "Biochar carbon removal through sustainable biomass pyrolysis and durable soil or non-soil utilization.",
    },
    "PURO_BIOCHAR_2025": {
        "id": "803127f7-2ef1-464e-8d95-55ba37ff9b17",
        "code": "PURO_BIOCHAR_2025",
        "name": "Puro Standard Biochar Methodology",
        "registry_code": "PURO_STANDARD",
        "registry_name": "Puro.earth Standard",
        "document_type": "METHODOLOGY",
        "version": "Edition 2025 v2",
        "supported_versions": ["Edition 2025 v2"],
        "historical_versions": ["Edition 2024", "Edition 2022"],
        "valid_from": "2025-01-01",
        "selectable_for_new_projects": True,
        "official_source_url": "https://puro.earth/biochar-methodology/",
        "source_authority": "Puro.earth Standard",
        "last_verified_at": "2026-10-11",
        "sector": CanonicalSector.BIOCHAR,
        "subsector": "Engineered Carbon Removal / CORC",
        "registry_status": "ACTIVE",
        "verifield_support_state": VeriFieldSupportState.FULL,
        "calculation_support_status": "ENABLED",
        "mrv_support_status": "ENABLED",
        "applicability_summary": "Engineered biochar carbon removal crediting under the Puro Standard with independent lab verification.",
        "stable_identifier": "PURO_STANDARD:PURO_BIOCHAR_2025:2025",
        "description": "Engineered biochar carbon removal crediting under the Puro Standard.",
    },
    "BIOCHAR_C_SINK": {
        "id": "8a2c728e-6a3c-5391-ba57-7da1af43c634",
        "code": "BIOCHAR_C_SINK",
        "name": "Global Biochar C-Sink Standard",
        "registry_code": "CSI",
        "registry_name": "Carbon Standards International",
        "document_type": "METHODOLOGY",
        "version": "3.3",
        "supported_versions": ["3.3"],
        "historical_versions": ["3.2", "3.1"],
        "valid_from": "2024-01-15",
        "selectable_for_new_projects": True,
        "official_source_url": "https://www.carbon-standards.com/en/standards/global-biochar-c-sink-standard/",
        "source_authority": "Carbon Standards International",
        "last_verified_at": "2026-10-11",
        "sector": CanonicalSector.BIOCHAR,
        "subsector": "Global & European Biochar Carbon Sink",
        "registry_status": "ACTIVE",
        "verifield_support_state": VeriFieldSupportState.CATALOG_ONLY,
        "calculation_support_status": "NOT_IMPLEMENTED",
        "mrv_support_status": "PLANNED",
        "applicability_summary": "Certification of biochar carbon sinks following European Biochar Certificate (EBC) and World Biochar Certificate guidelines with end-use tracking.",
        "stable_identifier": "CSI:BIOCHAR_C_SINK:3.3",
        "description": "Standard for certifying the climate impact of biochar carbon sink creation.",
    },

    # -------------------------------------------------------------------------
    # 3. Clean Cookstoves (COOKSTOVES)
    # -------------------------------------------------------------------------
    "GS_MECD": {
        "id": "183ce6d6-d193-41ca-be0e-1096e1971c69",
        "code": "GS_MECD",
        "name": "Metered & Measured Energy Cooking Devices",
        "registry_code": "GOLD_STANDARD",
        "registry_name": "Gold Standard for the Global Goals",
        "document_type": "METHODOLOGY",
        "version": "2.0",
        "supported_versions": ["2.0"],
        "historical_versions": ["1.0"],
        "valid_from": "2023-04-12",
        "selectable_for_new_projects": True,
        "official_source_url": "https://www.goldstandard.org/project-developer-platform/rules-and-requirements/methodologies/metered-and-measured-energy-cooking-devices",
        "source_authority": "Gold Standard for the Global Goals",
        "last_verified_at": "2026-10-11",
        "sector": CanonicalSector.COOKSTOVES,
        "subsector": "Metered Cooking Devices / IoT Thermal MRV",
        "registry_status": "ACTIVE",
        "verifield_support_state": VeriFieldSupportState.MRV_ONLY,
        "calculation_support_status": "NOT_IMPLEMENTED",
        "mrv_support_status": "ENABLED",
        "applicability_summary": "Projects deploying metered electric, biogas, LPG, or metered biomass cooking devices using automated data logging / IoT smart metering to quantify cooking energy directly.",
        "stable_identifier": "GOLD_STANDARD:GS_MECD:2.0",
        "description": "Gold Standard methodology for metered and measured energy cooking devices utilizing high-frequency digital IoT monitoring.",
    },
    "VM0050": {
        "id": "a7fb17ce-1d2c-4eca-99f2-3c69beff96bd",
        "code": "VM0050",
        "name": "Methodology for Improved Cookstoves",
        "registry_code": "VERRA",
        "registry_name": "Verra (VCS)",
        "document_type": "METHODOLOGY",
        "version": "1.0",
        "supported_versions": ["1.0"],
        "historical_versions": [],
        "valid_from": "2024-03-27",
        "selectable_for_new_projects": True,
        "official_source_url": "https://verra.org/methodologies/vm0050-methodology-for-improved-cookstoves-v1-0/",
        "source_authority": "Verra",
        "last_verified_at": "2026-10-11",
        "sector": CanonicalSector.COOKSTOVES,
        "subsector": "Efficient Cookstoves / Biomass Fuel Efficiency",
        "registry_status": "ACTIVE",
        "verifield_support_state": VeriFieldSupportState.CATALOG_ONLY,
        "calculation_support_status": "NOT_IMPLEMENTED",
        "mrv_support_status": "PLANNED",
        "applicability_summary": "Distribution of improved cookstoves that displace non-renewable biomass in domestic or institutional thermal cooking applications, superseding VM0006 under VCS.",
        "stable_identifier": "VERRA:VM0050:1.0",
        "description": "Verra VCS methodology for improved cookstoves displacing non-renewable biomass.",
    },
    "AMS_II_G": {
        "id": "9bd46fe2-5b2e-45a8-9c9c-5b761bdc6b98",
        "code": "AMS_II_G",
        "name": "Energy Efficiency Measures in Thermal Applications of Non-Renewable Biomass",
        "registry_code": "UNFCCC_CDM",
        "registry_name": "UNFCCC Clean Development Mechanism",
        "document_type": "METHODOLOGY",
        "version": "14.0",
        "supported_versions": ["14.0"],
        "historical_versions": ["13.0", "12.0", "11.0", "10.0"],
        "valid_from": "2025-06-12",
        "selectable_for_new_projects": True,
        "official_source_url": "https://cdm.unfccc.int/methodologies/SSCmethodologies/approved",
        "source_authority": "UNFCCC CDM Executive Board",
        "last_verified_at": "2026-10-11",
        "sector": CanonicalSector.COOKSTOVES,
        "subsector": "Thermal Biomass Efficiency / Improved Cookstoves",
        "registry_status": "ACTIVE",
        "verifield_support_state": VeriFieldSupportState.CATALOG_ONLY,
        "calculation_support_status": "NOT_IMPLEMENTED",
        "mrv_support_status": "PLANNED",
        "applicability_summary": "Small-scale methodology for introduction of high-efficiency biomass stoves displacing non-renewable biomass in domestic or commercial applications.",
        "stable_identifier": "UNFCCC:AMS-II.G:14.0",
        "description": "UNFCCC small-scale methodology for energy efficiency measures in thermal applications of non-renewable biomass.",
    },

    # -------------------------------------------------------------------------
    # 4. Hybrid Energy & Mini-grids (HYBRID_ENERGY)
    # -------------------------------------------------------------------------
    "AMS_I_F": {
        "id": "b007c7e9-2f2a-4155-85ae-371d66c97152",
        "code": "AMS_I_F",
        "name": "Renewable Electricity Generation for Captive Use and Mini-grid",
        "registry_code": "UNFCCC_CDM",
        "registry_name": "UNFCCC Clean Development Mechanism",
        "document_type": "METHODOLOGY",
        "version": "5.0",
        "supported_versions": ["5.0"],
        "historical_versions": ["4.0", "3.0", "2.0", "1.0"],
        "valid_from": "2022-09-08",
        "selectable_for_new_projects": True,
        "official_source_url": "https://cdm.unfccc.int/methodologies/DB/XKCRT4QQUUWXXZMQRXUGES0WON451M",
        "source_authority": "UNFCCC CDM Executive Board",
        "last_verified_at": "2026-10-11",
        "sector": CanonicalSector.HYBRID_ENERGY,
        "subsector": "Mini-grids / Captive Renewable Generation",
        "registry_status": "ACTIVE",
        "verifield_support_state": VeriFieldSupportState.MRV_ONLY,
        "calculation_support_status": "NOT_IMPLEMENTED",
        "mrv_support_status": "ENABLED",
        "applicability_summary": "Installations of renewable electricity generation facilities supplying captive consumers or mini-grid distribution systems, displacing fossil-fuel-based grid electricity or local diesel generators.",
        "stable_identifier": "UNFCCC:AMS-I.F:5.0",
        "description": "UNFCCC small-scale methodology for renewable electricity generation for captive use and mini-grid systems.",
    },
    "AMS_I_L": {
        "id": "cfed120a-8ed3-554d-9bfa-86e62b8fd4cf",
        "code": "AMS_I_L",
        "name": "Electrification of Rural Communities Using Renewable Energy",
        "registry_code": "UNFCCC_CDM",
        "registry_name": "UNFCCC Clean Development Mechanism",
        "document_type": "METHODOLOGY",
        "version": "5.0",
        "supported_versions": ["5.0"],
        "historical_versions": ["4.0", "3.0", "2.0", "1.0"],
        "valid_from": "2024-03-22",
        "selectable_for_new_projects": True,
        "official_source_url": "https://cdm.unfccc.int/methodologies/DB/7LB4TLJF6F0ZQQ07C91ND2EOLC0WPK/",
        "source_authority": "UNFCCC CDM Executive Board",
        "last_verified_at": "2026-10-11",
        "sector": CanonicalSector.HYBRID_ENERGY,
        "subsector": "Rural Electrification / Solar Home Systems",
        "registry_status": "ACTIVE",
        "verifield_support_state": VeriFieldSupportState.CATALOG_ONLY,
        "calculation_support_status": "NOT_IMPLEMENTED",
        "mrv_support_status": "PLANNED",
        "applicability_summary": "Renewable energy systems (e.g. solar home systems, micro-hydro) providing electricity to rural households and communities with no previous grid connection.",
        "stable_identifier": "UNFCCC:AMS-I.L:5.0",
        "description": "UNFCCC small-scale methodology for electrification of rural communities using renewable energy systems.",
    },
    "ACM0002": {
        "id": "4b131d9b-3d26-5870-aa53-c97fd58b8020",
        "code": "ACM0002",
        "name": "Grid-Connected Electricity Generation from Renewable Sources",
        "registry_code": "UNFCCC_CDM",
        "registry_name": "UNFCCC Clean Development Mechanism",
        "document_type": "METHODOLOGY",
        "version": "22.0",
        "supported_versions": ["22.0"],
        "historical_versions": [
            "21.0", "20.0", "19.0", "18.0", "17.0", "16.0", "15.0", "14.0", "13.0",
            "12.0", "11.0", "10.0", "9.0", "8.0", "7.0", "6.0", "5.0", "4.0", "3.0", "2.0", "1.0"
        ],
        "valid_from": "2024-05-31",
        "selectable_for_new_projects": True,
        "official_source_url": "https://cdm.unfccc.int/methodologies/DB/XB1TX7TAZ6SLWM9B7BC67THHVD16JV",
        "source_authority": "UNFCCC CDM Executive Board",
        "last_verified_at": "2026-10-11",
        "sector": CanonicalSector.HYBRID_ENERGY,
        "subsector": "Grid-Connected Renewable Energy",
        "registry_status": "ACTIVE",
        "verifield_support_state": VeriFieldSupportState.CATALOG_ONLY,
        "calculation_support_status": "NOT_IMPLEMENTED",
        "mrv_support_status": "PLANNED",
        "applicability_summary": "Large-scale grid-connected renewable power generation plants supplying electricity to national or regional utility grids.",
        "stable_identifier": "UNFCCC:ACM0002:22.0",
        "description": "Consolidated baseline methodology for grid-connected electricity generation from renewable sources.",
    },

    # -------------------------------------------------------------------------
    # 5. EV Mobility (EV_MOBILITY)
    # -------------------------------------------------------------------------
    "VM0038": {
        "id": "f835e2ce-630d-4479-97ad-ef0a25e405af",
        "code": "VM0038",
        "name": "Methodology for Electric Vehicle Charging Systems",
        "registry_code": "VERRA",
        "registry_name": "Verra (VCS)",
        "document_type": "METHODOLOGY",
        "version": "1.1",
        "supported_versions": ["1.1"],
        "historical_versions": ["1.0"],
        "valid_from": "2022-09-08",
        "selectable_for_new_projects": True,
        "official_source_url": "https://verra.org/methodologies/vm0038-methodology-for-electric-vehicle-charging-systems-v1-1/",
        "source_authority": "Verra",
        "last_verified_at": "2026-10-11",
        "sector": CanonicalSector.EV_MOBILITY,
        "subsector": "EV Charging Infrastructure / Transport Electrification",
        "registry_status": "ACTIVE",
        "verifield_support_state": VeriFieldSupportState.MRV_ONLY,
        "calculation_support_status": "NOT_IMPLEMENTED",
        "mrv_support_status": "ENABLED",
        "applicability_summary": "Quantifies emission reductions from displacement of internal combustion engine vehicles through electricity supplied by grid-connected or renewable EV charging stations.",
        "stable_identifier": "VERRA:VM0038:1.1",
        "description": "Verra VCS methodology for electric vehicle charging systems.",
        "associated_modules": ["VMD0049"],
    },
    "AMS_III_C": {
        "id": "0cb3d677-647e-4873-8d31-d7c0c567d903",
        "code": "AMS_III_C",
        "name": "Emission Reductions by Electric and Hybrid Vehicles",
        "registry_code": "UNFCCC_CDM",
        "registry_name": "UNFCCC Clean Development Mechanism",
        "document_type": "METHODOLOGY",
        "version": "16.0",
        "supported_versions": ["16.0"],
        "historical_versions": [
            "15.0", "14.0", "13.0", "12.0", "11.0", "10.0", "9.0", "8.0", "7.0",
            "6.0", "5.0", "4.0", "3.0", "2.0", "1.0"
        ],
        "valid_from": "2022-09-08",
        "selectable_for_new_projects": True,
        "official_source_url": "https://cdm.unfccc.int/methodologies/DB/HLOH5R7J6M96A23TFECTQ1BVIE24CK/",
        "source_authority": "UNFCCC CDM Executive Board",
        "last_verified_at": "2026-10-11",
        "sector": CanonicalSector.EV_MOBILITY,
        "subsector": "Low-GHG Vehicle Fleets / Electric Transport",
        "registry_status": "ACTIVE",
        "verifield_support_state": VeriFieldSupportState.CATALOG_ONLY,
        "calculation_support_status": "NOT_IMPLEMENTED",
        "mrv_support_status": "PLANNED",
        "applicability_summary": "Commercial fleets, public transit buses, or passenger vehicles replacing conventional fossil-fueled vehicles with electric or hybrid vehicles.",
        "stable_identifier": "UNFCCC:AMS-III.C:16.0",
        "description": "UNFCCC small-scale methodology for emission reductions by electric and hybrid vehicle fleets.",
    },
}

# Production Methodologies Catalog per Canonical Sector
CANONICAL_SECTOR_PRODUCTION_METHODOLOGIES: Dict[CanonicalSector, List[Dict[str, Any]]] = {
    CanonicalSector.AGRICULTURE_LAND_USE: [
        GLOBAL_METHODOLOGY_CATALOG["VM0042"],
        GLOBAL_METHODOLOGY_CATALOG["VM0051"],
        GLOBAL_METHODOLOGY_CATALOG["VM0047"],
        GLOBAL_METHODOLOGY_CATALOG["VM0032"],
    ],
    CanonicalSector.BIOCHAR: [
        GLOBAL_METHODOLOGY_CATALOG["VM0044"],
        GLOBAL_METHODOLOGY_CATALOG["PURO_BIOCHAR_2025"],
        GLOBAL_METHODOLOGY_CATALOG["BIOCHAR_C_SINK"],
    ],
    CanonicalSector.COOKSTOVES: [
        GLOBAL_METHODOLOGY_CATALOG["GS_MECD"],
        GLOBAL_METHODOLOGY_CATALOG["VM0050"],
        GLOBAL_METHODOLOGY_CATALOG["AMS_II_G"],
    ],
    CanonicalSector.HYBRID_ENERGY: [
        GLOBAL_METHODOLOGY_CATALOG["AMS_I_F"],
        GLOBAL_METHODOLOGY_CATALOG["AMS_I_L"],
        GLOBAL_METHODOLOGY_CATALOG["ACM0002"],
    ],
    CanonicalSector.EV_MOBILITY: [
        GLOBAL_METHODOLOGY_CATALOG["VM0038"],
        GLOBAL_METHODOLOGY_CATALOG["AMS_III_C"],
    ],
}

# Calculation-ready methodologies (strictly separated from catalog discovery)
# COOKSTOVES, HYBRID_ENERGY, and EV_MOBILITY calculation engines remain STRICTLY GATED.
CANONICAL_SECTOR_PRODUCTION_CALCULATION_GATES: Dict[CanonicalSector, List[str]] = {
    CanonicalSector.AGRICULTURE_LAND_USE: ["VM0042"],
    CanonicalSector.BIOCHAR: ["VM0044", "PURO_BIOCHAR_2025"],
    CanonicalSector.COOKSTOVES: [],
    CanonicalSector.HYBRID_ENERGY: [],
    CanonicalSector.EV_MOBILITY: [],
}

# Supporting modules and tools that must NEVER be surfaced as primary project methodologies
DISALLOWED_PRIMARY_METHODOLOGY_CODES: Set[str] = {
    "VT0014",          # Digital soil mapping tool
    "VMD0053",         # Biogeochemical model calibration module
    "VMD0054",         # Soil organic carbon sampling module
    "BM_T_001",        # Combined additionality tool
    "GS_AGRI_ACT_REQ", # Activity requirement, not primary methodology
    "VMD0049",         # Positive list additionality module for VM0038
}

# Methodologies whose calculation pathways remain unconfigured / reference-only (not production calculation ready)
UNCONFIGURED_METHODOLOGY_CODES: Set[str] = {
    # Cookstoves
    "AMS_II_G",
    "VM0006",
    "VM0050",
    "VMR0050",
    "GS_TPDDTEC",
    "GS_MECD",
    # Hybrid Energy
    "AMS_I_F",
    "AMS_I_L",
    "ACM0002",
    "CI_GRID_DISPLACEMENT",
    "ENERGY_DISPLACEMENT",
    "MINIGRID_DIESEL_DISPLACEMENT",
    "SHS_RENEWABLE_DISPLACEMENT",
    # EV Mobility
    "AMS_III_C",
    "VM0038",
    "EV_DISPLACEMENT",
    # Biochar
    "BIOCHAR_C_SINK",
    "EBC_BIOCHAR",
    "GS_BIOCHAR",
    # Agriculture
    "VM0051",
    "VM0047",
    "VM0032",
}


def resolve_methodology_code(identifier: Optional[str]) -> Optional[str]:
    """
    Resolves any methodology identifier (database UUID, stale alias UUID, stable identifier,
    or code) to its canonical uppercase methodology code.
    Returns None if the identifier cannot be resolved.
    """
    if not identifier or not isinstance(identifier, str):
        return None

    raw = identifier.strip()
    if not raw:
        return None

    raw_lower = raw.lower()
    raw_upper = raw.upper()

    # Check stale UUID aliases
    if raw_lower in STALE_METHODOLOGY_UUID_ALIASES:
        return STALE_METHODOLOGY_UUID_ALIASES[raw_lower]

    # Check direct code
    if raw_upper in GLOBAL_METHODOLOGY_CATALOG:
        return raw_upper

    def _norm(c: str) -> str:
        return c.replace("-", "_").replace(".", "_").upper()

    norm_raw = _norm(raw_upper)

    # Legacy code aliases
    if norm_raw in ("VMR0050", "VM0006"):
        return "VM0050"
    if norm_raw in ("PURO_BIOCHAR_2025_V2", "PURO_BIOCHAR") or norm_raw.startswith("PURO_BIOCHAR_2025_V2_"):
        return "PURO_BIOCHAR_2025"

    for code in GLOBAL_METHODOLOGY_CATALOG:
        if norm_raw == _norm(code):
            return code

    # Check by ID in global catalog
    for code, entry in GLOBAL_METHODOLOGY_CATALOG.items():
        if raw_lower == str(entry["id"]).lower():
            return code

    # Check stable identifier (e.g. VERRA:VM0042:2.2, GOLD_STANDARD:GS_MECD:2.0, UNFCCC:AMS-II.G:14.0)
    for code, entry in GLOBAL_METHODOLOGY_CATALOG.items():
        if raw_upper == entry.get("stable_identifier", "").upper():
            return code
        # Check historical stable identifiers (e.g. UNFCCC:AMS-II.G:13.0, UNFCCC:AMS-I.L:3.0, UNFCCC:ACM0002:21.0)
        reg = entry.get("registry_code", "").upper()
        clean_code_dash = entry.get("code", "").replace("_", "-").upper()
        clean_code_under = entry.get("code", "").replace("-", "_").upper()
        for hist_ver in entry.get("historical_versions", []):
            if raw_upper in (
                f"{reg}:{clean_code_dash}:{hist_ver}".upper(),
                f"{reg}:{clean_code_under}:{hist_ver}".upper(),
                f"UNFCCC:{clean_code_dash}:{hist_ver}".upper(),
                f"UNFCCC:{clean_code_under}:{hist_ver}".upper(),
                f"{clean_code_dash}:{hist_ver}".upper(),
                f"{clean_code_under}:{hist_ver}".upper(),
            ):
                return code

    # Check colon-delimited format (e.g. REGISTRY:CODE:VER or CODE:VER)
    if ":" in raw_upper:
        parts = [p.strip() for p in raw_upper.split(":") if p.strip()]
        for p in parts:
            p_norm = _norm(p)
            for code in GLOBAL_METHODOLOGY_CATALOG:
                if p_norm == _norm(code):
                    return code

    return None


def validate_methodology_version_selection(
    code_or_id: str,
    version: Optional[str] = None,
) -> Tuple[bool, str, Optional[str]]:
    """
    Validates whether a specified methodology version is allowed for NEW project creation.
    - If version is None/empty, defaults to the active current_version -> (True, "", current_version).
    - If version is an active/supported version -> (True, "", version).
    - If version is in historical_versions -> (False, "Version '{ver}' of {code} is historical/inactive and cannot be selected for new projects. Active version is {cur_ver}.", cur_ver).
    - If version is unrecognized -> (False, "Version '{ver}' is not a recognized version of {code}. Active version is {cur_ver}.", cur_ver).
    """
    if not code_or_id:
        return True, "", version

    resolved_code = resolve_methodology_code(code_or_id) or str(code_or_id).upper().replace("-", "_")
    cat_entry = GLOBAL_METHODOLOGY_CATALOG.get(resolved_code)
    if not cat_entry:
        return True, "", version

    cur_version = str(cat_entry.get("version", "1.0")).strip()
    supported = [str(v).strip().lower() for v in cat_entry.get("supported_versions", [cur_version])]
    historical = [str(v).strip().lower() for v in cat_entry.get("historical_versions", [])]

    if not version or str(version).strip() == "":
        return True, "", cur_version

    req_ver = str(version).strip()
    req_ver_lower = req_ver.lower()

    if req_ver_lower in supported or req_ver_lower == cur_version.lower():
        return True, "", req_ver

    display_code = cat_entry.get("code", resolved_code)

    if req_ver_lower in historical:
        return False, (
            f"Version '{req_ver}' of {display_code} is historical/inactive and cannot be selected for new projects. "
            f"Active version is {cur_version}."
        ), cur_version

    return False, (
        f"Version '{req_ver}' is not a recognized version of {display_code}. "
        f"Active version is {cur_version}."
    ), cur_version


def get_production_methodologies_for_sector(
    sector: CanonicalSector | str,
) -> List[Dict[str, Any]]:
    """Returns the list of primary catalog methodologies for a canonical sector."""
    canon = sector if isinstance(sector, CanonicalSector) else normalize_to_canonical_sector(str(sector))
    if not canon or canon not in CANONICAL_SECTOR_PRODUCTION_METHODOLOGIES:
        return []
    return [dict(m) for m in CANONICAL_SECTOR_PRODUCTION_METHODOLOGIES[canon]]


def get_canonical_methodology_codes_for_sector(
    sector: CanonicalSector | str,
) -> Set[str]:
    """Returns the set of uppercase methodology codes authorized for a canonical sector."""
    meths = get_production_methodologies_for_sector(sector)
    return {m["code"].upper() for m in meths}


def is_methodology_valid_for_sector(
    sector: CanonicalSector | str,
    methodology_code_or_id: str,
) -> Tuple[bool, str]:
    """
    Validates whether a methodology code or identifier is authorized for the given canonical sector.
    Returns (True, "") if valid, or (False, error_reason) if invalid.
    """
    canon = sector if isinstance(sector, CanonicalSector) else normalize_to_canonical_sector(str(sector))
    if not canon:
        return False, f"Invalid primary operating sector: '{sector}'. Sector must be one of: {', '.join(CANONICAL_SECTOR_CODES)}."

    raw_val = str(methodology_code_or_id).strip()
    raw_lower = raw_val.lower()
    clean_meth = raw_val.upper()

    if clean_meth in DISALLOWED_PRIMARY_METHODOLOGY_CODES:
        return False, f"'{clean_meth}' is a supporting module/tool, not an authorized primary project methodology."

    # Resolve identifier to canonical code if possible
    resolved_code = resolve_methodology_code(raw_val)
    check_code = resolved_code or clean_meth

    if check_code in DISALLOWED_PRIMARY_METHODOLOGY_CODES:
        return False, f"'{check_code}' is a supporting module/tool, not an authorized primary project methodology."

    valid_meths = get_production_methodologies_for_sector(canon)
    valid_codes = {m["code"].upper() for m in valid_meths}
    valid_ids = {str(m["id"]).lower() for m in valid_meths}

    # Direct match on ID or resolved code
    if raw_lower in valid_ids or check_code in valid_codes:
        return True, ""

    def _norm(c: str) -> str:
        return c.replace("-", "_").replace(".", "_").upper()

    norm_meth = _norm(check_code)
    norm_valid_codes = {_norm(c) for c in valid_codes}

    if norm_meth in norm_valid_codes:
        return True, ""

    # Check if methodology (by ID or code) belongs to a different canonical sector
    other_sector = None
    other_code = check_code
    for sec, items in CANONICAL_SECTOR_PRODUCTION_METHODOLOGIES.items():
        if sec != canon:
            for item in items:
                if (
                    raw_lower == str(item["id"]).lower()
                    or norm_meth == _norm(item["code"])
                    or check_code == item["code"].upper()
                ):
                    other_sector = CANONICAL_SECTOR_LABELS[sec]
                    other_code = item["code"]
                    break
            if other_sector:
                break

    # Also check other sectors in global catalog
    if not other_sector and check_code in GLOBAL_METHODOLOGY_CATALOG:
        cat_sec = GLOBAL_METHODOLOGY_CATALOG[check_code]["sector"]
        if cat_sec != canon:
            other_sector = CANONICAL_SECTOR_LABELS.get(cat_sec, cat_sec.value)
            other_code = check_code

    if other_sector:
        return False, (
            f"Methodology '{other_code}' belongs to sector '{other_sector}', not '{CANONICAL_SECTOR_LABELS[canon]}'. "
            f"Authorized methodologies for {CANONICAL_SECTOR_LABELS[canon]}: {', '.join(sorted(valid_codes))}."
        )

    return False, (
        f"Methodology '{clean_meth}' is not applicable to sector '{CANONICAL_SECTOR_LABELS[canon]}'. "
        f"Authorized methodologies: {', '.join(sorted(valid_codes))}."
    )
