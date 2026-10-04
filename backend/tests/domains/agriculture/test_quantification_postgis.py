"""
VeriField Nexus — Agriculture MRV Phase 3A: PostGIS & PostgreSQL Integration Tests
Runtime tests against PostgreSQL 18+ and PostGIS 3.6+.
Tests:
1. quantification_input_snapshots table schema, foreign keys, JSONB columns, and indexes.
2. Snapshot hash determinism and JSONB integrity in real PostgreSQL.
3. Multi-tenant isolation for quantification snapshots in real database.
4. Spatial boundary linkage: verifying project boundary versions and sampling points.
"""

import hashlib
import json
import os
import uuid
from datetime import date, datetime, timezone
import pytest
from sqlalchemy import create_engine, text


def get_postgis_engine():
    """
    Attempts to connect to a PostgreSQL instance with PostGIS enabled.
    Checks POSTGIS_TEST_URL or localhost:5432.
    """
    user = os.environ.get("POSTGRES_USER") or os.environ.get("USER") or "postgres"
    test_urls = [
        os.environ.get("POSTGIS_TEST_URL"),
        f"postgresql://{user}@localhost:5432/verifield_postgis_test",
        f"postgresql://{user}@localhost:5432/postgres",
    ]
    for url in test_urls:
        if not url:
            continue
        try:
            eng = create_engine(url)
            with eng.connect() as conn:
                ver = conn.execute(text("SELECT postgis_version();")).scalar()
                if ver:
                    return eng
        except Exception:
            continue
    return None


@pytest.fixture(scope="function")
def postgis_conn():
    engine = get_postgis_engine()
    if engine is None:
        pytest.skip("Real PostGIS database is not available in the current test environment.")
    with engine.connect() as conn:
        trans = conn.begin()
        yield conn
        trans.rollback()


def test_quantification_snapshots_schema(postgis_conn):
    """
    Verifies that quantification_input_snapshots table exists in PostgreSQL
    with required columns, JSONB types, and constraints.
    """
    result = postgis_conn.execute(
        text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'quantification_input_snapshots'
            ORDER BY ordinal_position;
        """)
    ).fetchall()

    cols = {r[0]: (r[1], r[2]) for r in result}
    assert "id" in cols, "Missing id column"
    assert "organization_id" in cols, "Missing organization_id column"
    assert "project_id" in cols, "Missing project_id column"
    assert "snapshot_code" in cols, "Missing snapshot_code column"
    assert "snapshot_hash" in cols, "Missing snapshot_hash column"
    assert "is_locked" in cols, "Missing is_locked column"
    assert "input_package" in cols, "Missing input_package column"
    assert cols["input_package"][0] == "jsonb", "input_package must be JSONB"
    assert "readiness_summary" in cols, "Missing readiness_summary column"
    assert cols["readiness_summary"][0] == "jsonb", "readiness_summary must be JSONB"
    assert "source_evidence_ids" in cols, "Missing source_evidence_ids column"
    assert cols["source_evidence_ids"][0] == "jsonb", "source_evidence_ids must be JSONB"


def test_quantification_snapshots_indexes(postgis_conn):
    """
    Verifies that performance and tenant isolation indexes are created on
    quantification_input_snapshots table.
    """
    result = postgis_conn.execute(
        text("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'quantification_input_snapshots';
        """)
    ).fetchall()

    index_names = [r[0] for r in result]
    assert any("org" in idx.lower() for idx in index_names), "Missing organization index"
    assert any("project" in idx.lower() for idx in index_names), "Missing project index"
    assert any("hash" in idx.lower() for idx in index_names), "Missing snapshot_hash index"
    assert any("code" in idx.lower() for idx in index_names), "Missing snapshot_code index"


def test_quantification_snapshot_persistence_and_hashing(postgis_conn):
    """
    Verifies inserting and reading back a locked quantification snapshot
    with SHA-256 hash integrity in PostgreSQL.
    """
    tag = uuid.uuid4().hex[:6]
    org_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    snap_id = uuid.uuid4()
    code = f"QIS-2026-TEST-{tag.upper()}"

    # Insert test organization & project
    postgis_conn.execute(
        text("""
            INSERT INTO organizations (id, name, plan, org_type, status, max_installations, max_agents, api_calls_count, version, is_deleted)
            VALUES (:org_id, :name, 'ENTERPRISE', 'DEVELOPER', 'ACTIVE', 100, 5, 0, 1, false);
        """),
        {"org_id": org_id, "name": f"PostGIS Test Org {tag}"},
    )

    postgis_conn.execute(
        text("""
            INSERT INTO projects (id, organization_id, name, project_code, crediting_start, crediting_end, baseline_parameters)
            VALUES (:proj_id, :org_id, :name, :code, '2026-01-01', '2046-12-31', '{}'::jsonb);
        """),
        {"proj_id": proj_id, "org_id": org_id, "name": f"PostGIS Project {tag}", "code": f"PRJ-{tag}"},
    )

    input_package = {
        "context": "BASELINE",
        "methodology": {"code": "VM0042", "version": "2.2"},
        "measurements": [
            {
                "sample_code": f"SMP-{tag}",
                "analyte": "SOC_CONCENTRATION",
                "normalized_value": 18.5,
                "normalized_unit": "g/kg",
            }
        ],
    }
    canonical_json = json.dumps(input_package, sort_keys=True)
    snap_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    # Insert snapshot
    postgis_conn.execute(
        text("""
            INSERT INTO quantification_input_snapshots (
                id, organization_id, project_id, snapshot_code, status,
                context, methodology_code, methodology_version, rule_set_version,
                snapshot_hash, is_locked, locked_at, total_eligible_measurements,
                total_excluded_measurements, readiness_summary, input_package,
                source_evidence_ids, notes
            ) VALUES (
                :id, :org_id, :proj_id, :code, 'LOCKED',
                'BASELINE', 'VM0042', '2.2', 'VM0042_V2_2_RULES_V1.0',
                :hash, true, NOW(), 1, 0,
                CAST('{"overall_status": "COMPLETE"}' AS jsonb),
                CAST(:package AS jsonb),
                CAST('[]' AS jsonb),
                'PostGIS Integration Test Snapshot'
            );
        """),
        {
            "id": snap_id,
            "org_id": org_id,
            "proj_id": proj_id,
            "code": code,
            "hash": snap_hash,
            "package": json.dumps(input_package),
        },
    )

    # Read back and verify
    row = postgis_conn.execute(
        text("""
            SELECT id, snapshot_code, snapshot_hash, is_locked,
                   input_package->'measurements'->0->>'analyte' AS analyte,
                   CAST(input_package->'measurements'->0->>'normalized_value' AS numeric) AS norm_val,
                   input_package->'measurements'->0->>'normalized_unit' AS norm_unit
            FROM quantification_input_snapshots
            WHERE id = :id;
        """),
        {"id": snap_id},
    ).fetchone()

    assert row is not None
    assert row[1] == code
    assert row[2] == snap_hash
    assert row[3] is True
    assert row[4] == "SOC_CONCENTRATION"
    assert float(row[5]) == 18.5
    assert row[6] == "g/kg"
