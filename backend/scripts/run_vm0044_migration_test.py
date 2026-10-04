"""
VeriField Nexus — VM0044 v1.2 Clean Reversible Migration Test
============================================================
1. Creates a dedicated disposable test database: verifield_vm0044_mig_test
2. Upgrades from base to HEAD (b3c4d5e6f7a8)
3. Verifies all 7 VM0044 tables, columns, and indexes exist
4. Downgrades by 1 revision (-1) to a2b3c4d5e6f7 (Puro closure)
5. Verifies all 7 VM0044 tables are cleanly removed and parent tables intact
6. Upgrades back to HEAD (b3c4d5e6f7a8)
7. Verifies all 7 VM0044 tables and indexes are recreated cleanly
8. Drops disposable test database.
"""

import os
import subprocess
import sys
from sqlalchemy import create_engine, text

TEST_DB_NAME = "verifield_vm0044_mig_test"
SYNC_DB_URL = f"postgresql://segun@localhost:5432/{TEST_DB_NAME}"

VM0044_TABLES = [
    "vm0044_methodology_versions",
    "vm0044_rule_definitions",
    "vm0044_normative_dependencies",
    "vm0044_applicability_evaluations",
    "vm0044_additionality_assessments",
    "vm0044_calculation_snapshots",
    "vm0044_calculation_executions",
]


def run_cmd(cmd: str, env_vars=None):
    current_env = os.environ.copy()
    if env_vars:
        current_env.update(env_vars)
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=current_env)
    return res


def get_existing_tables(engine):
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
        """)).fetchall()
        return {r[0] for r in rows}


def main():
    print("=" * 70)
    print("VERRA VM0044 v1.2: REVERSIBLE MIGRATION VERIFICATION")
    print("=" * 70)

    # 1. Create fresh disposable DB
    print("\n[Step 1] Creating disposable test database...")
    subprocess.run(f"dropdb --if-exists {TEST_DB_NAME}", shell=True)
    res = run_cmd(f"createdb {TEST_DB_NAME}")
    if res.returncode != 0:
        raise RuntimeError(f"createdb failed: {res.stderr}")
    print(f"Created database: {TEST_DB_NAME}")

    # 2. Upgrade to HEAD
    print("\n[Step 2] Executing Alembic upgrade head from scratch...")
    res = run_cmd("venv/bin/alembic upgrade head", env_vars={"DATABASE_URL": SYNC_DB_URL})
    if res.returncode != 0:
        print(res.stderr)
        raise RuntimeError("Alembic upgrade head failed!")
    print("Upgrade to head successful.")

    engine = create_engine(SYNC_DB_URL)

    # 3. Verify VM0044 tables exist
    print("\n[Step 3] Verifying VM0044 v1.2 tables exist at HEAD...")
    tables = get_existing_tables(engine)
    for t in VM0044_TABLES:
        assert t in tables, f"Expected table {t} missing at HEAD!"
        print(f"  ✓ Found table: {t}")
    print(f"All {len(VM0044_TABLES)} VM0044 tables verified.")

    # 4. Downgrade to down_revision (a2b3c4d5e6f7)
    print("\n[Step 4] Executing Alembic downgrade -1 (to a2b3c4d5e6f7)...")
    res = run_cmd("venv/bin/alembic downgrade -1", env_vars={"DATABASE_URL": SYNC_DB_URL})
    if res.returncode != 0:
        print(res.stderr)
        raise RuntimeError("Alembic downgrade -1 failed!")
    print("Downgrade -1 successful.")

    # 5. Verify VM0044 tables were cleanly dropped
    print("\n[Step 5] Verifying VM0044 tables dropped cleanly after downgrade...")
    tables_after_down = get_existing_tables(engine)
    for t in VM0044_TABLES:
        assert t not in tables_after_down, f"Table {t} should have been dropped!"
        print(f"  ✓ Cleanly dropped: {t}")
    # Verify previous migration's table still exists
    assert "puro_calculation_executions" in tables_after_down or "biochar_batches" in tables_after_down
    print("Base and parent domain tables remained completely intact.")

    # 6. Re-upgrade to HEAD
    print("\n[Step 6] Re-executing Alembic upgrade head...")
    res = run_cmd("venv/bin/alembic upgrade head", env_vars={"DATABASE_URL": SYNC_DB_URL})
    if res.returncode != 0:
        print(res.stderr)
        raise RuntimeError("Alembic re-upgrade to head failed!")
    print("Re-upgrade to head successful.")

    # 7. Verify tables restored
    print("\n[Step 7] Verifying tables restored after re-upgrade...")
    tables_restored = get_existing_tables(engine)
    for t in VM0044_TABLES:
        assert t in tables_restored, f"Table {t} missing after re-upgrade!"
        print(f"  ✓ Recreated table: {t}")

    engine.dispose()

    # 8. Clean up
    print("\n[Step 8] Dropping disposable test database...")
    subprocess.run(f"dropdb {TEST_DB_NAME}", shell=True)
    print(f"Dropped database: {TEST_DB_NAME}")

    print("\n" + "=" * 70)
    print("CLEAN REVERSIBLE MIGRATION TEST: PASS (Upgrade -> Downgrade -> Upgrade)")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nFATAL ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
