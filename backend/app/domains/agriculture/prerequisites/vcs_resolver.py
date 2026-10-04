"""
=============================================================================
VeriField Nexus — VCS Program Version & Template Transition Resolver
=============================================================================
Deterministic rule resolver for applicable Verified Carbon Standard (VCS)
program version, rule context, and project description template version
pursuant to official Verra Version 5 Document History and Transition Guidance.

Separates:
1. GOVERNING_VCS_STANDARD:
   - VCS_4_7: VCS Standard v4.7
   - VCS_5_0: VCS Standard v5.0
2. V5_TEMPLATE_VARIANT:
   - NONE: Version 5 templates do not apply (pre-2027 submission without early adoption)
   - V5_0A: Version 5.0A template for pre-2027 start projects, incorporating
     official delayed V5 requirements (V5#14, V5#16, V5#17, V5#23, V5#58)
     until the first crediting renewal or verification approval request with
     baseline reassessment submitted on or after 1 January 2030.
   - V5_0B: Version 5.0B template for projects starting on/after 1 January 2027,
     voluntary V5_0B_FULL early adopters, or pre-2027 projects undergoing 2030
     full transition.
3. PROJECT_DESCRIPTION_TEMPLATE:
   - VCS_PROJECT_DESCRIPTION_V4.4: Applicable to pre-2027 submissions prior to
     1 January 2027 without voluntary early adoption (mandatory from 1 Jan 2025).
   - VCS_PROJECT_DESCRIPTION_V5.0A: Applicable to pre-2027 start projects
     submitted on or after 1 January 2027 or electing voluntary early adoption V5_0A.
   - VCS_PROJECT_DESCRIPTION_V5.0B: Applicable to post-2027 start projects,
     voluntary V5_0B_FULL early adopters, or pre-2027 projects undergoing 2030
     full transition.
4. EARLY_ADOPTION_MODE:
   - NONE: Standard timeline
   - V5_0A: Voluntary early adoption of Version 5 with 5.0A delayed provisions
   - V5_0B_FULL: Voluntary early adoption of all Version 5 requirements without carve-outs
=============================================================================
"""

from dataclasses import asdict, dataclass
from datetime import date
from enum import Enum
from typing import Any, Dict, List, Optional


# Official Verra Transition Milestones & Cutoff Dates
VCS_V4_TEMPLATE_V4_4_MANDATORY_CUTOFF = date(2025, 1, 1)  # VCS Project Description Template v4.4 effective 1 Jan 2025
VCS_V5_MANDATORY_START_CUTOFF = date(2027, 1, 1)         # Projects starting on/after 1 Jan 2027 mandate VCS 5.0B
VCS_V5_MANDATORY_SUBMISSION_CUTOFF = date(2027, 1, 1)    # Requests submitted on/after 1 Jan 2027 mandate Version 5 templates
VCS_V5_FULL_TRANSITION_2030_CUTOFF = date(2030, 1, 1)    # Pre-2027 projects retain v4.7 requirements until renewal/reassessment on/after 1 Jan 2030

# Backward compatibility aliases
VCS_V5_RENEWAL_CUTOFF = VCS_V5_FULL_TRANSITION_2030_CUTOFF
VCS_V5_TEMPLATE_SUBMISSION_CUTOFF = VCS_V5_MANDATORY_SUBMISSION_CUTOFF


class GoverningVCSStandard(str, Enum):
    VCS_4_7 = "VCS_4_7"
    VCS_5_0 = "VCS_5_0"
    V4_7 = "VCS_4_7"
    V5_0 = "VCS_5_0"


class V5TemplateVariant(str, Enum):
    NONE = "NONE"
    V5_0A = "V5_0A"
    V5_0B = "V5_0B"


class ProjectDescriptionTemplate(str, Enum):
    VCS_PROJECT_DESCRIPTION_V4_4 = "VCS_PROJECT_DESCRIPTION_V4.4"
    VCS_PROJECT_DESCRIPTION_V5_0A = "VCS_PROJECT_DESCRIPTION_V5.0A"
    VCS_PROJECT_DESCRIPTION_V5_0B = "VCS_PROJECT_DESCRIPTION_V5.0B"


class EarlyAdoptionMode(str, Enum):
    NONE = "NONE"
    V5_0A = "V5_0A"
    V5_0B_FULL = "V5_0B_FULL"


