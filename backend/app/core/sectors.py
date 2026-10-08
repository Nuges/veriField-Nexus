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


# Authoritative Production-Enabled Primary Methodologies per Canonical Sector
CANONICAL_SECTOR_PRODUCTION_METHODOLOGIES: Dict[CanonicalSector, List[Dict[str, Any]]] = {
    CanonicalSector.AGRICULTURE_LAND_USE: [
        {
            "id": "ec739cc0-517a-4fa0-9ff3-ed4cc6d17667",
            "code": "VM0042",
            "name": "Improved Agricultural Land Management",
            "registry_code": "VERRA",
            "registry_name": "Verra (VCS)",
            "document_type": "METHODOLOGY",
            "version": "2.2",
            "description": "Quantifies greenhouse gas emission reductions and carbon dioxide removals resulting from the adoption of improved agricultural land management practices (e.g., reduced tillage, cover crops, improved nutrient management, organic amendments).",
        }
    ],
    CanonicalSector.BIOCHAR: [
        {
            "id": "61114e85-8b39-470f-8c4a-70b7ae098009",
            "code": "VM0044",
            "name": "Biochar Utilization in Soil and Non-Soil Applications",
            "registry_code": "VERRA",
            "registry_name": "Verra (VCS)",
            "document_type": "METHODOLOGY",
            "version": "1.2",
            "description": "Biochar carbon removal through sustainable biomass pyrolysis and durable soil or non-soil utilization.",
        },
        {
            "id": "61114e85-8b39-470f-8c4a-70b7ae098008",
            "code": "BIOCHAR_C_SINK",
            "name": "Biochar Carbon Sink",
            "registry_code": "CSI",
            "registry_name": "Carbon Standards International",
            "document_type": "METHODOLOGY",
            "version": "1.0.0",
            "description": "Standard for carbon sink certification through biochar application.",
        },
        {
            "id": "61114e85-8b39-470f-8c4a-70b7ae098007",
            "code": "PURO_BIOCHAR_2025",
            "name": "Puro Standard Biochar Methodology",
            "registry_code": "PURO_STANDARD",
            "registry_name": "Puro.earth Standard",
            "document_type": "METHODOLOGY",
            "version": "2025",
            "description": "Engineered biochar carbon removal crediting under the Puro Standard.",
        },
        {
            "id": "61114e85-8b39-470f-8c4a-70b7ae098006",
            "code": "EBC_BIOCHAR",
            "name": "European Biochar Certificate",
            "registry_code": "CSI",
            "registry_name": "Carbon Standards International",
            "document_type": "METHODOLOGY",
            "version": "1.0.0",
            "description": "European standard for sustainable production and carbon sink certification of biochar.",
        },
        {
            "id": "61114e85-8b39-470f-8c4a-70b7ae098005",
            "code": "GS_BIOCHAR",
            "name": "Gold Standard Biochar Methodology",
            "registry_code": "GOLD_STANDARD",
            "registry_name": "Gold Standard (GS)",
            "document_type": "METHODOLOGY",
            "version": "1.0.0",
            "description": "Gold Standard methodology for biochar production and application.",
        },
    ],
    CanonicalSector.COOKSTOVES: [
        {
            "id": "4685d816-3d51-4cdd-85f1-8c6aab3c50a1",
            "code": "AMS_II_G",
            "name": "Energy Efficiency in Thermal Applications",
            "registry_code": "CDM",
            "registry_name": "Clean Development Mechanism",
            "document_type": "METHODOLOGY",
            "version": "1.0.0",
            "description": "CDM methodology for energy efficiency in thermal applications including household improved cookstoves.",
        },
        {
            "id": "4685d816-3d51-4cdd-85f1-8c6aab3c50a2",
            "code": "GS_MECD",
            "name": "Metered Energy Cooking Devices",
            "registry_code": "GOLD_STANDARD",
            "registry_name": "Gold Standard (GS)",
            "document_type": "METHODOLOGY",
            "version": "3.0",
            "description": "Quantification for electric and metered cooking devices displacing biomass.",
        },
        {
            "id": "4685d816-3d51-4cdd-85f1-8c6aab3c50a3",
            "code": "GS_TPDDTEC",
            "name": "Displace Decentralized Thermal Energy",
            "registry_code": "GOLD_STANDARD",
            "registry_name": "Gold Standard (GS)",
            "document_type": "METHODOLOGY",
            "version": "4.0",
            "description": "Thermal energy applications displacing woody biomass.",
        },
        {
            "id": "4685d816-3d51-4cdd-85f1-8c6aab3c50a4",
            "code": "VM0006",
            "name": "Fuel Switching (Cookstoves)",
            "registry_code": "VERRA",
            "registry_name": "Verra (VCS)",
            "document_type": "METHODOLOGY",
            "version": "1.0.0",
            "description": "Switching from non-renewable biomass to renewable cooking fuels.",
        },
        {
            "id": "4685d816-3d51-4cdd-85f1-8c6aab3c50a5",
            "code": "VMR0050",
            "name": "Thermal Energy Displacement",
            "registry_code": "VERRA",
            "registry_name": "Verra (VCS)",
            "document_type": "METHODOLOGY",
            "version": "1.0.0",
            "description": "Displacement of non-renewable fossil or biomass energy with clean thermal appliances.",
        },
    ],
    CanonicalSector.HYBRID_ENERGY: [
        {
            "id": "e1074ae1-c76c-47c7-a5de-0241d44031f1",
            "code": "AMS_I_F",
            "name": "Renewable Electricity for Captive Use",
            "registry_code": "CDM",
            "registry_name": "Clean Development Mechanism",
            "document_type": "METHODOLOGY",
            "version": "1.0.0",
            "description": "Renewable electricity generation displacing fossil fuel generators and captive mini-grids.",
        },
        {
            "id": "e1074ae1-c76c-47c7-a5de-0241d44031f2",
            "code": "CI_GRID_DISPLACEMENT",
            "name": "C&I Grid Displacement",
            "registry_code": "CDM",
            "registry_name": "Clean Development Mechanism",
            "document_type": "METHODOLOGY",
            "version": "1.0.0",
            "description": "Commercial & Industrial solar installations displacing grid and diesel power.",
        },
        {
            "id": "e1074ae1-c76c-47c7-a5de-0241d44031f3",
            "code": "ENERGY_DISPLACEMENT",
            "name": "Renewable Energy Displacement",
            "registry_code": "CDM",
            "registry_name": "Clean Development Mechanism",
            "document_type": "METHODOLOGY",
            "version": "1.0.0",
            "description": "Clean energy displacement of fossil generators across distributed assets.",
        },
        {
            "id": "e1074ae1-c76c-47c7-a5de-0241d44031f4",
            "code": "MINIGRID_DIESEL_DISPLACEMENT",
            "name": "Mini-Grid Diesel Displacement",
            "registry_code": "CDM",
            "registry_name": "Clean Development Mechanism",
            "document_type": "METHODOLOGY",
            "version": "1.0.0",
            "description": "Community solar mini-grids displacing baseline diesel gensets.",
        },
        {
            "id": "e1074ae1-c76c-47c7-a5de-0241d44031f5",
            "code": "SHS_RENEWABLE_DISPLACEMENT",
            "name": "Solar Home System Displacement",
            "registry_code": "CDM",
            "registry_name": "Clean Development Mechanism",
            "document_type": "METHODOLOGY",
            "version": "1.0.0",
            "description": "Distributed solar home systems for off-grid households displacing kerosene and diesel.",
        },
        {
            "id": "e1074ae1-c76c-47c7-a5de-0241d44031f6",
            "code": "ACM0002",
            "name": "Grid-Connected Renewable Electricity Generation",
            "registry_code": "CDM",
            "registry_name": "Clean Development Mechanism",
            "document_type": "METHODOLOGY",
            "version": "1.0.0",
            "description": "Grid-connected electricity generation from renewable sources displacing baseline fossil fuel generation.",
        },
    ],
    CanonicalSector.EV_MOBILITY: [
        {
            "id": "30592386-cdc7-4c42-a003-bc8aa7191aa1",
            "code": "EV_DISPLACEMENT",
            "name": "EV Fossil Fuel Displacement",
            "registry_code": "CDM",
            "registry_name": "Clean Development Mechanism",
            "document_type": "METHODOLOGY",
            "version": "1.0.0",
            "description": "Electric vehicle transport systems and fleets displacing internal combustion engines.",
        },
        {
            "id": "30592386-cdc7-4c42-a003-bc8aa7191aa2",
            "code": "AMS_III_C",
            "name": "Emission Reductions by Low-GHG Vehicles",
            "registry_code": "CDM",
            "registry_name": "Clean Development Mechanism",
            "document_type": "METHODOLOGY",
            "version": "1.0.0",
            "description": "Low-greenhouse gas emission vehicles for public and commercial transport fleets.",
        },
        {
            "id": "30592386-cdc7-4c42-a003-bc8aa7191aa3",
            "code": "VM0038",
            "name": "Electric Vehicle Charging Systems",
            "registry_code": "VERRA",
            "registry_name": "Verra (VCS)",
            "document_type": "METHODOLOGY",
            "version": "1.0.0",
            "description": "Quantifies emission reductions from the deployment of EV charging infrastructure.",
        },
    ],
}

