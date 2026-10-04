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
from typing import Dict, List, Optional, Set
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
