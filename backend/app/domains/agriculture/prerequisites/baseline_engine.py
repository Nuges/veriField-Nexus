"""
=============================================================================
VeriField Nexus — Baseline Scenario, Management History & Control Sites Engine
=============================================================================
Evaluates historical management look-back coverage and linked baseline control
sites for VM0042 v2.2 Quantification Approach 2.

Distinguishes:
- HISTORICAL_LOOKBACK_PERIOD: Minimum 3 years AND at least one complete crop
  rotation where applicable.
- BASELINE_REASSESSMENT_PERIOD: Standard 10-year (or 5-year dynamic) reassessment
  cycle per VM0042 / VCS rules.
- Management practice categories: Distinguishes APPLICABLE_WITH_DATA,
  NOT_APPLICABLE, and MISSING_REQUIRED_DATA without inferring absence as zero.
=============================================================================
"""

from dataclasses import asdict, dataclass
from datetime import date
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


CANONICAL_MANAGEMENT_CATEGORIES = {
    "TILLAGE",
    "SYNTHETIC_FERTILIZER",
    "ORGANIC_AMENDMENTS",
    "CROP_ROTATION",
    "COVER_CROP",
    "IRRIGATION",
    "RESIDUE_BURNING",
    "GRAZING",
    "OTHER",
}

DEFAULT_ARABLE_CATEGORIES = {
    "TILLAGE",
    "SYNTHETIC_FERTILIZER",
    "ORGANIC_AMENDMENTS",
    "CROP_ROTATION",
}


class PracticeDataStatus(str, Enum):
    APPLICABLE_WITH_DATA = "APPLICABLE_WITH_DATA"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    MISSING_REQUIRED_DATA = "MISSING_REQUIRED_DATA"


@dataclass(frozen=True)
class PracticeCategoryAssessment:
    category: str
    applicability_status: str  # APPLICABLE_WITH_DATA, NOT_APPLICABLE, MISSING_REQUIRED_DATA
    records_count: int
    notes: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ManagementHistoryCoverage:
    project_id: str
    project_start_date: str
    historical_lookback_years: int
    crop_rotation_cycle_years: int
    effective_lookback_required_years: int
    lookback_start_date: str
    total_pre_project_records: int
    practice_assessments: Dict[str, PracticeCategoryAssessment]
    documented_categories: List[str]
    missing_categories: List[str]
    not_applicable_categories: List[str]
    missing_periods: List[str]
    is_lookback_sufficient: bool
    is_complete: bool
    status: str  # READY, INCOMPLETE, BLOCKED
    baseline_reassessment_period_years: int
    baseline_reassessment_governance_type: str = "PROGRAM_REQUIREMENT"
    methodology_recommended_reassessment_years: int = 5
    methodology_reassessment_trigger_logic: str = "REGIONAL_PRACTICE_CHANGE_OR_DATA_AVAILABILITY"
    baseline_reassessment_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "project_start_date": self.project_start_date,
            "historical_lookback_years": self.historical_lookback_years,
            "crop_rotation_cycle_years": self.crop_rotation_cycle_years,
            "effective_lookback_required_years": self.effective_lookback_required_years,
            "lookback_start_date": self.lookback_start_date,
            "total_pre_project_records": self.total_pre_project_records,
            "practice_assessments": {k: v.to_dict() for k, v in self.practice_assessments.items()},
            "documented_categories": self.documented_categories,
            "missing_categories": self.missing_categories,
            "not_applicable_categories": self.not_applicable_categories,
            "missing_periods": self.missing_periods,
            "is_lookback_sufficient": self.is_lookback_sufficient,
            "is_complete": self.is_complete,
            "status": self.status,
            "baseline_reassessment_period_years": self.baseline_reassessment_period_years,
            "baseline_reassessment_governance_type": self.baseline_reassessment_governance_type,
            "methodology_recommended_reassessment_years": self.methodology_recommended_reassessment_years,
            "methodology_reassessment_trigger_logic": self.methodology_reassessment_trigger_logic,
            "baseline_reassessment_notes": self.baseline_reassessment_notes,
        }


