"""
VeriField Nexus — Agriculture MRV Phase 3B-0: VM0042 v2.2 Methodology Prerequisite Engine Tests
Authoritative Gating Tests:
- Source Lock Registry & C&C 2026-06-11 Validation
- VCS Program Version Resolver (v4.7 vs v5.0 deterministic cutoffs)
- Component-Level Route Mapping & Gating (VMD0053 Approach 1 only, VT0014 DSM only)
- ESM Depth Horizons (0-30cm min + deeper bounding layer requirement)
- Shallow Soil Exception (verified bedrock/impeding layer)
- Sampling Design Sufficiency & Power Analysis Advisory (non-blocking advisory per Sec 8.2)
- Baseline Historical Lookback & Control Sites (no zero-emission assumptions)
- Temporal Stratum Resolution (StratumMembership validity window)
- Prerequisite Assessment Immutability, Lineage, and SHA-256 Hashing
- Segregation of Duties (FIELD_AGENT blocked from locking assessments)
- Fail-Closed Null Carbon Contract (no carbon stock, dSOC, or tCO2e minted/calculated)
- Multi-Tenant Isolation
"""

import hashlib
import json
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.security import get_password_hash
from app.db.session import async_session_factory
from app.domains.agriculture.models import (
    AgriculturePrerequisiteAssessment,
    ChainOfCustodyEvent,
    LaboratoryAnalysis,
    LaboratoryReceipt,
    LaboratoryResult,
    LandUnit,
    PhysicalSample,
    QuantificationInputSnapshot,
    SampleCollectionEvent,
    SampleQAReview,
    SamplingCampaign,
    SamplingPlanVersion,
    SamplingPoint,
    Stratum,
    StratumMembership,
)
from app.domains.agriculture.prerequisites.sources import (
    OFFICIAL_SOURCE_REGISTRY,
    compute_source_registry_hash,
    validate_methodology_ruleset,
    CANONICAL_METHODOLOGY_CODE,
    CANONICAL_METHODOLOGY_VERSION,
    CANONICAL_CC_VERSION,
)
from app.domains.agriculture.prerequisites.vcs_resolver import (
    resolve_vcs_program_version,
)
from app.domains.agriculture.prerequisites.route_resolver import (
    resolve_quantification_routes,
    QuantificationApproach,
    GHGComponent,
)
from app.domains.agriculture.prerequisites.esm_engine import (
    evaluate_depth_sufficiency,
    compile_esm_input_dossier,
    DepthSufficiencyStatus,
    BulkDensityProvenance,
    CoarseFragmentProvenance,
    SampleLayerEvidence,
)
from app.domains.agriculture.prerequisites.sampling_design_engine import (
    calculate_vm0042_power_analysis,
    evaluate_sampling_design,
    DesignSufficiencyStatus,
    PowerAnalysisStatus,
)
from app.domains.agriculture.prerequisites.baseline_engine import (
    evaluate_management_history_coverage,
    evaluate_baseline_control_sites,
)
from app.domains.agriculture.service import AgricultureService
from app.domains.authentication.models import User
from app.domains.authentication.service import AuthenticationService
from app.domains.earth_observation.models import ProjectBoundaryVersion
from app.domains.methodologies.models.base_registry import (
    Methodology,
    MethodologyFamily,
    MethodologyVersion,
)
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project
from app.main import app


# =============================================================================
# UNIT TESTS: Prerequisite Engines & Resolvers
# =============================================================================

def test_source_lock_registry_and_validation():
    """Verify that all official VM0042 v2.2 and VCS sources are locked and validation behaves deterministically."""
    # Check that required sources exist in registry
    assert "VM0042_V2_2" in OFFICIAL_SOURCE_REGISTRY
    assert "VM0042_V2_2_CC_20260611" in OFFICIAL_SOURCE_REGISTRY
    assert "VCS_STANDARD_V4_7" in OFFICIAL_SOURCE_REGISTRY
    assert "VCS_STANDARD_V5_0" in OFFICIAL_SOURCE_REGISTRY
    assert "VT0008_V1_0" in OFFICIAL_SOURCE_REGISTRY
    assert "VMD0053_V2_1" in OFFICIAL_SOURCE_REGISTRY
    assert "VT0014_V1_0" in OFFICIAL_SOURCE_REGISTRY
    assert "VT0014_V1_0_CC_20251016" in OFFICIAL_SOURCE_REGISTRY

    vm0042_entry = OFFICIAL_SOURCE_REGISTRY["VM0042_V2_2"]
    assert vm0042_entry.status == "ACTIVE"
    assert vm0042_entry.effective_date == "2025-10-21"

    cc_entry = OFFICIAL_SOURCE_REGISTRY["VM0042_V2_2_CC_20260611"]
    assert cc_entry.status == "ACTIVE"
    assert cc_entry.effective_date == "2026-06-11"

    # Fingerprint check
    fingerprint = compute_source_registry_hash()
    assert len(fingerprint) == 64  # SHA-256 hex string

    # Valid ruleset validation
    valid, code, details = validate_methodology_ruleset({
        "methodology_code": "VM0042",
        "version": "2.2",
        "corrections_clarifications_version": "2026-06-11",
    })
    assert valid is True
    assert code == "METHODOLOGY_RULESET_VALID"
    assert details["methodology_code"] == "VM0042"
    assert details["methodology_version"] == "2.2"

    # Invalid methodology code
    invalid, code, details = validate_methodology_ruleset({
        "methodology_code": "VM0099",
        "version": "2.2",
        "corrections_clarifications_version": "2026-06-11",
    })
    assert invalid is False
    assert code == "INVALID_METHODOLOGY_CODE"

    # Outdated C&C date
    invalid_cc, code_cc, details_cc = validate_methodology_ruleset({
        "methodology_code": "VM0042",
        "version": "2.2",
        "corrections_clarifications_version": "2024-01-01",
    })
    assert invalid_cc is False
    assert code_cc == "C_AND_C_NOT_APPLIED"


