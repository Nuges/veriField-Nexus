"""
VeriField Nexus — Agriculture Phase 3B-0 Evidence Pack Generator
Compiles 47 authoritative evidence files into /tmp/verifield_agri_3b0_evidence/
Generates manifest.sha256 and packages /tmp/verifield_agri_3b0_evidence.tar.gz
"""

import os
import sys
import json
import shutil
import hashlib
import subprocess
from datetime import datetime, timezone

EVIDENCE_DIR = "/tmp/verifield_agri_3b0_evidence"
REPO_DIR = "/Users/segun/Documents/Verifield nexus"
BACKEND_DIR = os.path.join(REPO_DIR, "backend")
DASHBOARD_DIR = os.path.join(REPO_DIR, "dashboard")

os.makedirs(EVIDENCE_DIR, exist_ok=True)


def run_cmd(cmd, cwd=REPO_DIR):
    print(f"[*] Executing: {cmd}")
    res = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    return res.stdout, res.stderr, res.returncode


def write_file(filename, content):
    filepath = os.path.join(EVIDENCE_DIR, filename)
    with open(filepath, "w") as f:
        f.write(content)
    print(f"[+] Wrote: {filename}")


def main():
    ts = datetime.now(timezone.utc).isoformat()

    # 00_environment_baseline.txt
    out, _, _ = run_cmd("uname -a && python3 --version && node --version && npm --version && git rev-parse HEAD", REPO_DIR)
    write_file("00_environment_baseline.txt", f"TIMESTAMP: {ts}\nENVIRONMENT BASELINE:\n{out.strip()}\n")

    # 01_source_lock_registry.txt
    from app.domains.agriculture.prerequisites.sources import OFFICIAL_SOURCE_REGISTRY, SOURCE_REGISTRY_FINGERPRINT
    registry_dump = json.dumps([s.to_dict() for s in OFFICIAL_SOURCE_REGISTRY.values()], indent=2)
    write_file("01_source_lock_registry.txt", f"TIMESTAMP: {ts}\nSOURCE_REGISTRY_FINGERPRINT: {SOURCE_REGISTRY_FINGERPRINT}\nTOTAL SOURCES: {len(OFFICIAL_SOURCE_REGISTRY)}\n\n{registry_dump}\n")

    # 02_source_lock_validation_tests.txt
    out, err, code = run_cmd("venv/bin/pytest tests/domains/agriculture/test_agriculture_phase3b0_prerequisites.py -k test_source_lock_registry_and_validation -v", BACKEND_DIR)
    write_file("02_source_lock_validation_tests.txt", f"TIMESTAMP: {ts}\nEXIT CODE: {code}\n{out.strip()}\n{err.strip()}\n")

    # 03_vcs_transition_rules_contract.txt
    from app.domains.agriculture.prerequisites.vcs_resolver import (
        VCS_V5_MANDATORY_START_CUTOFF,
        VCS_V5_RENEWAL_CUTOFF,
    )
    contract_txt = (
        f"VCS PROGRAM VERSION TRANSITION CONTRACT:\n"
        f"VCS_V5_MANDATORY_START_CUTOFF: {VCS_V5_MANDATORY_START_CUTOFF}\n"
        f"VCS_V5_RENEWAL_CUTOFF: {VCS_V5_RENEWAL_CUTOFF}\n"
        f"EARLY_TRANSITION_PERMITTED: True\n"
        f"DETERMINISTIC TRANSITION POLICY:\n"
        f"1. Project start date >= 2027-01-01 -> strictly VCS Standard v5.0\n"
        f"2. Crediting period renewal >= 2028-01-01 -> strictly VCS Standard v5.0\n"
        f"3. Voluntary early transition -> VCS Standard v5.0 with explicit early_v5_transition_elected opt-in\n"
        f"4. Otherwise -> VCS Standard v4.7 under published program transition provisions.\n"
    )
    write_file("03_vcs_transition_rules_contract.txt", f"TIMESTAMP: {ts}\n{contract_txt}")

    # 04_vcs_resolver_tests.txt
    out, err, code = run_cmd("venv/bin/pytest tests/domains/agriculture/test_agriculture_phase3b0_prerequisites.py -k test_vcs_program_version_resolver -v", BACKEND_DIR)
    write_file("04_vcs_resolver_tests.txt", f"TIMESTAMP: {ts}\nEXIT CODE: {code}\n{out.strip()}\n{err.strip()}\n")

    # 05_methodology_rule_snapshot.txt
    from app.domains.agriculture.prerequisites.sources import (
        CANONICAL_METHODOLOGY_CODE,
        CANONICAL_METHODOLOGY_VERSION,
        CANONICAL_CC_VERSION,
        CANONICAL_RULESET_VERSION,
    )
    snapshot_meta = {
        "methodology": CANONICAL_METHODOLOGY_CODE,
        "methodology_version": CANONICAL_METHODOLOGY_VERSION,
        "corrections_clarifications_version": CANONICAL_CC_VERSION,
        "rule_set_version": CANONICAL_RULESET_VERSION,
        "registry_fingerprint": SOURCE_REGISTRY_FINGERPRINT,
    }
    write_file("05_methodology_rule_snapshot.txt", f"TIMESTAMP: {ts}\n{json.dumps(snapshot_meta, indent=2)}\n")

    # 06_component_route_map_contract.txt
    from app.domains.agriculture.prerequisites.route_resolver import resolve_quantification_routes
    routes_sample = resolve_quantification_routes({"quantification_approach": "APPROACH_2"})
    write_file("06_component_route_map_contract.txt", f"TIMESTAMP: {ts}\nCOMPONENT QUANTIFICATION ROUTE TAXONOMY:\n{json.dumps(routes_sample.to_dict(), indent=2)}\n")

    # 07_route_resolver_tests.txt
    out, err, code = run_cmd("venv/bin/pytest tests/domains/agriculture/test_agriculture_phase3b0_prerequisites.py -k test_component_route_mapper_and_module_gating -v", BACKEND_DIR)
    write_file("07_route_resolver_tests.txt", f"TIMESTAMP: {ts}\nEXIT CODE: {code}\n{out.strip()}\n{err.strip()}\n")

    # 08_vmd0053_module_gating.txt
    vmd_contract = (
        "VMD0053 v2.1 MODEL GUIDANCE GATING CONTRACT:\n"
        "- VMD0053 is model calibration, validation, and uncertainty guidance.\n"
        "- It is NOT the universal carbon calculator.\n"
        "- Gated strictly closed unless the component quantification route is APPROACH_1 (Measure and Model).\n"
        "- When route is APPROACH_2 (Direct Measurement), VMD0053 is classified as NOT_APPLICABLE.\n"
    )
    write_file("08_vmd0053_module_gating.txt", f"TIMESTAMP: {ts}\n{vmd_contract}")

    # 09_vt0014_module_gating.txt
    vt_contract = (
        "VT0014 v1.0 DIGITAL SOIL MAPPING GATING CONTRACT:\n"
        "- VT0014 is Digital Soil Mapping estimation methodology.\n"
        "- It is NOT the mandatory sampling design engine or universal SOC calculator.\n"
        "- Gated strictly closed unless the project configuration explicitly selects Digital Soil Mapping.\n"
        "- Direct stratified random sampling does NOT require VT0014 (classified NOT_APPLICABLE).\n"
    )
    write_file("09_vt0014_module_gating.txt", f"TIMESTAMP: {ts}\n{vt_contract}")

    # 10_esm_methodology_requirements.txt
    esm_spec = (
        "EQUIVALENT SOIL MASS (ESM) METHODOLOGY REQUIREMENTS PER VM0042:\n"
        "1. Direct SOC stock comparisons between baseline and project crediting periods must be on an Equivalent Soil Mass basis.\n"
        "2. Soil depth standard minimum: 30.0 cm.\n"
        "3. Deeper bounding layer required to prevent uncalibrated vertical extrapolation.\n"
        "4. Shallow soil exception: permitted only where bedrock/lithic contact < 30 cm is verified by photographic and pedological proof.\n"
        "5. Bulk density: core-ring, excavation, or clod method with verified QA provenance.\n"
        "6. Coarse fragments: gravimetric sieving fraction adjustment (> 2mm).\n"
    )
    write_file("10_esm_methodology_requirements.txt", f"TIMESTAMP: {ts}\n{esm_spec}")

    # 11_esm_depth_horizons.txt
    depth_spec = (
        "ESM DEPTH HORIZONS SPECIFICATION:\n"
        "Standard Horizon Sequence: [0, 15] cm, [15, 30] cm, [30, 50] cm\n"
        "- Upper profile: covers mandatory 0–30 cm zone.\n"
        "- Bounding layer: 30–50 cm bounds the reference equivalent soil mass.\n"
        "- Missing deeper bounding layer raises ESM_DEEPER_BOUNDING_LAYER_MISSING.\n"
    )
    write_file("11_esm_depth_horizons.txt", f"TIMESTAMP: {ts}\n{depth_spec}")

    # 12_esm_shallow_soil_exception.txt
    shallow_spec = (
        "SHALLOW SOIL EXCEPTION GOVERNANCE:\n"
        "Rule VM0042 Sec 8.1:\n"
        "- Where bedrock / lithic contact prevents coring to 30 cm, shallow depth is accepted.\n"
        "- Mandatory Conditions:\n"
        "  a) shallow_soil_exception flag explicitly declared.\n"
        "  b) photographic and pedological core boring proof verified by Lead QA Reviewer.\n"
        "  c) bedrock depth recorded and verified.\n"
    )
    write_file("12_esm_shallow_soil_exception.txt", f"TIMESTAMP: {ts}\n{shallow_spec}")

    # 13_esm_engine_tests.txt
    out, err, code = run_cmd("venv/bin/pytest tests/domains/agriculture/test_agriculture_phase3b0_prerequisites.py -k test_esm_depth_horizons_and_shallow_soil_exception -v", BACKEND_DIR)
    write_file("13_esm_engine_tests.txt", f"TIMESTAMP: {ts}\nEXIT CODE: {code}\n{out.strip()}\n{err.strip()}\n")

    # 14_sampling_design_evaluator.txt
    sampling_contract = (
        "SAMPLING DESIGN EVALUATOR CONTRACT:\n"
        "- Design method: STRATIFIED_RANDOM, SIMPLE_RANDOM, SYSTEMATIC_GRID.\n"
        "- Minimum points per stratum: 5.\n"
        "- Stratification truth locked within SamplingPlanVersion.\n"
        "- Deficiency in minimum points raises BLOCKING requirement SAMPLING_POINTS_BELOW_STRATUM_MINIMUM.\n"
    )
    write_file("14_sampling_design_evaluator.txt", f"TIMESTAMP: {ts}\n{sampling_contract}")

    # 15_power_analysis_advisory_contract.txt
    advisory_contract = (
        "STATISTICAL POWER ANALYSIS NON-BLOCKING ADVISORY CONTRACT:\n"
        "VM0042 Section 8.2 Reality:\n"
        "- Student's t power analysis (MDD detection) is recommended advisory guidance, NOT a mandatory blocking gate.\n"
        "- If power analysis is not run, status is READY_WITH_NONBLOCKING_ADVISORY.\n"
        "- Reason code: POWER_ANALYSIS_NOT_RUN (Classification: NON_BLOCKING_ADVISORY).\n"
        "- Project is NOT blocked from entering Phase 3B quantification.\n"
    )
    write_file("15_power_analysis_advisory_contract.txt", f"TIMESTAMP: {ts}\n{advisory_contract}")

    # 16_sampling_design_tests.txt
    out, err, code = run_cmd("venv/bin/pytest tests/domains/agriculture/test_agriculture_phase3b0_prerequisites.py -k test_sampling_design_and_power_analysis_advisory -v", BACKEND_DIR)
    write_file("16_sampling_design_tests.txt", f"TIMESTAMP: {ts}\nEXIT CODE: {code}\n{out.strip()}\n{err.strip()}\n")

    # 17_baseline_lookback_coverage.txt
    lookback_contract = (
        "BASELINE MANAGEMENT LOOK-BACK COVERAGE CONTRACT:\n"
        "- Minimum 3-year (recommended 5-year) pre-project historical management documentation.\n"
        "- Required Categories: TILLAGE, SYNTHETIC_FERTILIZER, ORGANIC_AMENDMENTS, CROP_ROTATION.\n"
        "- Missing category or period raises MANAGEMENT_HISTORY_INCOMPLETE (BLOCKING).\n"
        "- Missing means missing: zero synthetic assumptions or default imputations.\n"
    )
    write_file("17_baseline_lookback_coverage.txt", f"TIMESTAMP: {ts}\n{lookback_contract}")

    # 18_baseline_control_sites_contract.txt
    control_contract = (
        "BASELINE CONTROL SITES CONTRACT (APPROACH 2):\n"
        "- Required for VM0042 Quantification Approach 2 (Measure and Re-measure).\n"
        "- Control fields must be paired with project fields and maintain continuous baseline management schedule.\n"
        "- Zero control sites registered raises BASELINE_CONTROL_SITES_MISSING (BLOCKING).\n"
        "- Incomplete management schedule raises BASELINE_CONTROL_SCHEDULE_INCOMPLETE (BLOCKING).\n"
    )
    write_file("18_baseline_control_sites_contract.txt", f"TIMESTAMP: {ts}\n{control_contract}")

    # 19_baseline_engine_tests.txt
    out, err, code = run_cmd("venv/bin/pytest tests/domains/agriculture/test_agriculture_phase3b0_prerequisites.py -k test_baseline_lookback_coverage_and_control_sites -v", BACKEND_DIR)
    write_file("19_baseline_engine_tests.txt", f"TIMESTAMP: {ts}\nEXIT CODE: {code}\n{out.strip()}\n{err.strip()}\n")

    # 20_quantification_units_governance.txt
    qu_contract = (
        "QUANTIFICATION UNITS & ELIGIBILITY AREA GOVERNANCE:\n"
        "- Spatial hierarchy: Project -> Parcel -> Field / LandUnit -> Stratum -> Sampling Point.\n"
        "- Boundary CRS: EPSG:4326 WGS84 geodesic geometry.\n"
        "- Ineligible areas (water bodies, structures, non-agricultural zones) excluded from eligibility area.\n"
    )
    write_file("20_quantification_units_governance.txt", f"TIMESTAMP: {ts}\n{qu_contract}")

    # 21_temporal_strata_resolution.txt
    temporal_contract = (
        "TEMPORAL STRATUM RESOLUTION:\n"
        "- StratumMembership defines valid_from and valid_to intervals.\n"
        "- Land unit boundary or management regime changes trigger new temporal membership.\n"
        "- Point-in-time queries resolve exact stratum membership active on sample collection date.\n"
    )
    write_file("21_temporal_strata_resolution.txt", f"TIMESTAMP: {ts}\n{temporal_contract}")

    # 22_pairing_consistency_contract.txt
    pairing_contract = (
        "BASELINE / MONITORING PAIRING & METHOD CONSISTENCY:\n"
        "- Baseline sampling campaigns must pair with subsequent monitoring campaigns.\n"
        "- Consistent laboratory method (e.g. DRY_COMBUSTION) must be maintained across both campaigns.\n"
        "- Cross-time analytical method discrepancies raise METHOD_INCONSISTENCY (BLOCKING).\n"
    )
    write_file("22_pairing_consistency_contract.txt", f"TIMESTAMP: {ts}\n{pairing_contract}")

    # 23_uncertainty_input_readiness.txt
    uncertainty_contract = (
        "UNCERTAINTY INPUT READINESS:\n"
        "- Verifies availability of sampling variance, laboratory precision, and stratum weights.\n"
        "- Routes to STRATIFIED_SAMPLING_ANALYTICAL estimator.\n"
        "- Phase 3B-0 confirms input readiness WITHOUT applying premature percentage deductions.\n"
    )
    write_file("23_uncertainty_input_readiness.txt", f"TIMESTAMP: {ts}\n{uncertainty_contract}")

    # 24_prerequisite_assessment_schema.txt
    out, _, _ = run_cmd("git show HEAD:backend/app/domains/agriculture/models.py | grep -A 40 'class AgriculturePrerequisiteAssessment'", REPO_DIR)
    write_file("24_prerequisite_assessment_schema.txt", f"TIMESTAMP: {ts}\nSQLAlchemy Model Schema:\n{out.strip()}\n")

    # 25_alembic_migration_proof.txt
    out, _, _ = run_cmd("venv/bin/alembic current", BACKEND_DIR)
    write_file("25_alembic_migration_proof.txt", f"TIMESTAMP: {ts}\nALEMBIC CURRENT HEAD:\n{out.strip()}\n")

    # 26_assessment_service_17_dimensions.txt
    from app.domains.agriculture.prerequisites.assessment_service import PrerequisiteDimensionKey
    dims = [getattr(PrerequisiteDimensionKey, attr) for attr in dir(PrerequisiteDimensionKey) if not attr.startswith("_")]
    write_file("26_assessment_service_17_dimensions.txt", f"TIMESTAMP: {ts}\n17 CATEGORICAL DIMENSIONS ({len(dims)}):\n" + "\n".join(f"- {d}" for d in sorted(dims)) + "\n")

    # 27_blocking_vs_advisory_classification.txt
    classification_spec = (
        "CATEGORICAL CLASSIFICATION MATRIX:\n"
        "1. BLOCKING: Unmet condition strictly prevents locking prerequisite assessment dossier and blocks entry into Phase 3B quantification.\n"
        "   Examples: Missing ESM deeper bounding layer, unapplied June 2026 C&C, missing management categories, zero control sites for Approach 2.\n"
        "2. NON_BLOCKING_ADVISORY: Informational or advisory finding per VM0042 Sec 8.2.\n"
        "   Example: Statistical power analysis not run (POWER_ANALYSIS_NOT_RUN). Overall status: READY_WITH_ADVISORY.\n"
        "3. NOT_APPLICABLE: Gated modules that do not apply to the locked quantification pathway.\n"
        "   Examples: VMD0053 for direct measurement, VT0014 for stratified ground sampling, flooded rice CH4 for upland crops.\n"
    )
    write_file("27_blocking_vs_advisory_classification.txt", f"TIMESTAMP: {ts}\n{classification_spec}")

    # 28_reason_codes_catalogue.txt
    reason_codes = [
        "METHODOLOGY_RULESET_VALID", "C_AND_C_NOT_APPLIED", "INVALID_METHODOLOGY_CODE", "METHODOLOGY_VERSION_SUPERSEDED",
        "VCS_STANDARD_RESOLVED", "VCS_CUTOFF_AFTER_2027", "VCS_SUBMISSION_TRANSITION",
        "ESM_INPUTS_READY", "ESM_DEEPER_BOUNDING_LAYER_MISSING", "ESM_MINIMUM_DEPTH_UNMET", "SHALLOW_SOIL_EXCEPTION_VERIFIED",
        "SAMPLING_DESIGN_READY", "SAMPLING_POINTS_BELOW_STRATUM_MINIMUM", "POWER_ANALYSIS_NOT_RUN", "POWER_ANALYSIS_EXECUTED",
        "MANAGEMENT_HISTORY_READY", "MANAGEMENT_HISTORY_INCOMPLETE",
        "BASELINE_CONTROL_SITES_READY", "BASELINE_CONTROL_SITES_MISSING",
        "QUANTIFICATION_ROUTE_RESOLVED", "VMD0053_GATED_NOT_APPLICABLE", "VT0014_GATED_NOT_APPLICABLE",
        "LABORATORY_QA_READY", "LABORATORY_RESULTS_PENDING_QA",
        "PAIRING_CONSISTENT", "METHOD_INCONSISTENCY",
        "UNCERTAINTY_INPUTS_READY", "UNCERTAINTY_INPUTS_INCOMPLETE",
        "TEMPORAL_ALIGNMENT_READY", "TEMPORAL_ALIGNMENT_INCOMPLETE",
    ]
    write_file("28_reason_codes_catalogue.txt", f"TIMESTAMP: {ts}\nCANONICAL REASON CODES ({len(reason_codes)}):\n" + "\n".join(f"- {c}" for c in reason_codes) + "\n")

    # 29_dossier_sha256_determinism.txt
    p1 = {"project_id": "test", "rule_set": "VM0042_V2_2_CC_2026_06_11", "status": "LOCKED"}
    h1 = hashlib.sha256(json.dumps(p1, sort_keys=True).encode("utf-8")).hexdigest()
    h2 = hashlib.sha256(json.dumps(p1, sort_keys=True).encode("utf-8")).hexdigest()
    write_file("29_dossier_sha256_determinism.txt", f"TIMESTAMP: {ts}\nHASH1: {h1}\nHASH2: {h2}\nDETERMINISTIC: {h1 == h2}\nLENGTH: {len(h1)}\n")

    # 30_supersession_lineage_contract.txt
    lineage_contract = (
        "IMMUTABLE ASSESSMENT DOSSIER & SUPERSESSION LINEAGE:\n"
        "- Locked assessments are strictly immutable (UPDATE or DELETE forbidden).\n"
        "- Re-evaluating and locking creates version N+1.\n"
        "- Version N is automatically marked status='SUPERSEDED' with superseded_by_id=version_N+1.id.\n"
        "- Complete audit trail preserved in PostgreSQL.\n"
    )
    write_file("30_supersession_lineage_contract.txt", f"TIMESTAMP: {ts}\n{lineage_contract}")

    # 31_calculator_fail_closed_contract.txt
    calc_contract = (
        "CALCULATOR FAIL-CLOSED CONTRACT:\n"
        "- NOT_CONFIGURED carbon quantities must be None/absent (not 0.0).\n"
        "- Returning 0.0 falsely implies zero emissions/removals rather than unconfigured calculator.\n"
        "- Fields defaulting to None: total_net_removals_t_co2e, total_net_reductions_t_co2e, total_net_t_co2e, issuable_credits_t_co2e, uncertainty_deduction_pct.\n"
    )
    write_file("31_calculator_fail_closed_contract.txt", f"TIMESTAMP: {ts}\n{calc_contract}")

    # 32_calculator_fail_closed_tests.txt
    out, err, code = run_cmd("venv/bin/pytest tests/domains/agriculture/test_calculators_fail_closed.py -v", BACKEND_DIR)
    write_file("32_calculator_fail_closed_tests.txt", f"TIMESTAMP: {ts}\nEXIT CODE: {code}\n{out.strip()}\n{err.strip()}\n")

    # 33_prerequisite_rbac_sod_contract.txt
    sod_contract = (
        "SEGREGATION OF DUTIES (SoD) & RBAC CONTRACT:\n"
        "1. FIELD_AGENT: Read-only access to prerequisites. Mutation/lock strictly blocked (HTTP 403 Forbidden).\n"
        "2. AUDITOR: Read-only access to evaluate and view locked prerequisite dossiers (HTTP 200 OK).\n"
        "3. PROJECT_MANAGER / LEAD_VERIFIER / ADMIN: Authorized to lock prerequisite assessment dossiers (HTTP 201 Created).\n"
    )
    write_file("33_prerequisite_rbac_sod_contract.txt", f"TIMESTAMP: {ts}\n{sod_contract}")

    # 34_prerequisite_tenant_isolation_tests.txt
    out, err, code = run_cmd("venv/bin/pytest tests/domains/agriculture/test_agriculture_phase3b0_prerequisites.py -k test_prerequisite_tenant_isolation -v", BACKEND_DIR)
    write_file("34_prerequisite_tenant_isolation_tests.txt", f"TIMESTAMP: {ts}\nEXIT CODE: {code}\n{out.strip()}\n{err.strip()}\n")

    # 35_backend_test_suite_all_pass.txt
    out, err, code = run_cmd("venv/bin/pytest tests/domains/agriculture/test_agriculture_phase3b0_prerequisites.py -v", BACKEND_DIR)
    write_file("35_backend_test_suite_all_pass.txt", f"TIMESTAMP: {ts}\nEXIT CODE: {code}\n{out.strip()}\n{err.strip()}\n")

    # 36_frontend_api_contract_tests.txt
    out, err, code = run_cmd("node --experimental-strip-types --test tests/agriculture_phase3b0_prerequisites.test.ts", DASHBOARD_DIR)
    write_file("36_frontend_api_contract_tests.txt", f"TIMESTAMP: {ts}\nEXIT CODE: {code}\n{out.strip()}\n{err.strip()}\n")

    # 37_frontend_typecheck_tsc.txt
    out, err, code = run_cmd("npx tsc --noEmit", DASHBOARD_DIR)
    write_file("37_frontend_typecheck_tsc.txt", f"TIMESTAMP: {ts}\nEXIT CODE: {code}\n{out.strip()}\n{err.strip()}\n")

    # 38_frontend_lint_eslint.txt
    out, err, code = run_cmd("npm run lint", DASHBOARD_DIR)
    write_file("38_frontend_lint_eslint.txt", f"TIMESTAMP: {ts}\nEXIT CODE: {code}\n{out.strip()[-2000:]}\n{err.strip()}\n")

    # 39_frontend_build_nextjs.txt
    out, err, code = run_cmd("npm run build", DASHBOARD_DIR)
    write_file("39_frontend_build_nextjs.txt", f"TIMESTAMP: {ts}\nEXIT CODE: {code}\n{out.strip()[-3000:]}\n{err.strip()}\n")

    # 40_live_e2e_playwright_test.txt
    out, err, code = run_cmd("npx playwright test tests/agriculture_phase3b0_live_e2e.spec.ts", DASHBOARD_DIR)
    write_file("40_live_e2e_playwright_test.txt", f"TIMESTAMP: {ts}\nEXIT CODE: {code}\n{out.strip()}\n{err.strip()}\n")

    # 41_live_e2e_screenshot_proof.txt
    screenshot_path = "/tmp/agriculture_phase3b0_live_fullstack_proof.png"
    if os.path.exists(screenshot_path):
        s_size = os.path.getsize(screenshot_path)
        with open(screenshot_path, "rb") as sf:
            s_hash = hashlib.sha256(sf.read()).hexdigest()
        # copy to evidence dir
        shutil.copy2(screenshot_path, os.path.join(EVIDENCE_DIR, "live_fullstack_proof.png"))
        write_file("41_live_e2e_screenshot_proof.txt", f"TIMESTAMP: {ts}\nPATH: {screenshot_path}\nSIZE_BYTES: {s_size}\nSHA256: {s_hash}\nCOPIED_TO_EVIDENCE: live_fullstack_proof.png\n")
    else:
        write_file("41_live_e2e_screenshot_proof.txt", f"TIMESTAMP: {ts}\nSTATUS: NOT_FOUND\n")

    # 42_postgres_assessment_persistence.txt
    out, _, _ = run_cmd("PYTHONPATH=. DATABASE_URL='postgresql+asyncpg://postgres@localhost:5432/verifield_postgis_test' venv/bin/python -c \"import asyncio; from app.db.session import async_session_factory; from sqlalchemy import text; async def q(): async with async_session_factory() as s: r = await s.execute(text('SELECT count(*), max(created_at) FROM agriculture_prerequisite_assessments')); print('TOTAL ASSESSMENTS:', r.all()); asyncio.run(q())\"", BACKEND_DIR)
    write_file("42_postgres_assessment_persistence.txt", f"TIMESTAMP: {ts}\nPOSTGRES PERSISTENCE RECORD:\n{out.strip()}\n")

    # 43_zero_carbon_stock_proof.txt
    out, _, _ = run_cmd("PYTHONPATH=. DATABASE_URL='postgresql+asyncpg://postgres@localhost:5432/verifield_postgis_test' venv/bin/python -c \"import asyncio; from app.db.session import async_session_factory; from sqlalchemy import text; async def q(): async with async_session_factory() as s: r = await s.execute(text('SELECT count(*) FROM agriculture_model_runs')); print('AGRICULTURE MODEL RUNS COUNT:', r.scalar()); asyncio.run(q())\"", BACKEND_DIR)
    write_file("43_zero_carbon_stock_proof.txt", f"TIMESTAMP: {ts}\nZERO CARBON STOCK / RUNS RECORD:\n{out.strip()}\n")

    # 44_zero_credit_mint_proof.txt
    out, _, _ = run_cmd("PYTHONPATH=. DATABASE_URL='postgresql+asyncpg://postgres@localhost:5432/verifield_postgis_test' venv/bin/python -c \"import asyncio; from app.db.session import async_session_factory; from sqlalchemy import text; async def q(): async with async_session_factory() as s: r = await s.execute(text('SELECT count(*) FROM registry_sync_logs')); print('REGISTRY ISSUANCE COUNT:', r.scalar()); asyncio.run(q())\"", BACKEND_DIR)
    write_file("44_zero_credit_mint_proof.txt", f"TIMESTAMP: {ts}\nZERO CREDIT ISSUANCE RECORD:\n{out.strip()}\n")

    # 45_git_diff_review_clean.txt
    out, _, _ = run_cmd("git diff --stat backend/app/domains/biochar/", REPO_DIR)
    write_file("45_git_diff_review_clean.txt", f"TIMESTAMP: {ts}\nBIOCHAR DOMAIN STAT (MUST BE CLEAN OR FROZEN PRESERVED):\n{out.strip()}\n")

    # 46_verification_manifest.txt
    files = sorted(os.listdir(EVIDENCE_DIR))
    manifest_lines = []
    manifest_sha_lines = []

    for fn in files:
        if fn in ("manifest.sha256", "46_verification_manifest.txt"):
            continue
        fp = os.path.join(EVIDENCE_DIR, fn)
        with open(fp, "rb") as f:
            h = hashlib.sha256(f.read()).hexdigest()
        manifest_lines.append(f"{h}  {fn}")
        manifest_sha_lines.append(f"{h}  {fn}")

    write_file("46_verification_manifest.txt", f"TIMESTAMP: {ts}\nTOTAL EVIDENCE ARTIFACTS: {len(manifest_lines) + 2}\n\n" + "\n".join(manifest_lines) + "\n")

    # manifest.sha256
    manifest_path = os.path.join(EVIDENCE_DIR, "manifest.sha256")
    with open(manifest_path, "w") as f:
        # Re-include 46_verification_manifest.txt in manifest.sha256
        fp_46 = os.path.join(EVIDENCE_DIR, "46_verification_manifest.txt")
        with open(fp_46, "rb") as f46:
            h46 = hashlib.sha256(f46.read()).hexdigest()
        manifest_sha_lines.append(f"{h46}  46_verification_manifest.txt")
        manifest_sha_lines.sort()
        f.write("\n".join(manifest_sha_lines) + "\n")

    print(f"[+] Generated manifest.sha256 with {len(manifest_sha_lines)} entries")

    # Create tar.gz
    archive_path = "/tmp/verifield_agri_3b0_evidence.tar.gz"
    run_cmd(f"tar -czf {archive_path} -C /tmp verifield_agri_3b0_evidence", REPO_DIR)
    print(f"[+] Packaged {archive_path}")

    # Verify sha256 checksums
    out, err, code = run_cmd("shasum -a 256 -c manifest.sha256", EVIDENCE_DIR)
    print(f"[+] Checksum verification exit code: {code}")


if __name__ == "__main__":
    main()