class SubmissionStatus(str, Enum):
    ACTUAL_SUBMISSION_DATE = "ACTUAL_SUBMISSION_DATE"
    PROJECTED_SUBMISSION_DATE = "PROJECTED_SUBMISSION_DATE"
    NOT_YET_SUBMITTED = "NOT_YET_SUBMITTED"


@dataclass(frozen=True)
class VCSEffectiveDateUpdate:
    update_id: str
    requirement_title: str
    effective_date: str
    transition_trigger: str
    applicable_project_condition: str
    source_reference: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Official delayed Version 5 updates associated with 5.0A reporting per Verra Version 5 FAQ & Effective Dates Matrix
OFFICIAL_V5_DELAYED_UPDATES_5_0A: Dict[str, VCSEffectiveDateUpdate] = {
    "V5#14": VCSEffectiveDateUpdate(
        update_id="V5#14",
        requirement_title="Right to operate / right to reductions and removals",
        effective_date="2027-01-01",
        transition_trigger="POST_2030_RENEWAL_OR_BASELINE_REASSESSMENT",
        applicable_project_condition="Pre-2027 project start using VCS 5.0A template until post-2030 milestone",
        source_reference="VCS Version 5 Document History & Transition Guidance, Update V5#14",
    ),
    "V5#16": VCSEffectiveDateUpdate(
        update_id="V5#16",
        requirement_title="Stakeholder engagement",
        effective_date="2027-01-01",
        transition_trigger="POST_2030_RENEWAL_OR_BASELINE_REASSESSMENT",
        applicable_project_condition="Pre-2027 project start using VCS 5.0A template until post-2030 milestone",
        source_reference="VCS Version 5 Document History & Transition Guidance, Update V5#16",
    ),
    "V5#17": VCSEffectiveDateUpdate(
        update_id="V5#17",
        requirement_title="Safeguards",
        effective_date="2027-01-01",
        transition_trigger="POST_2030_RENEWAL_OR_BASELINE_REASSESSMENT",
        applicable_project_condition="Pre-2027 project start using VCS 5.0A template until post-2030 milestone",
        source_reference="VCS Version 5 Document History & Transition Guidance, Update V5#17",
    ),
    "V5#23": VCSEffectiveDateUpdate(
        update_id="V5#23",
        requirement_title="Ecosystem conversion safeguards",
        effective_date="2027-01-01",
        transition_trigger="POST_2030_RENEWAL_OR_BASELINE_REASSESSMENT",
        applicable_project_condition="Pre-2027 project start using VCS 5.0A template until post-2030 milestone",
        source_reference="VCS Version 5 Document History & Transition Guidance, Update V5#23",
    ),
    "V5#58": VCSEffectiveDateUpdate(
        update_id="V5#58",
        requirement_title="Financial transparency / benefit sharing",
        effective_date="2027-01-01",
        transition_trigger="POST_2030_RENEWAL_OR_BASELINE_REASSESSMENT",
        applicable_project_condition="Pre-2027 project start using VCS 5.0A template until post-2030 milestone",
        source_reference="VCS Version 5 Document History & Transition Guidance, Update V5#58",
    ),
}

# Canonical list of delayed IDs
CANONICAL_5_0A_DELAYED_UPDATE_IDS = list(OFFICIAL_V5_DELAYED_UPDATES_5_0A.keys())

# Backward compatibility alias
RETAINED_V4_7_REQUIREMENTS = CANONICAL_5_0A_DELAYED_UPDATE_IDS