def test_vcs_transition_matrix_detailed():
    """
    Test Section 15 VCS Target Test Matrix (Cases A through H):
    A. pre-2027 start + pre-2027 request + no early adoption -> VCS_4_7 / template v4.4
    B. pre-2027 start + early V5_0A -> VCS_5_0 / template 5.0A / 5 official delayed requirements
    C. pre-2027 start + early V5_0B_FULL -> VCS_5_0 / template 5.0B / 0 delayed requirements
    D. pre-2027 start + post-2027 request -> VCS_5_0 / template 5.0A + delayed requirements
    E. post-2027 start -> VCS_5_0 / template 5.0B
    F. pre-2027 project + qualifying transition before 2030 -> no premature 5.0B forced transition
    G. pre-2027 project + qualifying transition on/after 2030 -> full 5.0B transition
    H. request_submission_date = NULL -> no fabricated historical submission date
    """
    # Case A: Start 2026-06-01, request 2026-10-01, no early adoption -> VCS Standard v4.7 + Template v4.4
    res_a = resolve_vcs_program_version(
        project_start_date=date(2026, 6, 1),
        submission_date=date(2026, 10, 1),
        request_type="INITIAL_REGISTRATION",
        early_adoption_mode="NONE",
    )
    assert res_a.governing_vcs_standard == "VCS_4_7"
    assert res_a.v5_template_variant == "NONE"
    assert res_a.project_description_template == "VCS_PROJECT_DESCRIPTION_V4.4"
    assert res_a.applicable_vcs_standard_version == "VCS_V4.7"
    assert res_a.template_version == "VCS_PROJECT_DESCRIPTION_V4.4"
    assert res_a.early_adoption_mode == "NONE"
    assert res_a.voluntary_v5_adoption is False
    assert len(res_a.delayed_requirement_ids) == 0
    assert res_a.transition_trigger == "PRE_2027_START_V4_TEMPLATE"

    # Case B: Start 2026-06-01, request 2026-10-01, voluntary V5 adoption V5_0A
    res_b = resolve_vcs_program_version(
        project_start_date=date(2026, 6, 1),
        submission_date=date(2026, 10, 1),
        request_type="INITIAL_REGISTRATION",
        early_adoption_mode="V5_0A",
    )
    assert res_b.governing_vcs_standard == "VCS_5_0"
    assert res_b.v5_template_variant == "V5_0A"
    assert res_b.project_description_template == "VCS_PROJECT_DESCRIPTION_V5.0A"
    assert res_b.applicable_vcs_standard_version == "VCS_V5.0"
    assert res_b.template_version == "VCS_PROJECT_DESCRIPTION_V5.0A"
    assert res_b.early_adoption_mode == "V5_0A"
    assert res_b.voluntary_v5_adoption is True
    assert len(res_b.delayed_requirement_ids) == 5
    assert "V5#14" in res_b.delayed_requirement_ids
    assert "V5#16" in res_b.delayed_requirement_ids
    assert "V5#17" in res_b.delayed_requirement_ids
    assert "V5#23" in res_b.delayed_requirement_ids
    assert "V5#58" in res_b.delayed_requirement_ids
    assert res_b.transition_trigger == "VOLUNTARY_EARLY_ADOPTION_V5A"

    # Case C: Start 2026-06-01, request 2026-10-01, voluntary V5_0B_FULL early adoption
    res_c = resolve_vcs_program_version(
        project_start_date=date(2026, 6, 1),
        submission_date=date(2026, 10, 1),
        request_type="INITIAL_REGISTRATION",
        early_adoption_mode="V5_0B_FULL",
    )
    assert res_c.governing_vcs_standard == "VCS_5_0"
    assert res_c.v5_template_variant == "V5_0B"
    assert res_c.project_description_template == "VCS_PROJECT_DESCRIPTION_V5.0B"
    assert res_c.applicable_vcs_standard_version == "VCS_V5.0"
    assert res_c.early_adoption_mode == "V5_0B_FULL"
    assert res_c.voluntary_v5_adoption is True
    assert len(res_c.delayed_requirement_ids) == 0
    assert res_c.transition_trigger == "VOLUNTARY_EARLY_ADOPTION_V5B_FULL"

    # Case D: Start 2026-06-01, request submitted 2027-02-01 (post-2027 request for pre-2027 start)
    res_d = resolve_vcs_program_version(
        project_start_date=date(2026, 6, 1),
        submission_date=date(2027, 2, 1),
        request_type="INITIAL_REGISTRATION",
    )
    assert res_d.governing_vcs_standard == "VCS_5_0"
    assert res_d.v5_template_variant == "V5_0A"
    assert res_d.project_description_template == "VCS_PROJECT_DESCRIPTION_V5.0A"
    assert res_d.applicable_vcs_standard_version == "VCS_V5.0"
    assert res_d.template_version == "VCS_PROJECT_DESCRIPTION_V5.0A"
    assert len(res_d.delayed_requirement_ids) == 5
    assert res_d.transition_trigger == "POST_2027_REQUEST_SUBMISSION"

    # Case E: Start 2027-01-01, request submitted 2027-02-01 -> Full VCS 5.0B context
    res_e = resolve_vcs_program_version(
        project_start_date=date(2027, 1, 1),
        submission_date=date(2027, 2, 1),
        request_type="INITIAL_REGISTRATION",
    )
    assert res_e.governing_vcs_standard == "VCS_5_0"
    assert res_e.v5_template_variant == "V5_0B"
    assert res_e.project_description_template == "VCS_PROJECT_DESCRIPTION_V5.0B"
    assert res_e.applicable_vcs_standard_version == "VCS_V5.0"
    assert res_e.template_version == "VCS_PROJECT_DESCRIPTION_V5.0B"
    assert len(res_e.delayed_requirement_ids) == 0
    assert res_e.transition_trigger == "PROJECT_START_DATE_ON_OR_AFTER_2027"

    # Case F: Start 2026-06-01, baseline reassessment request submitted 2029-12-31
    # MUST NOT prematurely transition to 5.0B before 1 Jan 2030
    res_f = resolve_vcs_program_version(
        project_start_date=date(2026, 6, 1),
        request_type="BASELINE_REASSESSMENT",
        submission_date=date(2029, 12, 31),
        baseline_reassessment_date=date(2029, 12, 31),
    )
    assert res_f.governing_vcs_standard == "VCS_5_0"
    assert res_f.v5_template_variant == "V5_0A"
    assert res_f.project_description_template == "VCS_PROJECT_DESCRIPTION_V5.0A"
    assert len(res_f.delayed_requirement_ids) == 5
    assert res_f.transition_trigger == "PRE_2030_BASELINE_REASSESSMENT"

    # Case G: Pre-2027 project qualifying renewal/reassessment request on or after 2030-01-01
    res_g = resolve_vcs_program_version(
        project_start_date=date(2026, 6, 1),
        request_type="CREDITING_PERIOD_RENEWAL",
        submission_date=date(2030, 1, 1),
        crediting_period_start=date(2030, 1, 1),
    )
    assert res_g.governing_vcs_standard == "VCS_5_0"
    assert res_g.v5_template_variant == "V5_0B"
    assert res_g.project_description_template == "VCS_PROJECT_DESCRIPTION_V5.0B"
    assert res_g.applicable_vcs_standard_version == "VCS_V5.0"
    assert len(res_g.delayed_requirement_ids) == 0
    assert res_g.transition_trigger == "POST_2030_RENEWAL_OR_BASELINE_REASSESSMENT"

    # Case H: request_submission_date = NULL -> no fabricated historical submission date
    res_h = resolve_vcs_program_version(
        project_start_date=date(2026, 6, 1),
        submission_date=None,
        early_adoption_mode="NONE",
    )
    assert res_h.submission_status == "NOT_YET_SUBMITTED"
    assert res_h.request_submission_date is None
    assert res_h.submission_date is None
    assert res_h.governing_vcs_standard == "VCS_4_7"
    assert res_h.v5_template_variant == "NONE"
    assert res_h.project_description_template == "VCS_PROJECT_DESCRIPTION_V4.4"
    assert res_h.resolution_as_of_date is not None


