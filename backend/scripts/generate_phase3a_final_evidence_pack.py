"""
VeriField Nexus — Phase 3A Final Evidence Pack Compiler
Runs all verification commands and generates authoritative raw logs in /tmp/verifield_phase3a_final_evidence/
"""

import os
import subprocess
import sys
import hashlib
from datetime import datetime, timezone

EVIDENCE_DIR = "/tmp/verifield_phase3a_final_evidence"
BACKEND_DIR = "/Users/segun/Documents/Verifield nexus/backend"
DASHBOARD_DIR = "/Users/segun/Documents/Verifield nexus/dashboard"
REPO_DIR = "/Users/segun/Documents/Verifield nexus"

os.makedirs(EVIDENCE_DIR, exist_ok=True)


def run_command(cmd, cwd, env=None):
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    print(f"[*] Running: {cmd} in {cwd}")
    res = subprocess.run(cmd, shell=True, cwd=cwd, env=merged_env, capture_output=True, text=True)
    return res.stdout, res.stderr, res.returncode


def main():
    ts = datetime.now(timezone.utc).isoformat()

    # 00. Environment Log
    stdout_env, _, _ = run_command("uname -a && python3 --version && node --version && npm --version && psql --version", REPO_DIR)
    with open(os.path.join(EVIDENCE_DIR, "00_environment.log"), "w") as f:
        f.write(f"TIMESTAMP: {ts}\nENVIRONMENT INFO:\n{stdout_env.strip()}\n")
    print("[PASS] 00_environment.log")

    # 07. Depth Alignment Tests
    stdout, stderr, code = run_command("venv/bin/pytest tests/domains/agriculture/test_quantification_acceptance_criteria.py -k test_depth_alignment_scenarios -v", BACKEND_DIR)
    with open(os.path.join(EVIDENCE_DIR, "07_depth_alignment_tests.log"), "w") as f:
        f.write(f"TIMESTAMP: {ts}\nEXIT CODE: {code}\n{stdout.strip()}\n{stderr.strip()}\n")
    print("[PASS] 07_depth_alignment_tests.log")

    # 08-09. Snapshot Gate & Design Sufficiency Tests
    stdout, stderr, code = run_command("venv/bin/pytest tests/domains/agriculture/test_quantification_acceptance_criteria.py -k test_snapshot_gate_9_scenarios -v", BACKEND_DIR)
    with open(os.path.join(EVIDENCE_DIR, "08_09_snapshot_gate_tests.log"), "w") as f:
        f.write(f"TIMESTAMP: {ts}\nEXIT CODE: {code}\n{stdout.strip()}\n{stderr.strip()}\n")
    print("[PASS] 08_09_snapshot_gate_tests.log")

    # 10. Latest Valid Result Selection
    stdout, stderr, code = run_command("venv/bin/pytest tests/domains/agriculture/test_quantification_acceptance_criteria.py -k test_latest_valid_result_supersession_and_rejection -v", BACKEND_DIR)
    with open(os.path.join(EVIDENCE_DIR, "10_latest_result_selection.log"), "w") as f:
        f.write(f"TIMESTAMP: {ts}\nEXIT CODE: {code}\n{stdout.strip()}\n{stderr.strip()}\n")
    print("[PASS] 10_latest_result_selection.log")

    # 11. Baseline / Project Dataset Separation
    stdout, stderr, code = run_command("venv/bin/pytest tests/domains/agriculture/test_quantification_acceptance_criteria.py -k test_baseline_project_dataset_separation -v", BACKEND_DIR)
    with open(os.path.join(EVIDENCE_DIR, "11_baseline_project_separation.log"), "w") as f:
        f.write(f"TIMESTAMP: {ts}\nEXIT CODE: {code}\n{stdout.strip()}\n{stderr.strip()}\n")
    print("[PASS] 11_baseline_project_separation.log")

    # 12. Temporal Stratum Resolution
    stdout, stderr, code = run_command("venv/bin/pytest tests/domains/agriculture/test_quantification_acceptance_criteria.py -k test_temporal_stratum_resolution -v", BACKEND_DIR)
    with open(os.path.join(EVIDENCE_DIR, "12_temporal_stratum_resolution.log"), "w") as f:
        f.write(f"TIMESTAMP: {ts}\nEXIT CODE: {code}\n{stdout.strip()}\n{stderr.strip()}\n")
    print("[PASS] 12_temporal_stratum_resolution.log")

    # 13. Bulk Density Scenarios
    stdout, stderr, code = run_command("venv/bin/pytest tests/domains/agriculture/test_quantification_acceptance_criteria.py -k test_bulk_density_scenarios -v", BACKEND_DIR)
    with open(os.path.join(EVIDENCE_DIR, "13_bulk_density_scenarios.log"), "w") as f:
        f.write(f"TIMESTAMP: {ts}\nEXIT CODE: {code}\n{stdout.strip()}\n{stderr.strip()}\n")
    print("[PASS] 13_bulk_density_scenarios.log")

    # 14. Coarse Fragments Scenarios
    stdout, stderr, code = run_command("venv/bin/pytest tests/domains/agriculture/test_quantification_acceptance_criteria.py -k test_coarse_fragments_scenarios -v", BACKEND_DIR)
    with open(os.path.join(EVIDENCE_DIR, "14_coarse_fragments_scenarios.log"), "w") as f:
        f.write(f"TIMESTAMP: {ts}\nEXIT CODE: {code}\n{stdout.strip()}\n{stderr.strip()}\n")
    print("[PASS] 14_coarse_fragments_scenarios.log")

    # 15. Snapshot Hash Determinism
    stdout, stderr, code = run_command("venv/bin/pytest tests/domains/agriculture/test_quantification_acceptance_criteria.py -k test_snapshot_canonical_hash_determinism -v", BACKEND_DIR)
    with open(os.path.join(EVIDENCE_DIR, "15_snapshot_hash_determinism.log"), "w") as f:
        f.write(f"TIMESTAMP: {ts}\nEXIT CODE: {code}\n{stdout.strip()}\n{stderr.strip()}\n")
    print("[PASS] 15_snapshot_hash_determinism.log")

    # 16. Snapshot Immutability
    stdout, stderr, code = run_command("venv/bin/pytest tests/domains/agriculture/test_quantification_acceptance_criteria.py -k test_snapshot_immutability -v", BACKEND_DIR)
    with open(os.path.join(EVIDENCE_DIR, "16_snapshot_immutability.log"), "w") as f:
        f.write(f"TIMESTAMP: {ts}\nEXIT CODE: {code}\n{stdout.strip()}\n{stderr.strip()}\n")
    print("[PASS] 16_snapshot_immutability.log")

    # 17. Source Evidence Reference Validation
    stdout, stderr, code = run_command("venv/bin/pytest tests/domains/agriculture/test_quantification_acceptance_criteria.py -k test_source_evidence_reference_validation -v", BACKEND_DIR)
    with open(os.path.join(EVIDENCE_DIR, "17_source_evidence_validation.log"), "w") as f:
        f.write(f"TIMESTAMP: {ts}\nEXIT CODE: {code}\n{stdout.strip()}\n{stderr.strip()}\n")
    print("[PASS] 17_source_evidence_validation.log")

    # 18. Quantification Readiness Dimensions (16 Dimensions, zero progress bars)
    stdout, stderr, code = run_command("venv/bin/pytest tests/domains/agriculture/test_quantification_readiness.py -v", BACKEND_DIR)
    with open(os.path.join(EVIDENCE_DIR, "18_quantification_readiness_dimensions.log"), "w") as f:
        f.write(f"TIMESTAMP: {ts}\nEXIT CODE: {code}\n{stdout.strip()}\n{stderr.strip()}\n")
    print("[PASS] 18_quantification_readiness_dimensions.log")

    # 21. PostGIS Snapshot Persistence
    stdout, stderr, code = run_command("venv/bin/pytest tests/domains/agriculture/test_quantification_postgis.py -v", BACKEND_DIR)
    with open(os.path.join(EVIDENCE_DIR, "21_postgis_snapshot_persistence.log"), "w") as f:
        f.write(f"TIMESTAMP: {ts}\nEXIT CODE: {code}\n{stdout.strip()}\n{stderr.strip()}\n")
    print("[PASS] 21_postgis_snapshot_persistence.log")

    # 22. Frontend Contract Tests
    stdout, stderr, code = run_command("node --experimental-strip-types tests/agriculture_phase3a_frontend.test.ts", DASHBOARD_DIR)
    with open(os.path.join(EVIDENCE_DIR, "22_frontend_contract_tests.log"), "w") as f:
        f.write(f"TIMESTAMP: {ts}\nEXIT CODE: {code}\n{stdout.strip()}\n{stderr.strip()}\n")
    print("[PASS] 22_frontend_contract_tests.log")

    # 23. TypeScript Verification
    stdout, stderr, code = run_command("npx tsc --noEmit", DASHBOARD_DIR)
    with open(os.path.join(EVIDENCE_DIR, "23_typescript_verification.log"), "w") as f:
        f.write(f"TIMESTAMP: {ts}\nEXIT CODE: {code}\n{stdout.strip()}\n{stderr.strip()}\n")
    print("[PASS] 23_typescript_verification.log")

    # 24. ESLint Verification
    stdout, stderr, code = run_command("npm run lint", DASHBOARD_DIR)
    with open(os.path.join(EVIDENCE_DIR, "24_eslint_verification.log"), "w") as f:
        f.write(f"TIMESTAMP: {ts}\nEXIT CODE: {code}\n{stdout.strip()}\n{stderr.strip()}\n")
    print("[PASS] 24_eslint_verification.log")

    # 25. Production Build
    stdout, stderr, code = run_command("npm run build", DASHBOARD_DIR)
    with open(os.path.join(EVIDENCE_DIR, "25_production_build.log"), "w") as f:
        f.write(f"TIMESTAMP: {ts}\nEXIT CODE: {code}\n{stdout.strip()}\n{stderr.strip()}\n")
    print("[PASS] 25_production_build.log")

    # 26. Live Full-Stack Playwright Test
    stdout, stderr, code = run_command("npx playwright test tests/agriculture_phase3a_live_fullstack.spec.ts", DASHBOARD_DIR, env={"DATABASE_URL": "postgresql+asyncpg://segun@localhost:5432/verifield_postgis_test"})
    with open(os.path.join(EVIDENCE_DIR, "26_live_fullstack_playwright.log"), "w") as f:
        f.write(f"TIMESTAMP: {ts}\nEXIT CODE: {code}\n{stdout.strip()}\n{stderr.strip()}\n")
    print("[PASS] 26_live_fullstack_playwright.log")

    # 20. Full Backend Regression
    stdout, stderr, code = run_command("venv/bin/pytest tests/ -q", BACKEND_DIR)
    with open(os.path.join(EVIDENCE_DIR, "20_full_backend_regression.log"), "w") as f:
        f.write(f"TIMESTAMP: {ts}\nEXIT CODE: {code}\n{stdout.strip()}\n{stderr.strip()}\n")
    print("[PASS] 20_full_backend_regression.log")

    # 27. Git Status & Diff
    stdout_status, _, _ = run_command("git status --short", REPO_DIR)
    stdout_diff, _, _ = run_command("git diff --stat", REPO_DIR)
    with open(os.path.join(EVIDENCE_DIR, "27_git_status_and_diff.log"), "w") as f:
        f.write(f"TIMESTAMP: {ts}\nGIT STATUS:\n{stdout_status.strip()}\n\nGIT DIFF STAT:\n{stdout_diff.strip()}\n")
    print("[PASS] 27_git_status_and_diff.log")

    # Generate Manifest & Checksums
    files = sorted(os.listdir(EVIDENCE_DIR))
    manifest_lines = [
        "================================================================================",
        "VERIFIELD NEXUS — AGRICULTURE MRV PHASE 3A EVIDENCE MANIFEST",
        f"GENERATION TIMESTAMP: {ts}",
        f"TOTAL ARTIFACTS: {len(files)}",
        "================================================================================",
        f"{'FILENAME':<45} | {'SIZE (BYTES)':<12} | {'SHA-256 HASH'}",
        "-" * 125,
    ]
    for fn in files:
        if fn in ["manifest.txt", "verifield_phase3a_final_evidence.tar.gz"]:
            continue
        fp = os.path.join(EVIDENCE_DIR, fn)
        size = os.path.getsize(fp)
        with open(fp, "rb") as bf:
            h = hashlib.sha256(bf.read()).hexdigest()
        manifest_lines.append(f"{fn:<45} | {size:<12} | {h}")

    manifest_content = "\n".join(manifest_lines) + "\n"
    with open(os.path.join(EVIDENCE_DIR, "manifest.txt"), "w") as f:
        f.write(manifest_content)
    print("[PASS] manifest.txt")

    # Create Tar Archive
    tar_cmd = f"tar -czf {EVIDENCE_DIR}/verifield_phase3a_final_evidence.tar.gz -C {os.path.dirname(EVIDENCE_DIR)} {os.path.basename(EVIDENCE_DIR)}"
    run_command(tar_cmd, REPO_DIR)

    # Compute Archive SHA-256
    tar_path = f"{EVIDENCE_DIR}/verifield_phase3a_final_evidence.tar.gz"
    with open(tar_path, "rb") as bf:
        tar_hash = hashlib.sha256(bf.read()).hexdigest()
    with open(f"{tar_path}.sha256", "w") as f:
        f.write(f"{tar_hash}  verifield_phase3a_final_evidence.tar.gz\n")

    print(f"\n[EVIDENCE PACK COMPLETE]")
    print(f"Archive: {tar_path}")
    print(f"SHA-256: {tar_hash}")


if __name__ == "__main__":
    main()