@dataclass(frozen=True)
class BaselineReassessmentRuleResult:
    governing_vcs_standard: str
    vcs_mandatory_reassessment_years: int
    vcs_reassessment_rule_code: str
    vcs_reassessment_rule_title: str
    vcs_rule_reference: str
    methodology_recommendation_years: int
    methodology_rule_code: str
    methodology_rule_title: str
    methodology_rule_reference: str
    reassessment_rule_summary: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def resolve_baseline_reassessment_rule(
    governing_vcs_standard: str,
    project_start_date: date,
    submission_date: Optional[date] = None,
    registration_status: str = "REGISTERED",
    crediting_period_years: int = 20,
) -> BaselineReassessmentRuleResult:
    """
    Deterministically resolves baseline reassessment rule applicability pursuant to
    VCS Standard v4.7 (Section 3.14.7 mandatory 10-year ALM reassessment) vs
    VCS Version 5 (Update V5#101 crediting period / reassessment rule), distinct from
    VM0042 v2.2 Section 8.1 5-year advisory recommendation.
    """
    std_upper = (governing_vcs_standard or "VCS_4_7").upper()
    is_v5 = "5" in std_upper

    if not is_v5:
        vcs_years = 10
        vcs_code = "VCS_V4_7_ALM_10_YEAR_MANDATORY"
        vcs_title = "VCS v4.7 Mandatory 10-Year ALM Baseline Reassessment"
        vcs_ref = "VCS Standard v4.7, Section 3.14.7 (ALM Baseline Reassessment)"
        summary = "Under VCS Standard v4.7, agricultural land management (ALM) baseline reassessment is mandatory every 10 years."
    else:
        vcs_years = 10
        vcs_code = "VCS_V5_UPDATE_101_REASSESSMENT"
        vcs_title = "VCS Version 5 Update V5#101 Crediting Period & Baseline Reassessment Rule"
        vcs_ref = "VCS Version 5 Document History & Transition Guidance, Update V5#101"
        summary = "Under VCS Version 5 (governed by Update V5#101), crediting period renewal and baseline reassessment rules apply."

    return BaselineReassessmentRuleResult(
        governing_vcs_standard="VCS_5_0" if is_v5 else "VCS_4_7",
        vcs_mandatory_reassessment_years=vcs_years,
        vcs_reassessment_rule_code=vcs_code,
        vcs_reassessment_rule_title=vcs_title,
        vcs_rule_reference=vcs_ref,
        methodology_recommendation_years=5,
        methodology_rule_code="VM0042_V2_2_5_YEAR_ADVISORY",
        methodology_rule_title="VM0042 v2.2 Advisory 5-Year Baseline Reassessment",
        methodology_rule_reference="VM0042 v2.2, Section 8.1 (Methodology Recommendation on 5-Year Baseline Reassessment)",
        reassessment_rule_summary=(
            f"{summary} VM0042 v2.2 additionally recommends reassessment every 5 years where data become available or regional practices change (METHODOLOGY_RECOMMENDATION)."
        ),
    )