def test_baseline_reassessment_rule_resolution():
    """
    Test Section 10 & 11: Baseline Reassessment Rule Versioning:
    - VCS v4.7: Mandatory 10-year ALM baseline reassessment
    - VCS v5.0: Update V5#101 crediting period / reassessment rule
    - VM0042 v2.2: Advisory 5-year baseline reassessment
    """
    from app.domains.agriculture.prerequisites.vcs_resolver import resolve_baseline_reassessment_rule

    r_v4 = resolve_baseline_reassessment_rule("VCS_4_7", date(2026, 6, 1))
    assert r_v4.governing_vcs_standard == "VCS_4_7"
    assert r_v4.vcs_mandatory_reassessment_years == 10
    assert r_v4.vcs_reassessment_rule_code == "VCS_V4_7_ALM_10_YEAR_MANDATORY"
    assert r_v4.methodology_recommendation_years == 5
    assert r_v4.methodology_rule_code == "VM0042_V2_2_5_YEAR_ADVISORY"

    r_v5 = resolve_baseline_reassessment_rule("VCS_5_0", date(2027, 1, 1))
    assert r_v5.governing_vcs_standard == "VCS_5_0"
    assert r_v5.vcs_mandatory_reassessment_years == 10
    assert r_v5.vcs_reassessment_rule_code == "VCS_V5_UPDATE_101_REASSESSMENT"
    assert r_v5.methodology_recommendation_years == 5
    assert r_v5.methodology_rule_code == "VM0042_V2_2_5_YEAR_ADVISORY"


def test_table5_exact_15_component_completeness():
    """
    Test Section 14: Table 5 Exact 15-Component Inventory Completeness:
    - Expected = 15
    - Actual = 15
    - Missing = 0
    - Extra = 0
    - Duplicate = 0
    """
    from app.domains.agriculture.prerequisites.route_resolver import (
        resolve_quantification_routes,
        CANONICAL_VM0042_TABLE_5_COMPONENTS,
    )
    assert len(CANONICAL_VM0042_TABLE_5_COMPONENTS) == 15

    res = resolve_quantification_routes({
        "quantification_approach": "APPROACH_2",
        "has_livestock": True,
        "include_woody_biomass": True,
        "has_paddy_rice": True,
    })

    assert res.table5_complete is True
    assert len(res.table5_validation_errors) == 0
    assert res.canonical_component_count == 15
    assert len(res.canonical_component_routes) == 15

    # Check set completeness
    expected_set = set(CANONICAL_VM0042_TABLE_5_COMPONENTS)
    actual_set = set(res.canonical_component_routes.keys())
    missing = expected_set - actual_set
    extra = actual_set - expected_set

    assert len(missing) == 0, f"Missing Table 5 components: {missing}"
    assert len(extra) == 0, f"Extra Table 5 components: {extra}"


def test_table5_route_matrix_completeness():
    """
    Test Section 37: Complete VM0042 v2.2 Table 5 exact route map.
    Every official Table 5 source/pool must appear exactly once in canonical metadata,
    and impermissible approaches must be rejected.
    """
    res = resolve_quantification_routes(
        project_config={
            "quantification_approach": "APPROACH_2",
            "include_woody_biomass": True,
            "has_paddy_rice": True,
            "has_livestock": True,
        }
    )
    assert res.table5_complete is True
    assert len(res.table5_validation_errors) == 0

    # Verify canonical methodology sources including CH4_MANURE_DEPOSITION
    assert "CH4_MANURE_DEPOSITION" in res.component_routes
    assert "CH4_MANURE_MANAGEMENT" in res.component_routes  # Legacy mapped alias
    assert res.component_routes["CH4_MANURE_DEPOSITION"].component == "CH4_MANURE_DEPOSITION"

    # Verify approach gating: SOC Stock change cannot use Approach 3
    soc_route = res.component_routes["CO2_SOC"]
    assert soc_route.quantification_approach in ("APPROACH_1", "APPROACH_2")
    assert soc_route.quantification_approach != "APPROACH_3"

    # Woody biomass uses external tool (CDM AR-TOOL14)
    wb_route = res.component_routes["CO2_WOODY_BIOMASS"]
    assert wb_route.quantification_approach == "EXTERNAL_TOOL"
    assert wb_route.applicable_module == "CDM_AR_TOOL14"

    # Soil Methanogenesis has canonical name CH4_SOIL_METHANOGENESIS (rice as subtype)
    ch4_meth = res.component_routes["CH4_SOIL_METHANOGENESIS"]
    assert ch4_meth.subtype == "RICE_CULTIVATION"


def test_baseline_lookback_matrix():
    """
    Test Section 38: Historical look-back matrix:
    - 3 years + complete 3-year rotation -> sufficient
    - 3 years + incomplete 5-year rotation -> incomplete
    - 5 years + complete 5-year rotation -> sufficient
    - 2 years -> insufficient
    - Missing applicable management history -> incomplete
    """
    start = date(2026, 1, 1)

    def make_records(years: int, cats: list):
        records = []
        for y_off in range(1, years + 1):
            yr = 2026 - y_off
            for c in cats:
                records.append({
                    "record_date": f"{yr}-04-15",
                    "record_type": c,
                    "practice_type": "BASELINE",
                })
        return records

    all_cats = ["TILLAGE", "SYNTHETIC_FERTILIZER", "ORGANIC_AMENDMENTS", "CROP_ROTATION"]

    # 1. 3 years + complete 3-year rotation -> SUFFICIENT (READY)
    res_3y_ok = evaluate_management_history_coverage(
        project_start_date=start,
        management_records=make_records(3, all_cats),
        lookback_years=3,
        crop_rotation_cycle_years=3,
    )
    assert res_3y_ok.is_lookback_sufficient is True
    assert res_3y_ok.is_complete is True
    assert res_3y_ok.status == "READY"
    assert res_3y_ok.baseline_reassessment_period_years == 10

    # 2. 3 years + incomplete 5-year rotation -> INCOMPLETE
    res_3y_incomp = evaluate_management_history_coverage(
        project_start_date=start,
        management_records=make_records(3, all_cats),
        lookback_years=3,
        crop_rotation_cycle_years=5,  # Requires at least 5 years
    )
    assert res_3y_incomp.is_lookback_sufficient is False
    assert res_3y_incomp.status == "INCOMPLETE"

    # 3. 5 years + complete 5-year rotation -> SUFFICIENT (READY)
    res_5y_ok = evaluate_management_history_coverage(
        project_start_date=start,
        management_records=make_records(5, all_cats),
        lookback_years=5,
        crop_rotation_cycle_years=5,
    )
    assert res_5y_ok.is_lookback_sufficient is True
    assert res_5y_ok.is_complete is True
    assert res_5y_ok.status == "READY"

    # 4. 2 years -> INSUFFICIENT (< 3 years minimum)
    res_2y = evaluate_management_history_coverage(
        project_start_date=start,
        management_records=make_records(2, all_cats),
        lookback_years=2,
    )
    assert res_2y.is_lookback_sufficient is False
    assert res_2y.status == "INCOMPLETE"

    # 5. Missing applicable management history category (e.g. no tillage recorded)
    res_missing_cat = evaluate_management_history_coverage(
        project_start_date=start,
        management_records=make_records(3, ["SYNTHETIC_FERTILIZER", "ORGANIC_AMENDMENTS", "CROP_ROTATION"]),
        lookback_years=3,
        crop_rotation_cycle_years=3,
    )
    assert res_missing_cat.is_complete is False
    assert "TILLAGE" in res_missing_cat.missing_categories
    assert res_missing_cat.status == "INCOMPLETE"