# Supporting modules and tools that must NEVER be surfaced as primary project methodologies
DISALLOWED_PRIMARY_METHODOLOGY_CODES: Set[str] = {
    "VT0014",       # Digital soil mapping tool
    "VMD0053",      # Biogeochemical model calibration module
    "BM_T_001",     # Combined additionality tool
    "GS_AGRI_ACT_REQ", # Activity requirement, not primary methodology
}

# Agriculture methodologies whose calculation pathways remain unconfigured / not production-ready
UNCONFIGURED_METHODOLOGY_CODES: Set[str] = {
    "VM0047",
    "VM0051",
    "VM0032",
    "VM0041",
    "BM_AG04_001",
    "BM_AG04_002",
    "BM_FR05_002",
}


def get_production_methodologies_for_sector(
    sector: CanonicalSector | str,
) -> List[Dict[str, Any]]:
    """Returns the list of production-enabled primary methodologies for a canonical sector."""
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

    if clean_meth in UNCONFIGURED_METHODOLOGY_CODES:
        return False, f"Methodology '{clean_meth}' is not yet configured for production project onboarding."

    valid_meths = get_production_methodologies_for_sector(canon)
    valid_codes = {m["code"].upper() for m in valid_meths}
    valid_ids = {str(m["id"]).lower() for m in valid_meths}

    # Check direct ID match for the sector
    if raw_lower in valid_ids:
        return True, ""

    def _norm(c: str) -> str:
        return c.replace("-", "_").replace(".", "_").upper()

    norm_meth = _norm(clean_meth)
    norm_valid_codes = {_norm(c) for c in valid_codes}

    if norm_meth in norm_valid_codes or clean_meth in valid_codes:
        return True, ""

    # Check if methodology (by ID or code) belongs to a different canonical sector
    other_sector = None
    other_code = clean_meth
    for sec, items in CANONICAL_SECTOR_PRODUCTION_METHODOLOGIES.items():
        if sec != canon:
            for item in items:
                if raw_lower == str(item["id"]).lower() or norm_meth == _norm(item["code"]) or clean_meth == item["code"].upper():
                    other_sector = CANONICAL_SECTOR_LABELS[sec]
                    other_code = item["code"]
                    break
            if other_sector:
                break

    if other_sector:
        return False, (
            f"Methodology '{other_code}' belongs to sector '{other_sector}', not '{CANONICAL_SECTOR_LABELS[canon]}'. "
            f"Authorized methodologies for {CANONICAL_SECTOR_LABELS[canon]}: {', '.join(sorted(valid_codes))}."
        )

    return False, (
        f"Methodology '{clean_meth}' is not applicable to sector '{CANONICAL_SECTOR_LABELS[canon]}'. "
        f"Authorized methodologies: {', '.join(sorted(valid_codes))}."
    )
