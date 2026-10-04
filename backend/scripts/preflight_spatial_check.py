#!/usr/bin/env python3
"""
=============================================================================
VeriField Nexus — Production Spatial & Database Preflight Verification
=============================================================================
Deployment preflight check:
1. DB reachable
2. PostgreSQL version >= 15.0
3. PostGIS installed & version >= 3.3.0
4. Alembic at expected head (e5f6a7b8c9d0)
5. Required typed Geometry columns exist
6. Required GiST spatial indexes exist

Exits 0 on PASS, 1 on FAIL.
Does not mutate the database.
=============================================================================
"""

import sys
import os
import re
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

EXPECTED_HEADS = ["e6f7a8b9c0d1", "d5e6f7a8b9c0", "c4d5e6f7a8b9", "b2c3d4e5f6a8", "a1b2c3d4e5f7", "f6a7b8c9d0e1"]
MIN_PG_VERSION = 15.0
MIN_POSTGIS_VERSION = (3, 3, 0)

REQUIRED_GEOMETRY_COLUMNS = [
    ("project_boundary_versions", "geom"),
    ("eo_areas_of_interest", "geom"),
    ("eo_observations", "footprint_geom"),
    ("eo_spatial_anomalies", "geom"),
    ("land_units", "geom"),
    ("sampling_points", "geom"),
    ("sample_collection_events", "actual_geom"),
]

REQUIRED_GIST_INDEXES = [
    "idx_project_boundary_versions_geom",
    "idx_eo_areas_of_interest_geom",
    "idx_eo_observations_footprint_geom",
    "idx_eo_spatial_anomalies_geom",
    "idx_land_units_geom",
    "idx_sampling_points_geom",
    "idx_sample_collection_events_actual_geom",
]


def parse_version_tuple(v_str: str):
    m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", v_str)
    if not m:
        return (0, 0, 0)
    major = int(m.group(1))
    minor = int(m.group(2))
    patch = int(m.group(3)) if m.group(3) else 0
    return (major, minor, patch)


async def run_preflight(database_url: str) -> bool:
    print("=" * 70)
    print("VeriField Nexus — Production Spatial Preflight Check")
    print("=" * 70)

    # Sanitize URL for logging
    sanitized_url = re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", database_url)
    print(f"Target Database: {sanitized_url}")

    failures = []

    # 1. Connect
    try:
        engine = create_async_engine(database_url, echo=False)
        async with engine.connect() as conn:
            # 2. Check Dialect
            dialect_name = engine.dialect.name
            print(f"[*] Dialect: {dialect_name}")

            if dialect_name == "sqlite":
                print("[!] SQLite detected: Supported for local test/dev only.")
                print("[!] GiST indexes and PostGIS native predicates are unavailable.")
                return True

            if dialect_name != "postgresql":
                failures.append(f"Unsupported database dialect: {dialect_name}")
                print(f"[FAIL] {failures[-1]}")
                return False

            # 3. PostgreSQL Version
            try:
                pg_ver_str = await conn.scalar(text("SHOW server_version;"))
                print(f"[*] PostgreSQL Server Version: {pg_ver_str}")
                pg_tuple = parse_version_tuple(pg_ver_str)
                if pg_tuple[0] < MIN_PG_VERSION:
                    failures.append(
                        f"PostgreSQL version {pg_ver_str} is below minimum requirement ({MIN_PG_VERSION}+)."
                    )
                    print(f"[FAIL] {failures[-1]}")
                else:
                    print(f"[PASS] PostgreSQL version {pg_ver_str} >= {MIN_PG_VERSION}")
            except Exception as e:
                await conn.rollback()
                failures.append(f"Failed to query PostgreSQL server_version: {e}")
                print(f"[FAIL] {failures[-1]}")

            # 4. PostGIS Extension & Version
            try:
                postgis_ver = await conn.scalar(text("SELECT postgis_version();"))
                print(f"[*] PostGIS Version: {postgis_ver}")
                postgis_tuple = parse_version_tuple(postgis_ver)
                if postgis_tuple < MIN_POSTGIS_VERSION:
                    failures.append(
                        f"PostGIS version {postgis_ver} is below minimum requirement ({MIN_POSTGIS_VERSION})."
                    )
                    print(f"[FAIL] {failures[-1]}")
                else:
                    print(f"[PASS] PostGIS version {postgis_ver} >= {MIN_POSTGIS_VERSION}")
            except Exception as e:
                await conn.rollback()
                failures.append(f"PostGIS extension missing or unreachable: {e}")
                print(f"[FAIL] {failures[-1]}")

            # 5. Alembic Head
            try:
                alembic_head = await conn.scalar(text("SELECT version_num FROM alembic_version LIMIT 1;"))
                print(f"[*] Current Alembic Head: {alembic_head}")
                if alembic_head not in EXPECTED_HEADS:
                    failures.append(
                        f"Alembic version {alembic_head} does not match expected head(s) {EXPECTED_HEADS}."
                    )
                    print(f"[FAIL] {failures[-1]}")
                else:
                    print(f"[PASS] Alembic head matches expected ({alembic_head})")
            except Exception as e:
                await conn.rollback()
                failures.append(f"Failed to verify alembic_version table: {e}")
                print(f"[FAIL] {failures[-1]}")

            # 6. Geometry Columns
            for tbl, col in REQUIRED_GEOMETRY_COLUMNS:
                try:
                    udt = await conn.scalar(text(f"""
                        SELECT udt_name FROM information_schema.columns
                        WHERE table_schema = 'public' AND table_name = '{tbl}' AND column_name = '{col}';
                    """))
                    if udt == "geometry":
                        print(f"[PASS] Column {tbl}.{col} is typed PostGIS geometry")
                    else:
                        failures.append(f"Column {tbl}.{col} has udt_name='{udt}', expected 'geometry'")
                        print(f"[FAIL] {failures[-1]}")
                except Exception as e:
                    await conn.rollback()
                    failures.append(f"Failed to inspect column {tbl}.{col}: {e}")
                    print(f"[FAIL] {failures[-1]}")

            # 7. GiST Indexes
            for idx in REQUIRED_GIST_INDEXES:
                try:
                    exists = await conn.scalar(text(f"""
                        SELECT 1 FROM pg_indexes
                        WHERE schemaname = 'public' AND indexname = '{idx}';
                    """))
                    if exists:
                        print(f"[PASS] Spatial GiST Index '{idx}' exists")
                    else:
                        failures.append(f"Spatial GiST Index '{idx}' does not exist")
                        print(f"[FAIL] {failures[-1]}")
                except Exception as e:
                    await conn.rollback()
                    failures.append(f"Failed to inspect index {idx}: {e}")
                    print(f"[FAIL] {failures[-1]}")

        await engine.dispose()
    except Exception as e:
        failures.append(f"Database connection failed: {e}")
        print(f"[FAIL] {failures[-1]}")

    print("=" * 70)
    if failures:
        print(f"PREFLIGHT FAILED: {len(failures)} error(s) detected:")
        for f in failures:
            print(f"  - {f}")
        return False
    else:
        print("PREFLIGHT PASSED: All database and PostGIS spatial requirements met.")
        return True


if __name__ == "__main__":
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL environment variable is required.")
        sys.exit(1)

    # Normalize url driver for asyncpg
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    success = asyncio.run(run_preflight(db_url))
    sys.exit(0 if success else 1)