def test_sampling_design_matrix():
    """
    Test Section 39: Sampling design test matrix:
    - stratified random -> standard-compliant
    - multistage with stratified-random final point stage -> standard-compliant
    - simple random without prior stratification -> deviation required
    - systematic/grid -> deviation required / not recommended
    """
    # 1. Stratified Random -> STANDARD_METHOD (READY)
    res_sr = evaluate_sampling_design(
        plan_version={"sampling_design_type": "STRATIFIED_RANDOM", "is_locked": True},
        actual_points_count=10,
        strata_count=2,
        variance_basis=0.35,
    )
    assert res_sr.design_compliance == "STANDARD_METHOD"
    assert res_sr.is_standard_default is True
    assert res_sr.overall_status in ("READY", "READY_WITH_NONBLOCKING_ADVISORY")

    # 2. Multistage with stratified random final stage -> STANDARD_METHOD
    res_multi = evaluate_sampling_design(
        plan_version={"sampling_design_type": "MULTISTAGE_WITH_STRATIFIED_RANDOM_FINAL_STAGE", "is_locked": True},
        actual_points_count=12,
        strata_count=3,
        variance_basis=0.40,
    )
    assert res_multi.design_compliance == "STANDARD_METHOD"
    assert res_multi.is_standard_default is True

    # 3. Simple random without prior stratification -> BLOCKED (Deviation required)
    res_simple = evaluate_sampling_design(
        plan_version={"sampling_design_type": "SIMPLE_RANDOM", "is_locked": True},
        actual_points_count=10,
        strata_count=0,
        variance_basis=0.35,
        has_approved_methodology_deviation=False,
    )
    assert res_simple.design_compliance == "METHODOLOGY_DEVIATION_REQUIRED"
    assert res_simple.overall_status == "BLOCKED"
    assert any("METHODOLOGY_DEVIATION_REQUIRED" in d for d in res_simple.blocking_defects)

    # Simple random WITH approved deviation -> can proceed
    res_simple_dev = evaluate_sampling_design(
        plan_version={"sampling_design_type": "SIMPLE_RANDOM", "is_locked": True},
        actual_points_count=10,
        strata_count=0,
        variance_basis=0.35,
        has_approved_methodology_deviation=True,
        deviation_justification="VVB Approved deviation DEV-2026-01",
    )
    assert res_simple_dev.has_approved_methodology_deviation is True
    assert res_simple_dev.overall_status != "BLOCKED"

    # 4. Systematic Grid -> NOT_RECOMMENDED / BLOCKED
    res_grid = evaluate_sampling_design(
        plan_version={"sampling_design_type": "GRID_OR_LINEAR", "is_locked": True},
        actual_points_count=10,
        strata_count=1,
        variance_basis=0.35,
        has_approved_methodology_deviation=False,
    )
    assert res_grid.design_compliance == "NOT_RECOMMENDED"
    assert res_grid.overall_status == "BLOCKED"


def test_power_parameter_source_audit():
    """
    Test Section 40: Power parameter source test:
    Audit alpha/power parameters against VM0042 Section 8.2 normative examples.
    """
    # Normative example values (alpha = 0.05 / 95% confidence; power = 90%)
    res_norm = calculate_vm0042_power_analysis(
        expected_variance=0.5,
        minimum_detectable_difference=1.0,
        confidence_level_pct=95.0,
        statistical_power_pct=90.0,
    )
    assert res_norm.status == "RESULT_AVAILABLE"
    assert res_norm.is_mandatory is False  # Non-blocking advisory
    alpha_audit = next(p for p in res_norm.parameter_audit if "alpha" in p.parameter_name)
    assert alpha_audit.normative_status == "NORMATIVE_EXAMPLE"
    power_audit = next(p for p in res_norm.parameter_audit if "power" in p.parameter_name)
    assert power_audit.normative_status == "NORMATIVE_EXAMPLE"

    # User configured values (e.g. 90% confidence / alpha=0.10; 80% power)
    res_cfg = calculate_vm0042_power_analysis(
        expected_variance=0.5,
        minimum_detectable_difference=1.0,
        confidence_level_pct=90.0,
        statistical_power_pct=80.0,
    )
    alpha_cfg = next(p for p in res_cfg.parameter_audit if "alpha" in p.parameter_name)
    assert alpha_cfg.normative_status == "PROJECT_CONFIGURED"
    power_cfg = next(p for p in res_cfg.parameter_audit if "power" in p.parameter_name)
    assert power_cfg.normative_status == "PROJECT_CONFIGURED"


def test_vt0014_matrix():
    """
    Test Section 41: VT0014 Test Matrix:
    - Direct measured SOC without DSM -> NOT_APPLICABLE
    - QA1 model initialized with DSM -> VT0014 REQUIRED
    - QA1 true-up using DSM -> VT0014 REQUIRED
    - QA2 mapped SOC predictions -> VT0014 REQUIRED
    - VT0014 without its 2025 C&C -> BLOCKED / RULESET_INCOMPLETE
    """
    # 1. Direct measured SOC without DSM -> NOT_APPLICABLE
    res_direct = resolve_quantification_routes(
        project_config={"quantification_approach": "APPROACH_2", "dsm_pathway_mode": "DSM_NOT_SELECTED"}
    )
    assert res_direct.requires_vt0014 is False
    assert res_direct.vt0014_status == "NOT_APPLICABLE"

    # 2. QA1 model initialized with DSM -> REQUIRED
    res_qa1_init = resolve_quantification_routes(
        project_config={
            "quantification_approach": "APPROACH_1",
            "dsm_pathway_mode": "DSM_QA1_INITIALIZATION",
            "has_vt0014_october_2025_cc": True,
        },
        dsm_run_evidence={"sample_points_count": 10, "spatial_uncertainty_mapped": True, "metrics": {"R2": 0.85}},
    )
    assert res_qa1_init.requires_vt0014 is True
    assert res_qa1_init.dsm_pathway_mode == "DSM_QA1_INITIALIZATION"
    assert res_qa1_init.vt0014_status == "COMPLETE"

    # 3. QA1 true-up using DSM -> REQUIRED
    res_qa1_trueup = resolve_quantification_routes(
        project_config={
            "quantification_approach": "APPROACH_1",
            "dsm_pathway_mode": "DSM_QA1_TRUE_UP",
            "has_vt0014_october_2025_cc": True,
        },
        dsm_run_evidence={"sample_points_count": 10, "spatial_uncertainty_mapped": True, "metrics": {"R2": 0.85}},
    )
    assert res_qa1_trueup.requires_vt0014 is True
    assert res_qa1_trueup.dsm_pathway_mode == "DSM_QA1_TRUE_UP"

    # 4. QA2 mapped SOC predictions -> REQUIRED
    res_qa2_map = resolve_quantification_routes(
        project_config={
            "quantification_approach": "APPROACH_2",
            "dsm_pathway_mode": "DSM_QA2_SOC_MAPPING",
            "has_vt0014_october_2025_cc": True,
        },
        dsm_run_evidence={"sample_points_count": 15, "spatial_uncertainty_mapped": True, "metrics": {"R2": 0.89}},
    )
    assert res_qa2_map.requires_vt0014 is True
    assert res_qa2_map.dsm_pathway_mode == "DSM_QA2_SOC_MAPPING"

    # 5. VT0014 without its 2025 C&C -> RULESET_INCOMPLETE
    res_no_cc = resolve_quantification_routes(
        project_config={
            "quantification_approach": "APPROACH_2",
            "dsm_pathway_mode": "DSM_QA2_SOC_MAPPING",
            "has_vt0014_october_2025_cc": False,
        }
    )
    assert res_no_cc.vt0014_status == "RULESET_INCOMPLETE"