@dataclass(frozen=True)
class BaselineControlSiteStatus:
    is_required: bool
    control_sites_count: int
    linked_quantification_units: List[str]
    has_continuous_management_schedule: bool
    is_temporally_valid: bool
    status: str  # READY, INCOMPLETE, NOT_APPLICABLE, BLOCKED
    notes: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def normalize_practice_category(raw_cat: str) -> str:
    """Maps varied category inputs to canonical management record types."""
    cat = (raw_cat or "").strip().upper()
    if cat in ("FERTILIZER_SYNTHETIC", "SYNTHETIC_FERT", "SYNTHETIC_FERTILIZER"):
        return "SYNTHETIC_FERTILIZER"
    if cat in ("FERTILIZER_ORGANIC", "ORGANIC_AMENDMENT", "ORGANIC_AMENDMENTS", "MANURE"):
        return "ORGANIC_AMENDMENTS"
    if cat in ("TILLAGE", "PLOWING", "REDUCED_TILLAGE", "NO_TILL"):
        return "TILLAGE"
    if cat in ("CROP_ROTATION", "ROTATION", "CROPPING_SEQUENCE"):
        return "CROP_ROTATION"
    if cat in ("COVER_CROP", "COVER_CROPPING"):
        return "COVER_CROP"
    if cat in ("IRRIGATION", "WATER_MANAGEMENT"):
        return "IRRIGATION"
    if cat in ("RESIDUE_BURNING", "BURNING"):
        return "RESIDUE_BURNING"
    if cat in ("GRAZING", "PASTURE_MANAGEMENT"):
        return "GRAZING"
    return cat if cat in CANONICAL_MANAGEMENT_CATEGORIES else "OTHER"


def evaluate_management_history_coverage(
    project_start_date: date,
    management_records: List[Dict[str, Any]],
    lookback_years: int = 3,
    crop_rotation_cycle_years: Optional[int] = None,
    applicable_categories: Optional[List[str]] = None,
    not_applicable_categories: Optional[List[str]] = None,
    reassessment_frequency_years: int = 10,
) -> ManagementHistoryCoverage:
    """
    Evaluates pre-project management records coverage.

    Methodology Rule (VM0042 v2.2 Section 8.1):
    - Minimum historical look-back = 3 years AND at least one complete crop rotation where applicable.
    - If lookback_years < 3 -> Insufficient.
    - If crop_rotation_cycle_years > lookback_years -> Insufficient (rotation incomplete).
    - Distinguishes APPLICABLE_WITH_DATA, NOT_APPLICABLE, and MISSING_REQUIRED_DATA.
    """
    rotation_years = crop_rotation_cycle_years if (crop_rotation_cycle_years and crop_rotation_cycle_years > 0) else 1
    effective_required_years = max(3, rotation_years)

    # Historical look-back duration sufficiency check (§4, §38)
    is_lookback_sufficient = (lookback_years >= 3) and (lookback_years >= rotation_years)

    try:
        lookback_start = project_start_date.replace(year=project_start_date.year - lookback_years)
    except ValueError:
        # Leap year fallback (Feb 29 -> Feb 28)
        lookback_start = project_start_date.replace(year=project_start_date.year - lookback_years, day=28)

    pre_project_records = []
    category_counts: Dict[str, int] = {}

    for rec in management_records:
        rec_date_raw = rec.get("record_date") or rec.get("activity_date") or rec.get("event_date") or rec.get("date")
        if not rec_date_raw:
            continue
        if isinstance(rec_date_raw, str):
            r_date = date.fromisoformat(rec_date_raw[:10])
        elif isinstance(rec_date_raw, date):
            r_date = rec_date_raw
        else:
            continue

        if lookback_start <= r_date < project_start_date:
            pre_project_records.append(rec)
            raw_type = rec.get("record_type") or rec.get("practice_type") or rec.get("category") or ""
            canon_cat = normalize_practice_category(raw_type)
            category_counts[canon_cat] = category_counts.get(canon_cat, 0) + 1

    # Determine applicable vs not-applicable categories (§6)
    na_set = set(normalize_practice_category(c) for c in (not_applicable_categories or []))
    if applicable_categories is not None:
        app_set = set(normalize_practice_category(c) for c in applicable_categories) - na_set
    else:
        app_set = set(DEFAULT_ARABLE_CATEGORIES) - na_set

    practice_assessments: Dict[str, PracticeCategoryAssessment] = {}
    missing_cats: List[str] = []
    documented_cats: List[str] = []

    for cat in sorted(list(app_set | na_set)):
        cnt = category_counts.get(cat, 0)
        if cat in na_set:
            status_enum = PracticeDataStatus.NOT_APPLICABLE.value
            notes = f"Management practice '{cat}' designated as not applicable to project/quantification unit."
        elif cnt > 0:
            status_enum = PracticeDataStatus.APPLICABLE_WITH_DATA.value
            notes = f"Applicable practice '{cat}' documented with {cnt} pre-project historical records."
            documented_cats.append(cat)
        else:
            status_enum = PracticeDataStatus.MISSING_REQUIRED_DATA.value
            notes = f"Applicable practice '{cat}' has zero pre-project historical records."
            missing_cats.append(cat)

        practice_assessments[cat] = PracticeCategoryAssessment(
            category=cat,
            applicability_status=status_enum,
            records_count=cnt,
            notes=notes,
        )

    # Missing look-back years check
    missing_periods: List[str] = []
    for yr_offset in range(1, lookback_years + 1):
        target_yr = project_start_date.year - yr_offset
        has_yr_rec = any(
            (date.fromisoformat(str(r.get("record_date") or r.get("event_date") or r.get("date"))[:10]).year == target_yr)
            for r in pre_project_records
        )
        if not has_yr_rec:
            missing_periods.append(f"Year {target_yr} (pre-project year -{yr_offset})")

    # Incomplete conditions
    is_complete = (
        is_lookback_sufficient
        and (len(missing_cats) == 0)
        and (len(missing_periods) == 0)
        and (len(pre_project_records) > 0)
    )

    if not is_lookback_sufficient:
        status = "INCOMPLETE"
    elif not is_complete:
        status = "INCOMPLETE"
    else:
        status = "READY"

    reassess_notes = (
        f"Baseline reassessment interval: {reassessment_frequency_years} years (PROGRAM_REQUIREMENT pursuant to VCS AFOLU rules). "
        "Methodology recommendation: 5 years (METHODOLOGY_RECOMMENDATION trigger logic under VM0042 v2.2 Section 8.1 "
        "when regional agricultural practices change or dynamic data become available)."
    )

    return ManagementHistoryCoverage(
        project_id=str(management_records[0].get("project_id", "")) if management_records else "",
        project_start_date=project_start_date.isoformat(),
        historical_lookback_years=lookback_years,
        crop_rotation_cycle_years=rotation_years,
        effective_lookback_required_years=effective_required_years,
        lookback_start_date=lookback_start.isoformat(),
        total_pre_project_records=len(pre_project_records),
        practice_assessments=practice_assessments,
        documented_categories=sorted(documented_cats),
        missing_categories=sorted(missing_cats),
        not_applicable_categories=sorted(list(na_set)),
        missing_periods=missing_periods,
        is_lookback_sufficient=is_lookback_sufficient,
        is_complete=is_complete,
        status=status,
        baseline_reassessment_period_years=reassessment_frequency_years,
        baseline_reassessment_governance_type="PROGRAM_REQUIREMENT",
        methodology_recommended_reassessment_years=5,
        methodology_reassessment_trigger_logic="REGIONAL_PRACTICE_CHANGE_OR_DATA_AVAILABILITY",
        baseline_reassessment_notes=reassess_notes,
    )


