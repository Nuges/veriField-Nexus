"""
VeriField Nexus — Clean Migration Test on PostgreSQL
===================================================
Tests upgrading a completely fresh database from base to HEAD (b2c3d4e5f6a8),
verifies preflight_spatial_check.py passes with exit code 0,
verifies all geometry columns and spatial indexes are created automatically,
and records execution evidence.
"""

import os
import subprocess
import sys
from sqlalchemy import create_engine, text

TEST_DB_NAME = "verifield_clean_b2_test"
SYNC_DB_URL = f"postgresql://segun@localhost:5432/{TEST_DB_NAME}"


def run_cmd(cmd: str, env_vars=None):
    current_env = os.environ.copy()
    if env_vars:
        current_env.update(env_vars)
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=current_env)
    return res


def main():
    print("=" * 70)
    print("AGRICULTURE MRV PHASE 2: CLEAN MIGRATION TEST")
    print("=" * 70)

    # 1. Create fresh DB
    print("\n[Step 1] Creating fresh disposable database...")
    subprocess.run(f"dropdb --if-exists {TEST_DB_NAME}", shell=True)
    res_cdb = run_cmd(f"createdb {TEST_DB_NAME}")
    if res_cdb.returncode != 0:
        raise RuntimeError(f"createdb failed: {res_cdb.stderr}")
    print(f"Created database: {TEST_DB_NAME}")

    # 2. Run Alembic upgrade head
    print("\n[Step 2] Executing Alembic upgrade head from scratch...")
    res_mig = run_cmd(f'venv/bin/alembic upgrade head', env_vars={"DATABASE_URL": SYNC_DB_URL})
    print(f"Migration return code: {res_mig.returncode}")
    print("Migration STDOUT:\n" + res_mig.stdout)
    print("Migration STDERR:\n" + res_mig.stderr)
    if res_mig.returncode != 0:
        raise RuntimeError("Alembic upgrade head failed on clean database!")

    # 3. Run preflight spatial check against the clean DB
    print("\n[Step 3] Running preflight_spatial_check.py against clean database...")
    res_preflight = run_cmd(f'venv/bin/python scripts/preflight_spatial_check.py', env_vars={"DATABASE_URL": SYNC_DB_URL})
    print(f"Preflight return code: {res_preflight.returncode}")
    print(res_preflight.stdout)
    print(res_preflight.stderr)
    if res_preflight.returncode != 0:
        raise RuntimeError("Preflight spatial check failed on clean database!")

    # 4. Verify geometry columns and GiST indexes directly via SQL
    print("\n[Step 4] Direct PostGIS catalog inspection...")
    engine = create_engine(SYNC_DB_URL)
    with engine.connect() as conn:
        geom_cols = conn.execute(text("""
            SELECT f_table_name, f_geometry_column, srid, type
            FROM geometry_columns
            WHERE f_table_schema = 'public'
            ORDER BY f_table_name, f_geometry_column;
        """)).fetchall()

        print(f"Found {len(geom_cols)} geometry columns:")
        for r in geom_cols:
            print(f"  - Table: {r[0]}, Column: {r[1]}, SRID: {r[2]}, Type: {r[3]}")
        assert len(geom_cols) >= 7

        gist_idx = conn.execute(text("""
            SELECT tablename, indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = 'public' AND indexdef LIKE '%USING gist%'
            ORDER BY tablename, indexname;
        """)).fetchall()

        print(f"\nFound {len(gist_idx)} GiST spatial indexes:")
        for r in gist_idx:
            print(f"  - Table: {r[0]}, Index: {r[1]}")
        assert len(gist_idx) >= 7

    engine.dispose()

    # 5. Clean up
    print("\n[Step 5] Dropping clean disposable database...")
    subprocess.run(f"dropdb {TEST_DB_NAME}", shell=True)
    print(f"Dropped database: {TEST_DB_NAME}")

    print("\n" + "=" * 70)
    print("CLEAN MIGRATION TEST: PASS (100% Fresh DB Upgrade Verified)")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nFATAL ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