def test_esm_depth_horizons_and_shallow_soil_exception():
    """Verify that fixed 0-30 cm alone fails closed without a deeper bounding layer unless shallow soil exception applies."""
    # Scenario A: 0-30 cm alone without deeper layer -> fails closed
    status_fail, note_fail, details_fail = evaluate_depth_sufficiency(
        layers=[{"depth_upper_cm": 0.0, "depth_lower_cm": 30.0}],
        require_esm_bounding_layer=True,
    )
    assert status_fail == DepthSufficiencyStatus.DEPTH_INSUFFICIENT
    assert details_fail.get("reason_code") == "ESM_DEEPER_BOUNDING_LAYER_MISSING"

    # Scenario B: 0-30 cm + deeper bounding layer (30-60 cm) -> DEPTH_SUFFICIENT
    status_pass, note_pass, details_pass = evaluate_depth_sufficiency(
        layers=[
            {"depth_upper_cm": 0.0, "depth_lower_cm": 30.0},
            {"depth_upper_cm": 30.0, "depth_lower_cm": 60.0},
        ],
        require_esm_bounding_layer=True,
    )
    assert status_pass == DepthSufficiencyStatus.DEPTH_SUFFICIENT
    assert details_pass.get("has_deeper_bounding") is True

    # Scenario C: 0-25 cm with verified shallow soil exception (bedrock at 25 cm) -> SHALLOW_SOIL_EXCEPTION_VALID
    status_shallow, note_shallow, details_shallow = evaluate_depth_sufficiency(
        layers=[{
            "depth_upper_cm": 0.0,
            "depth_lower_cm": 25.0,
            "impeding_layer_present": True,
            "impeding_layer_type": "BEDROCK",
            "impeding_evidence_verified": True,
            "qa_status": "VERIFIED",
        }],
        require_esm_bounding_layer=True,
    )
    assert status_shallow == DepthSufficiencyStatus.SHALLOW_SOIL_EXCEPTION_VALID
    assert details_shallow["layer_type"] == "BEDROCK"

    # Scenario D: Shallow soil exception claimed but unverified -> SHALLOW_SOIL_EXCEPTION_UNVERIFIED
    status_unverified, note_unverified, details_unverified = evaluate_depth_sufficiency(
        layers=[{
            "depth_upper_cm": 0.0,
            "depth_lower_cm": 20.0,
            "impeding_layer_present": True,
            "impeding_layer_type": "BEDROCK",
            "impeding_evidence_verified": False,
            "qa_status": "PENDING",
        }],
        require_esm_bounding_layer=True,
    )
    assert status_unverified == DepthSufficiencyStatus.SHALLOW_SOIL_EXCEPTION_UNVERIFIED


def test_sampling_design_and_power_analysis_advisory():
    """Verify that power analysis is an optional advisory and never a blocking gate (VM0042 Sec 8.2)."""
    # Student's t calculation helper
    power_res = calculate_vm0042_power_analysis(
        expected_variance=2.5,
        minimum_detectable_difference=1.2,
        confidence_level_pct=90.0,
        statistical_power_pct=80.0,
    )
    assert power_res.status == PowerAnalysisStatus.RESULT_AVAILABLE.value
    assert power_res.is_mandatory is False
    assert power_res.calculated_sample_count is not None
    assert power_res.calculated_sample_count > 0

    # Scenario 1: Sampling plan present, power analysis NOT run
    # Invariant: Must return READY_WITH_NONBLOCKING_ADVISORY, blocking_defects empty, advisories present
    assessment_no_pa = evaluate_sampling_design(
        plan_version={
            "sampling_design_type": "STRATIFIED_RANDOM",
            "is_locked": True,
            "target_sample_count": 10,
        },
        actual_points_count=10,
        strata_count=2,
        variance_basis=1.8,
        run_power_analysis=False,
    )
    assert assessment_no_pa.overall_status == DesignSufficiencyStatus.READY_WITH_NONBLOCKING_ADVISORY.value
    assert len(assessment_no_pa.blocking_defects) == 0
    assert assessment_no_pa.power_analysis.status == PowerAnalysisStatus.NOT_RUN.value
    assert any("POWER_ANALYSIS_NOT_RUN" in a for a in assessment_no_pa.advisories)

    # Scenario 2: Sampling plan missing entirely -> BLOCKED
    assessment_no_plan = evaluate_sampling_design(
        plan_version=None,
        actual_points_count=0,
        strata_count=0,
    )
    assert assessment_no_plan.overall_status == DesignSufficiencyStatus.BLOCKED.value
    assert len(assessment_no_plan.blocking_defects) > 0


def test_baseline_lookback_coverage_and_control_sites():
    """Verify that historical lookback coverage fails closed if missing without zero-default assumptions."""
    proj_start = date(2026, 1, 1)

    # Full 3-year historical management coverage (tillage, fertilizer, organic amendments, crop rotation)
    records = [
        {"record_date": "2023-04-10", "record_type": "TILLAGE", "project_id": "P1"},
        {"record_date": "2023-05-15", "record_type": "SYNTHETIC_FERTILIZER", "project_id": "P1"},
        {"record_date": "2024-04-10", "record_type": "ORGANIC_AMENDMENTS", "project_id": "P1"},
        {"record_date": "2024-06-01", "record_type": "CROP_ROTATION", "project_id": "P1"},
        {"record_date": "2025-03-20", "record_type": "TILLAGE", "project_id": "P1"},
        {"record_date": "2025-05-10", "record_type": "SYNTHETIC_FERTILIZER", "project_id": "P1"},
    ]
    res_full = evaluate_management_history_coverage(proj_start, records, lookback_years=3)
    assert res_full.status == "READY"
    assert res_full.is_complete is True
    assert len(res_full.missing_categories) == 0

    # Missing historical lookback coverage -> INCOMPLETE
    empty_records = []
    res_empty = evaluate_management_history_coverage(proj_start, empty_records, lookback_years=3)
    assert res_empty.status == "INCOMPLETE"
    assert res_empty.is_complete is False
    assert len(res_empty.missing_categories) > 0

    # Approach 2 without control sites -> BLOCKED
    res_app2_no_control = evaluate_baseline_control_sites(
        soc_approach="APPROACH_2",
        control_sites=[],
        quantification_units=["QU-01"],
    )
    assert res_app2_no_control.status == "BLOCKED"
    assert res_app2_no_control.is_required is True

    # Approach 1 with no control sites -> NOT_APPLICABLE
    res_app1 = evaluate_baseline_control_sites(
        soc_approach="APPROACH_1",
        control_sites=[],
        quantification_units=["QU-01"],
    )
    assert res_app1.status == "NOT_APPLICABLE"
    assert res_app1.is_required is False


# =============================================================================
# INTEGRATION TESTS: Database Persistence, Immutability & RBAC
# =============================================================================