@dataclass(frozen=True)
class VCSResolutionResult:
    # 1. Governing Standard identity separated from template variant (§2)
    governing_vcs_standard: str                  # "VCS_4_7" or "VCS_5_0"
    v5_template_variant: str                     # "NONE", "V5_0A", "V5_0B"
    project_description_template: str            # "VCS_PROJECT_DESCRIPTION_V4.4", "VCS_PROJECT_DESCRIPTION_V5.0A", "VCS_PROJECT_DESCRIPTION_V5.0B"

    # 2. Early adoption mode (§6)
    early_adoption_mode: str                     # "NONE", "V5_0A", "V5_0B_FULL"
    voluntary_v5_adoption: bool                  # True if early_adoption_mode != "NONE"
    voluntary_early_adoption: bool               # alias
    early_transition_elected: bool               # alias

    # 3. Delayed requirement IDs & Effective Dates (§8)
    delayed_requirement_ids: List[str]           # ["V5#14", "V5#16", "V5#17", "V5#23", "V5#58"] for 5.0A, [] otherwise
    effective_date_rule_ids: List[str]           # rule ids active
    delayed_requirements: List[Dict[str, Any]]   # structured VCSEffectiveDateUpdate records
    retained_v4_7_requirements: List[str]        # alias for delayed_requirement_ids

    # 4. Transition triggers & milestones (§4, §9)
    transition_trigger: str
    transition_milestone: str
    resolution_reason: str
    transition_reason: str                       # alias
    official_rule_reference: str

    # 5. Submission & Temporal Context (§12)
    project_start_date: str
    request_submission_date: Optional[str]       # None if not yet submitted (no fabricated historical date)
    submission_date: Optional[str]               # alias
    submission_status: str                       # "ACTUAL_SUBMISSION_DATE", "PROJECTED_SUBMISSION_DATE", "NOT_YET_SUBMITTED"
    resolution_as_of_date: str                   # date of evaluation
    request_type: str
    is_v5: bool

    # 6. Backward-compatibility aliases for existing callers
    applicable_vcs_standard_version: str         # "VCS_V4.7" or "VCS_V5.0" (never "VCS_5_0A")
    vcs_program_context: str                     # "VCS_4_7" or "VCS_5_0"
    program_requirement_context: str             # "VCS_4_7" or "VCS_5_0"
    resolved_vcs_rule_context: str               # "VCS_4_7" or "VCS_5_0"
    vcs_standard_rule_context: str               # "VCS_4_7" or "VCS_5_0"
    applicable_template_context: str             # template version
    template_version: str                        # template version
    resolved_template_version: str               # template version
    vcs_template_version: str                    # template version

    # 7. Baseline reassessment rule details (§10, §11)
    baseline_reassessment_rule: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def resolve_vcs_program_version(
    project_start_date: date,
    request_type: str = "INITIAL_REGISTRATION",
    submission_date: Optional[date] = None,
    crediting_period_start: Optional[date] = None,
    baseline_reassessment_date: Optional[date] = None,
    voluntary_v5_adoption: bool = False,
    early_v5_transition_elected: bool = False,
    early_adoption_mode: Optional[str] = None,
    as_of_date: Optional[date] = None,
) -> VCSResolutionResult:
    """
    Deterministically resolves the applicable Governing VCS Standard, V5 Template Variant,
    Project Description Template, delayed requirement IDs, and transition milestones
    pursuant to official Verra VCS Version 5 Document History and Transition Guidance.

    Separates:
        - GOVERNING_VCS_STANDARD ("VCS_4_7" vs "VCS_5_0")
        - V5_TEMPLATE_VARIANT ("NONE", "V5_0A", "V5_0B")
        - PROJECT_DESCRIPTION_TEMPLATE ("VCS_PROJECT_DESCRIPTION_V4.4", "VCS_PROJECT_DESCRIPTION_V5.0A", "VCS_PROJECT_DESCRIPTION_V5.0B")
        - EARLY_ADOPTION_MODE ("NONE", "V5_0A", "V5_0B_FULL")
        - SUBMISSION_STATUS ("ACTUAL_SUBMISSION_DATE", "NOT_YET_SUBMITTED")
        - DELAYED_REQUIREMENT_IDS (["V5#14", "V5#16", "V5#17", "V5#23", "V5#58"])
    """
    req_type_upper = (request_type or "INITIAL_REGISTRATION").upper()

    # 1. Normalize Early Adoption Mode (§6)
    if early_adoption_mode:
        mode_upper = early_adoption_mode.upper()
        if mode_upper in ("V5_0B_FULL", "V5_0B", "FULL_V5"):
            mode = EarlyAdoptionMode.V5_0B_FULL.value
        elif mode_upper in ("V5_0A", "TRUE", "EARLY_V5"):
            mode = EarlyAdoptionMode.V5_0A.value
        else:
            mode = EarlyAdoptionMode.NONE.value
    elif voluntary_v5_adoption or early_v5_transition_elected:
        mode = EarlyAdoptionMode.V5_0A.value
    else:
        mode = EarlyAdoptionMode.NONE.value

    is_early_adoption = mode != EarlyAdoptionMode.NONE.value

    # 2. Normalize Submission Date & Status (§12)
    evaluation_as_of = as_of_date or date(2026, 10, 1)
    if submission_date is None:
        sub_status = SubmissionStatus.NOT_YET_SUBMITTED.value
        req_sub_date_str = None
        effective_date_for_eval = evaluation_as_of
    else:
        sub_status = SubmissionStatus.ACTUAL_SUBMISSION_DATE.value
        req_sub_date_str = submission_date.isoformat()
        effective_date_for_eval = submission_date

    as_of_str = effective_date_for_eval.isoformat()
    is_pre_2027_start = project_start_date < VCS_V5_MANDATORY_START_CUTOFF

    # ─────────────────────────────────────────────────────────────────────────
    # BRANCH 1: Pre-2027 Project Crediting Renewal / Baseline Reassessment (§4, §9, Cases F & G)
    # ─────────────────────────────────────────────────────────────────────────
    reassess_date = baseline_reassessment_date or crediting_period_start or effective_date_for_eval
    is_renewal_or_reassessment = req_type_upper in (
        "CREDITING_PERIOD_RENEWAL",
        "BASELINE_REASSESSMENT",
        "VERIFICATION_BASELINE_REASSESSMENT",
    )

    if is_pre_2027_start and is_renewal_or_reassessment:
        effective_req_date = effective_date_for_eval or reassess_date
        if effective_req_date >= VCS_V5_FULL_TRANSITION_2030_CUTOFF:
            # Case G: Qualifying renewal / baseline reassessment on or after 1 Jan 2030
            # Triggers full VCS Version 5.0B transition and cessation of retained v4.7 rules
            gov_std = GoverningVCSStandard.V5_0.value
            v5_variant = V5TemplateVariant.V5_0B.value
            tmpl = ProjectDescriptionTemplate.VCS_PROJECT_DESCRIPTION_V5_0B.value
            delayed_ids: List[str] = []
            delayed_objs: List[Dict[str, Any]] = []
            rule_ids = ["V5#101", "POST_2030_FULL_TRANSITION"]
            trig = "POST_2030_RENEWAL_OR_BASELINE_REASSESSMENT"
            ms = "POST_2030_RENEWAL_FULL_TRANSITION"
            reason = (
                f"Pre-2027 project qualifying request '{req_type_upper}' submitted on or after 1 January 2030 "
                f"({effective_req_date.isoformat()}) triggers full transition to VCS Version 5.0B and cessation of retained v4.7 requirements."
            )
            rule_ref = "VCS Version 5 Document History and Transition Guidance, Section 2.2 (Project Crediting Renewals & Baseline Reassessment on or after 1 January 2030)"
        else:
            # Case F: Baseline reassessment / renewal before 1 Jan 2030 (e.g. 2029-12-31)
            # Retained v4.7 requirements continue until next renewal/reassessment on or after 1 Jan 2030
            gov_std = GoverningVCSStandard.V5_0.value if effective_req_date >= VCS_V5_MANDATORY_SUBMISSION_CUTOFF else GoverningVCSStandard.V4_7.value
            v5_variant = V5TemplateVariant.V5_0A.value if effective_req_date >= VCS_V5_MANDATORY_SUBMISSION_CUTOFF else V5TemplateVariant.NONE.value
            tmpl = (
                ProjectDescriptionTemplate.VCS_PROJECT_DESCRIPTION_V5_0A.value
                if effective_req_date >= VCS_V5_MANDATORY_SUBMISSION_CUTOFF
                else ProjectDescriptionTemplate.VCS_PROJECT_DESCRIPTION_V4_4.value
            )
            delayed_ids = list(CANONICAL_5_0A_DELAYED_UPDATE_IDS) if v5_variant == V5TemplateVariant.V5_0A.value else []
            delayed_objs = [OFFICIAL_V5_DELAYED_UPDATES_5_0A[uid].to_dict() for uid in delayed_ids]
            rule_ids = list(delayed_ids) if delayed_ids else ["VCS_V4_TEMPLATE_MANDATE_2025"]
            trig = "PRE_2030_BASELINE_REASSESSMENT"
            ms = "PRE_2027_RETAINED_UNTIL_2030"
            reason = (
                f"Pre-2027 project request '{req_type_upper}' submitted prior to 1 January 2030 ({effective_req_date.isoformat()}). "
                "Under Verra transition guidance, retained v4.7 requirements continue until the next renewal/reassessment submitted on or after 1 January 2030."
            )
            rule_ref = "VCS Version 5 Document History and Transition Guidance, Section 2.2 (Carry-Over Provisions for Pre-2027 Projects Prior to 1 January 2030)"

        baseline_rule = resolve_baseline_reassessment_rule(
            governing_vcs_standard=gov_std,
            project_start_date=project_start_date,
            submission_date=submission_date,
        )
        return VCSResolutionResult(
            governing_vcs_standard=gov_std,
            v5_template_variant=v5_variant,
            project_description_template=tmpl,
            early_adoption_mode=mode,
            voluntary_v5_adoption=is_early_adoption,
            voluntary_early_adoption=is_early_adoption,
            early_transition_elected=is_early_adoption,
            delayed_requirement_ids=delayed_ids,
            effective_date_rule_ids=rule_ids,
            delayed_requirements=delayed_objs,
            retained_v4_7_requirements=list(delayed_ids),
            transition_trigger=trig,
            transition_milestone=ms,
            resolution_reason=reason,
            transition_reason=reason,
            official_rule_reference=rule_ref,
            project_start_date=project_start_date.isoformat(),
            request_submission_date=req_sub_date_str,
            submission_date=req_sub_date_str,
            submission_status=sub_status,
            resolution_as_of_date=as_of_str,
            request_type=req_type_upper,
            is_v5=(gov_std == GoverningVCSStandard.V5_0.value),
            applicable_vcs_standard_version="VCS_V5.0" if gov_std == GoverningVCSStandard.V5_0.value else "VCS_V4.7",
            vcs_program_context=gov_std,
            program_requirement_context=gov_std,
            resolved_vcs_rule_context=gov_std,
            vcs_standard_rule_context=gov_std,
            applicable_template_context=tmpl,
            template_version=tmpl,
            resolved_template_version=tmpl,
            vcs_template_version=tmpl,
            baseline_reassessment_rule=baseline_rule.to_dict(),
        )

    # ─────────────────────────────────────────────────────────────────────────
    # BRANCH 2: Project Start Date on or after 1 January 2027 (§5, Case E)
    # ─────────────────────────────────────────────────────────────────────────
    if not is_pre_2027_start:
        gov_std = GoverningVCSStandard.V5_0.value
        v5_variant = V5TemplateVariant.V5_0B.value
        tmpl = ProjectDescriptionTemplate.VCS_PROJECT_DESCRIPTION_V5_0B.value
        delayed_ids = []
        delayed_objs = []
        rule_ids = ["V5#101", "VCS_V5_MANDATORY_2027"]
        trig = "PROJECT_START_DATE_ON_OR_AFTER_2027"
        ms = "POST_2027_MANDATORY_V5B"
        reason = (
            f"Project start date ({project_start_date.isoformat()}) is on or after 1 January 2027, "
            "mandating full VCS Version 5.0 governing standard and Version 5.0B templates without delayed requirement carve-outs."
        )
        rule_ref = "VCS Version 5 Document History and Transition Guidance, Section 2.1 (New Projects with Start Date on or after 1 January 2027)"

        baseline_rule = resolve_baseline_reassessment_rule(
            governing_vcs_standard=gov_std,
            project_start_date=project_start_date,
            submission_date=submission_date,
        )
        return VCSResolutionResult(
            governing_vcs_standard=gov_std,
            v5_template_variant=v5_variant,
            project_description_template=tmpl,
            early_adoption_mode=mode,
            voluntary_v5_adoption=is_early_adoption,
            voluntary_early_adoption=is_early_adoption,
            early_transition_elected=is_early_adoption,
            delayed_requirement_ids=delayed_ids,
            effective_date_rule_ids=rule_ids,
            delayed_requirements=delayed_objs,
            retained_v4_7_requirements=list(delayed_ids),
            transition_trigger=trig,
            transition_milestone=ms,
            resolution_reason=reason,
            transition_reason=reason,
            official_rule_reference=rule_ref,
            project_start_date=project_start_date.isoformat(),
            request_submission_date=req_sub_date_str,
            submission_date=req_sub_date_str,
            submission_status=sub_status,
            resolution_as_of_date=as_of_str,
            request_type=req_type_upper,
            is_v5=True,
            applicable_vcs_standard_version="VCS_V5.0",
            vcs_program_context=gov_std,
            program_requirement_context=gov_std,
            resolved_vcs_rule_context=gov_std,
            vcs_standard_rule_context=gov_std,
            applicable_template_context=tmpl,
            template_version=tmpl,
            resolved_template_version=tmpl,
            vcs_template_version=tmpl,
            baseline_reassessment_rule=baseline_rule.to_dict(),
        )

    # ─────────────────────────────────────────────────────────────────────────
    # BRANCH 3: Pre-2027 Project Electing Voluntary Early Version 5 Adoption (§6, Cases B & C)
    # ─────────────────────────────────────────────────────────────────────────
    if is_early_adoption:
        gov_std = GoverningVCSStandard.V5_0.value
        if mode == EarlyAdoptionMode.V5_0B_FULL.value:
            # Case C: Full voluntary V5 adoption without carve-outs
            v5_variant = V5TemplateVariant.V5_0B.value
            tmpl = ProjectDescriptionTemplate.VCS_PROJECT_DESCRIPTION_V5_0B.value
            delayed_ids = []
            delayed_objs = []
            rule_ids = ["V5#101", "VOLUNTARY_V5B_FULL_ADOPTION"]
            trig = "VOLUNTARY_EARLY_ADOPTION_V5B_FULL"
            ms = "VOLUNTARY_FULL_V5B_EARLY_ADOPTION"
            reason = (
                f"Project start date ({project_start_date.isoformat()}) is prior to 1 January 2027 with voluntary early adoption "
                "of full Version 5 (V5_0B_FULL). Governed by VCS Standard v5.0 and Template v5.0B with all Version 5 requirements active."
            )
            rule_ref = "VCS Version 5 Document History and Transition Guidance, Section 2.3 (Voluntary Early Full Version 5 Adoption)"
        else:
            # Case B: Voluntary 5.0A early adoption
            v5_variant = V5TemplateVariant.V5_0A.value
            tmpl = ProjectDescriptionTemplate.VCS_PROJECT_DESCRIPTION_V5_0A.value
            delayed_ids = list(CANONICAL_5_0A_DELAYED_UPDATE_IDS)
            delayed_objs = [OFFICIAL_V5_DELAYED_UPDATES_5_0A[uid].to_dict() for uid in delayed_ids]
            rule_ids = list(delayed_ids)
            trig = "VOLUNTARY_EARLY_ADOPTION_V5A"
            ms = "PRE_2027_RETAINED_UNTIL_2030"
            reason = (
                f"Project start date ({project_start_date.isoformat()}) is prior to 1 January 2027 with voluntary early adoption of Version 5.0A. "
                "Governed by VCS Standard v5.0 and Template v5.0A with delayed requirements retained until 2030 milestone."
            )
            rule_ref = "VCS Version 5 Document History and Transition Guidance, Section 2.3 (Voluntary Early Adoption Provisions)"

        baseline_rule = resolve_baseline_reassessment_rule(
            governing_vcs_standard=gov_std,
            project_start_date=project_start_date,
            submission_date=submission_date,
        )
        return VCSResolutionResult(
            governing_vcs_standard=gov_std,
            v5_template_variant=v5_variant,
            project_description_template=tmpl,
            early_adoption_mode=mode,
            voluntary_v5_adoption=True,
            voluntary_early_adoption=True,
            early_transition_elected=True,
            delayed_requirement_ids=delayed_ids,
            effective_date_rule_ids=rule_ids,
            delayed_requirements=delayed_objs,
            retained_v4_7_requirements=list(delayed_ids),
            transition_trigger=trig,
            transition_milestone=ms,
            resolution_reason=reason,
            transition_reason=reason,
            official_rule_reference=rule_ref,
            project_start_date=project_start_date.isoformat(),
            request_submission_date=req_sub_date_str,
            submission_date=req_sub_date_str,
            submission_status=sub_status,
            resolution_as_of_date=as_of_str,
            request_type=req_type_upper,
            is_v5=True,
            applicable_vcs_standard_version="VCS_V5.0",
            vcs_program_context=gov_std,
            program_requirement_context=gov_std,
            resolved_vcs_rule_context=gov_std,
            vcs_standard_rule_context=gov_std,
            applicable_template_context=tmpl,
            template_version=tmpl,
            resolved_template_version=tmpl,
            vcs_template_version=tmpl,
            baseline_reassessment_rule=baseline_rule.to_dict(),
        )

    # ─────────────────────────────────────────────────────────────────────────
    # BRANCH 4: Pre-2027 Project Submitted On or After 1 January 2027 (§4, Case D)
    # ─────────────────────────────────────────────────────────────────────────
    if effective_date_for_eval >= VCS_V5_MANDATORY_SUBMISSION_CUTOFF:
        gov_std = GoverningVCSStandard.V5_0.value
        v5_variant = V5TemplateVariant.V5_0A.value
        tmpl = ProjectDescriptionTemplate.VCS_PROJECT_DESCRIPTION_V5_0A.value
        delayed_ids = list(CANONICAL_5_0A_DELAYED_UPDATE_IDS)
        delayed_objs = [OFFICIAL_V5_DELAYED_UPDATES_5_0A[uid].to_dict() for uid in delayed_ids]
        rule_ids = list(delayed_ids)
        trig = "POST_2027_REQUEST_SUBMISSION"
        ms = "PRE_2027_RETAINED_UNTIL_2030"
        reason = (
            f"Project start date ({project_start_date.isoformat()}) is prior to 1 January 2027, "
            f"with request submission on or after 1 January 2027 ({effective_date_for_eval.isoformat()}). "
            "Governed by VCS Standard v5.0 and Template v5.0A, retaining delayed Version 5 requirements until 2030 milestone."
        )
        rule_ref = "VCS Version 5 Document History and Transition Guidance, Section 2.1 & 2.2 (Template Transition Mandate for Pre-2027 Starts)"

        baseline_rule = resolve_baseline_reassessment_rule(
            governing_vcs_standard=gov_std,
            project_start_date=project_start_date,
            submission_date=submission_date,
        )
        return VCSResolutionResult(
            governing_vcs_standard=gov_std,
            v5_template_variant=v5_variant,
            project_description_template=tmpl,
            early_adoption_mode=mode,
            voluntary_v5_adoption=False,
            voluntary_early_adoption=False,
            early_transition_elected=False,
            delayed_requirement_ids=delayed_ids,
            effective_date_rule_ids=rule_ids,
            delayed_requirements=delayed_objs,
            retained_v4_7_requirements=list(delayed_ids),
            transition_trigger=trig,
            transition_milestone=ms,
            resolution_reason=reason,
            transition_reason=reason,
            official_rule_reference=rule_ref,
            project_start_date=project_start_date.isoformat(),
            request_submission_date=req_sub_date_str,
            submission_date=req_sub_date_str,
            submission_status=sub_status,
            resolution_as_of_date=as_of_str,
            request_type=req_type_upper,
            is_v5=True,
            applicable_vcs_standard_version="VCS_V5.0",
            vcs_program_context=gov_std,
            program_requirement_context=gov_std,
            resolved_vcs_rule_context=gov_std,
            vcs_standard_rule_context=gov_std,
            applicable_template_context=tmpl,
            template_version=tmpl,
            resolved_template_version=tmpl,
            vcs_template_version=tmpl,
            baseline_reassessment_rule=baseline_rule.to_dict(),
        )

    # ─────────────────────────────────────────────────────────────────────────
    # BRANCH 5: Pre-2027 Start + Pre-2027 Submission + No Early Adoption (§3, Case A & Case H)
    # ─────────────────────────────────────────────────────────────────────────
    gov_std = GoverningVCSStandard.V4_7.value
    v5_variant = V5TemplateVariant.NONE.value
    tmpl = ProjectDescriptionTemplate.VCS_PROJECT_DESCRIPTION_V4_4.value
    delayed_ids = []
    delayed_objs = []
    rule_ids = ["VCS_V4_TEMPLATE_MANDATE_2025"]
    trig = "PRE_2027_START_V4_TEMPLATE"
    ms = "PRE_2027_RETAINED_UNTIL_2030"
    reason = (
        f"Project start date ({project_start_date.isoformat()}) and request submission date are prior to 1 January 2027 "
        "without voluntary Version 5 early adoption. Governed by VCS Standard v4.7 and VCS Project Description Template v4.4 "
        "(mandatory effective from 1 January 2025)."
    )
    rule_ref = "VCS Program Document History (v4.4 effective 1 January 2025) and VCS Version 5 Document History and Transition Guidance, Section 2.1"

    baseline_rule = resolve_baseline_reassessment_rule(
        governing_vcs_standard=gov_std,
        project_start_date=project_start_date,
        submission_date=submission_date,
    )
    return VCSResolutionResult(
        governing_vcs_standard=gov_std,
        v5_template_variant=v5_variant,
        project_description_template=tmpl,
        early_adoption_mode=mode,
        voluntary_v5_adoption=False,
        voluntary_early_adoption=False,
        early_transition_elected=False,
        delayed_requirement_ids=delayed_ids,
        effective_date_rule_ids=rule_ids,
        delayed_requirements=delayed_objs,
        retained_v4_7_requirements=list(delayed_ids),
        transition_trigger=trig,
        transition_milestone=ms,
        resolution_reason=reason,
        transition_reason=reason,
        official_rule_reference=rule_ref,
        project_start_date=project_start_date.isoformat(),
        request_submission_date=req_sub_date_str,
        submission_date=req_sub_date_str,
        submission_status=sub_status,
        resolution_as_of_date=as_of_str,
        request_type=req_type_upper,
        is_v5=False,
        applicable_vcs_standard_version="VCS_V4.7",
        vcs_program_context=gov_std,
        program_requirement_context=gov_std,
        resolved_vcs_rule_context=gov_std,
        vcs_standard_rule_context=gov_std,
        applicable_template_context=tmpl,
        template_version=tmpl,
        resolved_template_version=tmpl,
        vcs_template_version=tmpl,
        baseline_reassessment_rule=baseline_rule.to_dict(),
    )
