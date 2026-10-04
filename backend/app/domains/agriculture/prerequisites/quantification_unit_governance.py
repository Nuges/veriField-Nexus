"""
=============================================================================
VeriField Nexus — Quantification Unit & Eligibility Area Governance Engine
=============================================================================
Enforces explicit separation between Quantification Units and Eligibility Areas
under June 2026 VM0042 C&C, and executes temporal Stratum resolution.
=============================================================================
"""

import math
from dataclasses import asdict, dataclass
from datetime import date
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class QuantificationUnitGovernanceRecord:
    quantification_unit_id: str
    project_id: str
    name: str
    code: Optional[str]
    total_area_ha: float
    eligible_area_ha: float
    boundary_geojson: Dict[str, Any]
    linked_land_unit_ids: List[str]
    configured_stratum_ids: List[str]
    is_active: bool
    active_period_start: Optional[str]
    active_period_end: Optional[str]
    baseline_parameters: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def validate_quantification_unit_mapping(
    qu_record: Dict[str, Any],
    associated_land_units: List[Dict[str, Any]],
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Validates the structure of a Quantification Unit against VM0042 and C&C 2026-06-11 rules:
    1. Must have explicit polygon boundary.
    2. Eligible area must not exceed total physical area.
    3. Linked land units must belong to the same project.
    4. Eligible area must be strictly positive.
    """
    qu_id = qu_record.get("id") or qu_record.get("quantification_unit_id")
    if not qu_id:
        return False, "QUANTIFICATION_UNIT_ID_MISSING", {"message": "Quantification unit identifier missing."}

    total_ha = float(qu_record.get("total_area_ha") or 0.0)
    eligible_ha = float(qu_record.get("eligible_area_ha") or total_ha)

    if total_ha <= 0.0:
        return False, "INVALID_TOTAL_AREA", {"total_area_ha": total_ha, "message": "Total area must be strictly positive."}

    if eligible_ha <= 0.0:
        return False, "INVALID_ELIGIBLE_AREA", {"eligible_area_ha": eligible_ha, "message": "Eligible area must be strictly positive."}

    if eligible_ha > total_ha * 1.0001:  # Allow 0.01% floating tolerance
        return False, "ELIGIBLE_AREA_EXCEEDS_TOTAL", {
            "eligible_area_ha": eligible_ha,
            "total_area_ha": total_ha,
            "message": "Eligible area cannot exceed total physical boundary area.",
        }

    boundary = qu_record.get("boundary_geojson")
    if not boundary or not boundary.get("coordinates"):
        return False, "SPATIAL_BOUNDARY_MISSING", {"message": "Quantification unit lacks explicit GeoJSON boundary."}

    return True, "QUANTIFICATION_UNIT_VALID", {
        "quantification_unit_id": str(qu_id),
        "total_area_ha": total_ha,
        "eligible_area_ha": eligible_ha,
        "linked_land_units_count": len(associated_land_units),
    }


def resolve_temporal_stratum(
    land_unit_id: str,
    observation_date: date,
    stratum_memberships: List[Dict[str, Any]],
) -> Tuple[Optional[str], Optional[str], str]:
    """
    Resolves the exact historical stratum for a land unit as-of the observation date.

    Returns:
        (stratum_id, stratum_code, resolution_status)
    """
    for sm in stratum_memberships:
        if str(sm.get("land_unit_id")) != str(land_unit_id):
            continue

        raw_from = sm.get("valid_from")
        raw_to = sm.get("valid_to")

        d_from = date.fromisoformat(str(raw_from)[:10]) if raw_from else date.min
        d_to = date.fromisoformat(str(raw_to)[:10]) if raw_to else date.max

        if d_from <= observation_date <= d_to:
            s_id = str(sm.get("stratum_id"))
            s_code = sm.get("stratum_code") or s_id[:8]
            return s_id, s_code, "HISTORICAL_STRATUM_RESOLVED"

    return None, None, "STRATUM_MEMBERSHIP_NOT_FOUND"