@pytest_asyncio.fixture
async def setup_phase3b0_environment():
    """Creates an isolated enterprise organization, project, users (PM, QA, Field Agent, Auditor), land units and strata."""
    tag = uuid.uuid4().hex[:8]
    now = datetime.now(timezone.utc)
    today = now.date()

    async with async_session_factory() as session:
        # Organization
        org = Organization(
            id=uuid.uuid4(),
            name=f"Phase 3B-0 Agriculture Org {tag}",
            plan="ENTERPRISE",
            org_type="DEVELOPER",
        )
        session.add(org)

        # Users
        pm_user = User(
            id=uuid.uuid4(),
            email=f"pm.{tag}@phase3b0.test",
            password_hash=get_password_hash("VeriField_2026!"),
            full_name="Phase 3B Project Manager",
            role="PROJECT_MANAGER",
            organization_id=org.id,
            is_active=True,
            status="active",
        )
        qa_user = User(
            id=uuid.uuid4(),
            email=f"qa.{tag}@phase3b0.test",
            password_hash=get_password_hash("VeriField_2026!"),
            full_name="Lead MRV QA Officer",
            role="QA_OFFICER",
            organization_id=org.id,
            is_active=True,
            status="active",
        )
        field_agent = User(
            id=uuid.uuid4(),
            email=f"agent.{tag}@phase3b0.test",
            password_hash=get_password_hash("VeriField_2026!"),
            full_name="Tariq Field Agent",
            role="FIELD_AGENT",
            organization_id=org.id,
            is_active=True,
            status="active",
        )
        auditor = User(
            id=uuid.uuid4(),
            email=f"auditor.{tag}@phase3b0.test",
            password_hash=get_password_hash("VeriField_2026!"),
            full_name="External VVB Auditor",
            role="AUDITOR",
            organization_id=org.id,
            is_active=True,
            status="active",
        )
        session.add_all([pm_user, qa_user, field_agent, auditor])
        await session.flush()

        # Methodology
        fam = (await session.execute(select(MethodologyFamily).where(MethodologyFamily.code == "AGRICULTURE_LAND_USE"))).scalars().first()
        vm = (await session.execute(select(Methodology).where(Methodology.code == "VM0042"))).scalars().first()
        v22 = None
        if vm:
            v22 = (await session.execute(select(MethodologyVersion).where(MethodologyVersion.methodology_id == vm.id))).scalars().first()

        # Project
        proj = Project(
            id=uuid.uuid4(),
            name=f"Phase 3B-0 Agricultural Project {tag}",
            project_code=f"AGR-3B0-{tag[:6]}",
            organization_id=org.id,
            sector_id=fam.id if fam else None,
            methodology_id=vm.id if vm else None,
            methodology_version_id=v22.id if v22 else None,
            crediting_start=date(2026, 1, 1),
            crediting_end=date(2046, 12, 31),
            baseline_parameters={
                "soil_depth_standard_cm": 30.0,
                "locked_methodology_version": {
                    "methodology_code": "VM0042",
                    "version": "2.2",
                    "corrections_clarifications_version": "2026-06-11",
                    "rule_set_version": "VM0042_V2.2_RULES_CC20260611_V1.0",
                    "status": "LOCKED",
                    "locked_at": now.isoformat(),
                },
                "historical_lookback_years": 3.0,
                "historical_management_events_count": 12,
            },
        )
        session.add(proj)
        await session.flush()

        # Project Boundary Version
        boundary = ProjectBoundaryVersion(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            version_number=1,
            effective_date=date(2026, 1, 1),
            boundary_geojson={
                "type": "Polygon",
                "coordinates": [[[77.10, 28.50], [77.15, 28.50], [77.15, 28.55], [77.10, 28.55], [77.10, 28.50]]],
            },
            geom="SRID=4326;POLYGON((77.10 28.50, 77.15 28.50, 77.15 28.55, 77.10 28.55, 77.10 28.50))",
            area_ha=120.5,
        )
        session.add(boundary)

        # Land Unit
        lu = LandUnit(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            code=f"LU-3B-{tag[:4]}",
            name="North Sector Field Plot",
            area_ha=Decimal("120.5"),
            boundary_geojson={
                "type": "Polygon",
                "coordinates": [[[77.10, 28.50], [77.15, 28.50], [77.15, 28.55], [77.10, 28.55], [77.10, 28.50]]],
            },
            geom="SRID=4326;POLYGON((77.10 28.50, 77.15 28.50, 77.15 28.55, 77.10 28.55, 77.10 28.50))",
            is_active=True,
        )
        session.add(lu)
        await session.flush()

        # Stratum
        stratum = Stratum(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            code=f"STRAT-CLAY-{tag[:4]}",
            name="Clay Loam Flat Stratum",
            stratum_type="SOIL_TYPE",
            area_ha=Decimal("120.5"),
            is_active=True,
        )
        session.add(stratum)
        await session.flush()

        # Stratum Membership (Observation Date in validity window)
        membership = StratumMembership(
            id=uuid.uuid4(),
            organization_id=org.id,
            stratum_id=stratum.id,
            land_unit_id=lu.id,
            valid_from=date(2025, 1, 1),
            valid_to=None,
            status="ACTIVE",
        )
        session.add(membership)

        # Sampling Campaign (Baseline)
        campaign = SamplingCampaign(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            campaign_code=f"CAMP-3B-{tag[:4]}",
            name="Baseline Soil Survey Campaign",
            purpose="BASELINE_SOC_DETERMINATION",
            baseline_or_monitoring_context="BASELINE",
            planned_start_date=date(2026, 1, 10),
            planned_end_date=date(2026, 1, 25),
            status="COMPLETE",
            project_boundary_version_id=boundary.id,
        )
        session.add(campaign)
        await session.flush()

        # Sampling Plan Version (Locked)
        plan_version = SamplingPlanVersion(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            campaign_id=campaign.id,
            version_number=1,
            status="LOCKED",
            effective_as_of_date=date(2026, 1, 15),
            is_locked=True,
            locked_at=now,
            locked_by_id=pm_user.id,
        )
        session.add(plan_version)
        await session.flush()

        # Sampling Points: Layer 1 (0-30cm) & Layer 2 (30-60cm deeper bounding)
        pt1 = SamplingPoint(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            campaign_id=campaign.id,
            plan_version_id=plan_version.id,
            land_unit_id=lu.id,
            point_code=f"SP-3B-01-{tag[:4]}",
            planned_lat=28.52,
            planned_lon=77.12,
            depth_from_cm=0.0,
            depth_to_cm=30.0,
            status="COLLECTED",
        )
        pt2 = SamplingPoint(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            campaign_id=campaign.id,
            plan_version_id=plan_version.id,
            land_unit_id=lu.id,
            point_code=f"SP-3B-02-{tag[:4]}",
            planned_lat=28.52,
            planned_lon=77.12,
            depth_from_cm=30.0,
            depth_to_cm=60.0,
            status="COLLECTED",
        )
        session.add_all([pt1, pt2])
        await session.flush()

        # Physical Soil Samples
        sample1 = PhysicalSample(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            campaign_id=campaign.id,
            plan_version_id=plan_version.id,
            sampling_point_id=pt1.id,
            land_unit_id=lu.id,
            sample_code=f"SMP-3B-01-{tag[:4]}",
            status="QA_ACCEPTED",
        )
        sample2 = PhysicalSample(
            id=uuid.uuid4(),
            organization_id=org.id,
            project_id=proj.id,
            campaign_id=campaign.id,
            plan_version_id=plan_version.id,
            sampling_point_id=pt2.id,
            land_unit_id=lu.id,
            sample_code=f"SMP-3B-02-{tag[:4]}",
            status="QA_ACCEPTED",
        )
        session.add_all([sample1, sample2])
        await session.flush()

        # Collection Events
        ev1 = SampleCollectionEvent(
            id=uuid.uuid4(),
            physical_sample_id=sample1.id,
            sampling_point_id=pt1.id,
            actual_lat=28.52005,
            actual_lon=77.12005,
            actual_depth_from_cm=0.0,
            actual_depth_to_cm=30.0,
            collection_timestamp=datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc),
            collector_name="Tariq Field Agent",
            sample_condition="GOOD",
        )
        ev2 = SampleCollectionEvent(
            id=uuid.uuid4(),
            physical_sample_id=sample2.id,
            sampling_point_id=pt2.id,
            actual_lat=28.52005,
            actual_lon=77.12005,
            actual_depth_from_cm=30.0,
            actual_depth_to_cm=60.0,
            collection_timestamp=datetime(2026, 1, 15, 10, 30, tzinfo=timezone.utc),
            collector_name="Tariq Field Agent",
            sample_condition="GOOD",
        )
        session.add_all([ev1, ev2])

        # Custody Events
        cust1 = ChainOfCustodyEvent(
            id=uuid.uuid4(),
            physical_sample_id=sample1.id,
            event_type="TRANSFER",
            event_timestamp=datetime(2026, 1, 16, 9, 0, tzinfo=timezone.utc),
            custodian_name="Courier Alpha",
            custodian_organization="Agri Logistics",
            seal_intact=True,
            seal_identifier=f"SEAL-01-{tag[:4]}",
        )
        cust2 = ChainOfCustodyEvent(
            id=uuid.uuid4(),
            physical_sample_id=sample2.id,
            event_type="TRANSFER",
            event_timestamp=datetime(2026, 1, 16, 9, 0, tzinfo=timezone.utc),
            custodian_name="Courier Alpha",
            custodian_organization="Agri Logistics",
            seal_intact=True,
            seal_identifier=f"SEAL-02-{tag[:4]}",
        )
        session.add_all([cust1, cust2])

        # Laboratory Receipts
        rcp1 = LaboratoryReceipt(
            id=uuid.uuid4(),
            physical_sample_id=sample1.id,
            laboratory_name="Certified AgroSoil Analytics Inc.",
            received_at=datetime(2026, 1, 18, 11, 0, tzinfo=timezone.utc),
            received_by_name="Lab Intake Specialist",
            intake_status="ACCEPTED",
        )
        rcp2 = LaboratoryReceipt(
            id=uuid.uuid4(),
            physical_sample_id=sample2.id,
            laboratory_name="Certified AgroSoil Analytics Inc.",
            received_at=datetime(2026, 1, 18, 11, 0, tzinfo=timezone.utc),
            received_by_name="Lab Intake Specialist",
            intake_status="ACCEPTED",
        )
        session.add_all([rcp1, rcp2])

        # Laboratory Analyses
        ana1 = LaboratoryAnalysis(
            id=uuid.uuid4(),
            physical_sample_id=sample1.id,
            laboratory_name="Certified AgroSoil Analytics Inc.",
            analytical_method="DRY_COMBUSTION",
            analysis_date=date(2026, 1, 20),
            qa_status="VERIFIED",
        )
        ana2 = LaboratoryAnalysis(
            id=uuid.uuid4(),
            physical_sample_id=sample2.id,
            laboratory_name="Certified AgroSoil Analytics Inc.",
            analytical_method="DRY_COMBUSTION",
            analysis_date=date(2026, 1, 20),
            qa_status="VERIFIED",
        )
        session.add_all([ana1, ana2])
        await session.flush()

        # Laboratory Results: Sample 1 (0-30cm)
        res_soc1 = LaboratoryResult(
            id=uuid.uuid4(),
            analysis_id=ana1.id,
            physical_sample_id=sample1.id,
            analyte="SOC_CONCENTRATION",
            raw_value=Decimal("1.85"),
            raw_unit="%",
            normalized_value=Decimal("18.5"),
            normalized_unit="g/kg",
            normalization_method="LINEAR_SCALING:VAL*10",
            normalization_version="UNIT_CONV_V1.0",
            is_superseded=False,
        )
        res_bd1 = LaboratoryResult(
            id=uuid.uuid4(),
            analysis_id=ana1.id,
            physical_sample_id=sample1.id,
            analyte="BULK_DENSITY_G_CM3",
            raw_value=Decimal("1.32"),
            raw_unit="g/cm3",
            normalized_value=Decimal("1.32"),
            normalized_unit="g/cm³",
            is_superseded=False,
        )
        res_cf1 = LaboratoryResult(
            id=uuid.uuid4(),
            analysis_id=ana1.id,
            physical_sample_id=sample1.id,
            analyte="COARSE_FRAGMENTS_PERCENT",
            raw_value=Decimal("0.0"),
            raw_unit="%",
            normalized_value=Decimal("0.0"),
            normalized_unit="fraction",
            is_superseded=False,
        )

        # Laboratory Results: Sample 2 (30-60cm)
        res_soc2 = LaboratoryResult(
            id=uuid.uuid4(),
            analysis_id=ana2.id,
            physical_sample_id=sample2.id,
            analyte="SOC_CONCENTRATION",
            raw_value=Decimal("1.20"),
            raw_unit="%",
            normalized_value=Decimal("12.0"),
            normalized_unit="g/kg",
            normalization_method="LINEAR_SCALING:VAL*10",
            normalization_version="UNIT_CONV_V1.0",
            is_superseded=False,
        )
        res_bd2 = LaboratoryResult(
            id=uuid.uuid4(),
            analysis_id=ana2.id,
            physical_sample_id=sample2.id,
            analyte="BULK_DENSITY_G_CM3",
            raw_value=Decimal("1.45"),
            raw_unit="g/cm3",
            normalized_value=Decimal("1.45"),
            normalized_unit="g/cm³",
            is_superseded=False,
        )
        session.add_all([res_soc1, res_bd1, res_cf1, res_soc2, res_bd2])
        await session.flush()

        # QA Reviews
        qa1 = SampleQAReview(
            id=uuid.uuid4(),
            physical_sample_id=sample1.id,
            reviewer_name="Lead MRV QA Officer",
            overall_qa_status="ACCEPTED",
            review_date=datetime(2026, 1, 22, 14, 0, tzinfo=timezone.utc),
        )
        qa2 = SampleQAReview(
            id=uuid.uuid4(),
            physical_sample_id=sample2.id,
            reviewer_name="Lead MRV QA Officer",
            overall_qa_status="ACCEPTED",
            review_date=datetime(2026, 1, 22, 14, 0, tzinfo=timezone.utc),
        )
        session.add_all([qa1, qa2])
        await session.commit()

        return {
            "org": org,
            "project": proj,
            "pm_user": pm_user,
            "qa_user": qa_user,
            "field_agent": field_agent,
            "auditor": auditor,
            "sample_layer1": sample1,
            "sample_layer2": sample2,
        }