def evaluate_baseline_control_sites(
    soc_approach: str,
    control_sites: List[Dict[str, Any]],
    quantification_units: List[str],
) -> BaselineControlSiteStatus:
    """
    Evaluates baseline control site readiness for Quantification Approach 2.
    """
    is_req = (soc_approach or "").upper() == "APPROACH_2"

    if not is_req:
        return BaselineControlSiteStatus(
            is_required=False,
            control_sites_count=len(control_sites),
            linked_quantification_units=[],
            has_continuous_management_schedule=True,
            is_temporally_valid=True,
            status="NOT_APPLICABLE",
            notes="Quantification Approach 1 uses biogeochemical modeling; baseline control sites not required.",
        )

    if not control_sites:
        return BaselineControlSiteStatus(
            is_required=True,
            control_sites_count=0,
            linked_quantification_units=[],
            has_continuous_management_schedule=False,
            is_temporally_valid=False,
            status="BLOCKED",
            notes="Quantification Approach 2 requires linked baseline control sites. Zero control sites registered.",
        )

    # Check linkage and active management schedule
    linked_qu: Set[str] = set()
    all_schedules_valid = True
    for cs in control_sites:
        qu_ref = cs.get("linked_quantification_unit_id") or cs.get("quantification_unit_id")
        if qu_ref:
            linked_qu.add(str(qu_ref))
        if not cs.get("has_continuous_management_schedule", True):
            all_schedules_valid = False

    missing_qu = set(str(q) for q in quantification_units) - linked_qu
    if missing_qu:
        return BaselineControlSiteStatus(
            is_required=True,
            control_sites_count=len(control_sites),
            linked_quantification_units=sorted(list(linked_qu)),
            has_continuous_management_schedule=all_schedules_valid,
            is_temporally_valid=True,
            status="INCOMPLETE",
            notes=f"Approach 2 control sites missing for quantification units: {sorted(list(missing_qu))}",
        )

    if not all_schedules_valid:
        return BaselineControlSiteStatus(
            is_required=True,
            control_sites_count=len(control_sites),
            linked_quantification_units=sorted(list(linked_qu)),
            has_continuous_management_schedule=False,
            is_temporally_valid=False,
            status="INCOMPLETE",
            notes="One or more baseline control sites lack documented continuous business-as-usual management schedule.",
        )

    return BaselineControlSiteStatus(
        is_required=True,
        control_sites_count=len(control_sites),
        linked_quantification_units=sorted(list(linked_qu)),
        has_continuous_management_schedule=True,
        is_temporally_valid=True,
        status="READY",
        notes=f"Linked baseline control sites verified for all {len(quantification_units)} quantification units.",
    )