@pytest.mark.asyncio
async def test_prerequisite_assessment_immutability_and_lineage(setup_phase3b0_environment):
    """Verify that locking prerequisite assessments is immutable and versioned with SHA-256 lineage."""
    data = setup_phase3b0_environment
    project = data["project"]
    pm_user = data["pm_user"]

    async with async_session_factory() as session:
        # 1. Evaluate prerequisites
        eval_result = await AgricultureService.evaluate_methodology_prerequisites(
            db=session,
            project_id=project.id,
            organization_id=project.organization_id,
            run_power_analysis=False,
        )
        assert eval_result["overall_status"] in ("READY", "READY_WITH_ADVISORY")
        assert len(eval_result["dimensions"]) == 17
        assert len(eval_result["evaluation_hash"]) == 64

        # 2. Lock Prerequisite Assessment Version 1
        dossier_v1 = await AgricultureService.lock_prerequisite_assessment(
            db=session,
            project_id=project.id,
            organization_id=project.organization_id,
            user_id=pm_user.id,
            user_role=pm_user.role,
            notes="Official Baseline Prerequisite Evaluation Lock",
            run_power_analysis=False,
        )
        assert dossier_v1.version == 1
        assert dossier_v1.status == "LOCKED"
        assert dossier_v1.is_locked is True
        assert dossier_v1.assessment_hash is not None
        assert len(dossier_v1.assessment_hash) == 64
        assert dossier_v1.superseded_by_id is None

        # 3. Lock Version 2 (e.g. after parameter update) -> Version 1 must become SUPERSEDED
        dossier_v2 = await AgricultureService.lock_prerequisite_assessment(
            db=session,
            project_id=project.id,
            organization_id=project.organization_id,
            user_id=pm_user.id,
            user_role=pm_user.role,
            notes="Second lock updating advisory notes",
            run_power_analysis=True,
            target_mdd=1.2,
        )
        assert dossier_v2.version == 2
        assert dossier_v2.status == "LOCKED"
        assert dossier_v2.id != dossier_v1.id

        # Verify database state: Version 1 is SUPERSEDED by Version 2
        old_v1 = (await session.execute(
            select(AgriculturePrerequisiteAssessment).where(AgriculturePrerequisiteAssessment.id == dossier_v1.id)
        )).scalars().first()
        assert old_v1.status == "SUPERSEDED"
        assert old_v1.superseded_by_id == dossier_v2.id


@pytest.mark.asyncio
async def test_prerequisite_fail_closed_null_carbon(setup_phase3b0_environment):
    """Verify that prerequisite assessment strictly fails closed with NULL carbon quantities."""
    data = setup_phase3b0_environment
    project = data["project"]
    pm_user = data["pm_user"]

    async with async_session_factory() as session:
        dossier = await AgricultureService.lock_prerequisite_assessment(
            db=session,
            project_id=project.id,
            organization_id=project.organization_id,
            user_id=pm_user.id,
            user_role=pm_user.role,
        )
        # Ensure that no carbon estimates are generated or stored in assessment
        # The dossier must contain methodology evaluation, route mapping, ESM horizons, but NO carbon metrics
        assert "soc_stock_t_per_ha" not in dossier.dimensions
        assert "delta_soc_tco2e" not in dossier.dimensions
        assert "net_removals_tco2e" not in dossier.dimensions


@pytest.mark.asyncio
async def test_prerequisite_rbac_segregation_of_duties(setup_phase3b0_environment):
    """Verify that FIELD_AGENT is blocked from locking prerequisite assessments (HTTP 403 / SoD)."""
    data = setup_phase3b0_environment
    project = data["project"]
    field_agent = data["field_agent"]
    pm_user = data["pm_user"]
    auditor = data["auditor"]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create tokens
        agent_token = AuthenticationService.generate_token_static(field_agent)
        pm_token = AuthenticationService.generate_token_static(pm_user)
        auditor_token = AuthenticationService.generate_token_static(auditor)

        # 1. FIELD_AGENT attempts to lock prerequisite assessment -> MUST FAIL WITH HTTP 403
        resp_agent = await client.post(
            f"/api/v1/agriculture/projects/{project.id}/prerequisites/lock",
            headers={"Authorization": f"Bearer {agent_token}"},
            json={"notes": "Field agent unauthorized lock attempt"},
        )
        assert resp_agent.status_code == 403
        assert any(m in resp_agent.text for m in ("FIELD_AGENT", "Field agents", "Access Denied"))

        # 2. AUDITOR attempts to view assessments -> MUST SUCCEED (Read-only)
        resp_auditor = await client.get(
            f"/api/v1/agriculture/projects/{project.id}/prerequisites/assessments",
            headers={"Authorization": f"Bearer {auditor_token}"},
        )
        assert resp_auditor.status_code == 200
        assert isinstance(resp_auditor.json(), list)

        # 3. PROJECT_MANAGER locks prerequisite assessment -> MUST SUCCEED HTTP 200
        resp_pm = await client.post(
            f"/api/v1/agriculture/projects/{project.id}/prerequisites/lock",
            headers={"Authorization": f"Bearer {pm_token}"},
            json={"notes": "PM authorized lock"},
        )
        assert resp_pm.status_code in (200, 201)
        body = resp_pm.json()
        assert body["assessment_code"].startswith("PREREQ-")
        assert body["status"] == "LOCKED"
        assert len(body["assessment_hash"]) == 64


@pytest.mark.asyncio
async def test_prerequisite_tenant_isolation(setup_phase3b0_environment):
    """Verify cross-tenant isolation: Foreign organization cannot access or evaluate project prerequisites."""
    data = setup_phase3b0_environment
    project = data["project"]

    async with async_session_factory() as session:
        # Create a foreign org and foreign PM user
        foreign_org = Organization(
            id=uuid.uuid4(),
            name=f"Adversarial Foreign Org {uuid.uuid4().hex[:6]}",
            plan="ENTERPRISE",
            org_type="DEVELOPER",
        )
        session.add(foreign_org)
        foreign_user = User(
            id=uuid.uuid4(),
            email=f"intruder.{uuid.uuid4().hex[:6]}@foreign.test",
            password_hash=get_password_hash("Intruder_2026!"),
            full_name="Foreign PM User",
            role="PROJECT_MANAGER",
            organization_id=foreign_org.id,
            is_active=True,
            status="active",
        )
        session.add(foreign_user)
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        foreign_token = AuthenticationService.generate_token_static(foreign_user)

        # Attempt to evaluate foreign project prerequisites -> MUST FAIL 404 or 403
        resp = await client.get(
            f"/api/v1/agriculture/projects/{project.id}/prerequisites/readiness",
            headers={"Authorization": f"Bearer {foreign_token}"},
        )
        assert resp.status_code in (403, 404)

        # Attempt to lock foreign project prerequisites -> MUST FAIL 404 or 403
        resp_lock = await client.post(
            f"/api/v1/agriculture/projects/{project.id}/prerequisites/lock",
            headers={"Authorization": f"Bearer {foreign_token}"},
            json={"notes": "Malicious foreign lock"},
        )
        assert resp_lock.status_code in (403, 404)
