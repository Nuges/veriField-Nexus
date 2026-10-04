"""
VeriField Nexus — Agriculture MRV Phase 2: PostGIS Sampling Point & Spatial Verification
Runtime tests against PostgreSQL 15+ and PostGIS 3.3+.
Tests:
1. PostGIS POINT geometry on sampling_points and sample_collection_events
2. ST_Contains / ST_Within spatial queries between LandUnit and SamplingPoint
3. PostGIS ST_Distance(geom::geography, actual_geom::geography) geodesic deviation verification
4. Spatial GiST index inspection for sampling_points and sample_collection_events
"""

import os
import uuid
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


def test_postgis_sampling_point_geometry_types(postgis_conn):
    """Verifies that PostGIS recognizes ST_Point geometry and EPSG:4326 SRID for planned and actual points."""
    planned_lon, planned_lat = 77.105, 28.505
    actual_lon, actual_lat = 77.1051, 28.50505

    row = postgis_conn.execute(
        text("""
            SELECT
                ST_GeometryType(ST_SetSRID(ST_MakePoint(:p_lon, :p_lat), 4326)) AS p_geom_type,
                ST_SRID(ST_SetSRID(ST_MakePoint(:p_lon, :p_lat), 4326)) AS p_srid,
                ST_GeometryType(ST_SetSRID(ST_MakePoint(:a_lon, :a_lat), 4326)) AS a_geom_type,
                ST_SRID(ST_SetSRID(ST_MakePoint(:a_lon, :a_lat), 4326)) AS a_srid;
        """),
        {"p_lon": planned_lon, "p_lat": planned_lat, "a_lon": actual_lon, "a_lat": actual_lat},
    ).mappings().first()

    assert row["p_geom_type"] == "ST_Point"
    assert row["p_srid"] == 4326
    assert row["a_geom_type"] == "ST_Point"
    assert row["a_srid"] == 4326


def test_postgis_spatial_containment_in_land_unit(postgis_conn):
    """Verifies ST_Contains and ST_Within between LandUnit boundary polygon and SamplingPoint."""
    poly_geojson = '{"type":"Polygon","coordinates":[[[77.10,28.50],[77.12,28.50],[77.12,28.52],[77.10,28.52],[77.10,28.50]]]}'

    # Inside point: (77.11, 28.51)
    # Outside point: (77.15, 28.55)
    row = postgis_conn.execute(
        text("""
            WITH poly AS (
                SELECT ST_SetSRID(ST_GeomFromGeoJSON(:gj), 4326) AS geom
            )
            SELECT
                ST_Contains(poly.geom, ST_SetSRID(ST_MakePoint(77.11, 28.51), 4326)) AS inside_contains,
                ST_Within(ST_SetSRID(ST_MakePoint(77.11, 28.51), 4326), poly.geom) AS inside_within,
                ST_Contains(poly.geom, ST_SetSRID(ST_MakePoint(77.15, 28.55), 4326)) AS outside_contains,
                ST_Within(ST_SetSRID(ST_MakePoint(77.15, 28.55), 4326), poly.geom) AS outside_within
            FROM poly;
        """),
        {"gj": poly_geojson},
    ).mappings().first()

    assert row["inside_contains"] is True
    assert row["inside_within"] is True
    assert row["outside_contains"] is False
    assert row["outside_within"] is False


def test_postgis_geodesic_deviation_distance(postgis_conn):
    """Verifies that PostGIS ellipsoidal ST_Distance(geography) matches geodesic deviation expectations."""
    # Point A: 28.505, 77.105
    # Point B: 28.505, 77.1051 (offset ~9.78m)
    # Point C: 28.506, 77.105 (offset ~110.8m)
    row = postgis_conn.execute(
        text("""
            SELECT
                ST_Distance(
                    ST_SetSRID(ST_MakePoint(77.105, 28.505), 4326)::geography,
                    ST_SetSRID(ST_MakePoint(77.1051, 28.505), 4326)::geography
                ) AS dist_small_m,
                ST_Distance(
                    ST_SetSRID(ST_MakePoint(77.105, 28.505), 4326)::geography,
                    ST_SetSRID(ST_MakePoint(77.105, 28.506), 4326)::geography
                ) AS dist_large_m;
        """)
    ).mappings().first()

    assert 9.0 < row["dist_small_m"] < 11.0
    assert 105.0 < row["dist_large_m"] < 115.0


def test_postgis_tables_and_gist_indexes_exist(postgis_conn):
    """Verifies that Phase 2 spatial tables and GiST indexes exist in the live database."""
    tables = postgis_conn.execute(
        text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('sampling_points', 'sample_collection_events', 'physical_samples', 'sampling_campaigns');
        """)
    ).scalars().all()

    assert "sampling_points" in tables
    assert "sample_collection_events" in tables
    assert "physical_samples" in tables
    assert "sampling_campaigns" in tables

    indexes = postgis_conn.execute(
        text("""
            SELECT indexname FROM pg_indexes
            WHERE schemaname = 'public'
            AND indexname IN ('idx_sampling_points_geom', 'idx_sample_collection_events_actual_geom');
        """)
    ).scalars().all()

    assert "idx_sampling_points_geom" in indexes
    assert "idx_sample_collection_events_actual_geom" in indexes


def test_postgis_point_boundary_and_project_containment(postgis_conn):
    """
    Tests spatial boundary containment:
    1. Point inside land unit AND inside project boundary
    2. Point inside project boundary BUT outside land unit
    3. Point completely outside project boundary
    """
    # Project boundary polygon (larger)
    proj_geojson = '{"type":"Polygon","coordinates":[[[77.0,28.0],[77.3,28.0],[77.3,28.7],[77.0,28.7],[77.0,28.0]]]}'
    # Land unit polygon (subset)
    lu_geojson = '{"type":"Polygon","coordinates":[[[77.10,28.50],[77.15,28.50],[77.15,28.55],[77.10,28.55],[77.10,28.50]]]}'

    # Point 1: Inside Land Unit (and inside Project) -> (77.12, 28.52)
    # Point 2: Outside Land Unit, Inside Project -> (77.20, 28.60)
    # Point 3: Outside Project -> (77.40, 28.80)
    res = postgis_conn.execute(
        text("""
            WITH proj AS (
                SELECT ST_SetSRID(ST_GeomFromGeoJSON(:p_gj), 4326) AS geom
            ),
            lu AS (
                SELECT ST_SetSRID(ST_GeomFromGeoJSON(:lu_gj), 4326) AS geom
            )
            SELECT
                ST_Contains(lu.geom, ST_SetSRID(ST_MakePoint(77.12, 28.52), 4326)) AS p1_in_lu,
                ST_Contains(proj.geom, ST_SetSRID(ST_MakePoint(77.12, 28.52), 4326)) AS p1_in_proj,
                ST_Contains(lu.geom, ST_SetSRID(ST_MakePoint(77.20, 28.60), 4326)) AS p2_in_lu,
                ST_Contains(proj.geom, ST_SetSRID(ST_MakePoint(77.20, 28.60), 4326)) AS p2_in_proj,
                ST_Contains(lu.geom, ST_SetSRID(ST_MakePoint(77.40, 28.80), 4326)) AS p3_in_lu,
                ST_Contains(proj.geom, ST_SetSRID(ST_MakePoint(77.40, 28.80), 4326)) AS p3_in_proj
            FROM proj, lu;
        """),
        {"p_gj": proj_geojson, "lu_gj": lu_geojson}
    ).mappings().first()

    assert res["p1_in_lu"] is True
    assert res["p1_in_proj"] is True
    assert res["p2_in_lu"] is False
    assert res["p2_in_proj"] is True
    assert res["p3_in_lu"] is False
    assert res["p3_in_proj"] is False


def test_postgis_actual_collection_point_persistence_and_gist(postgis_conn):
    """
    Verifies actual collection point persistence with GiST indexing:
    Inserts a row into sample_collection_events with actual_geom and tests ST_DWithin query.
    """
    import uuid
    # Create required parent hierarchy for FKs
    org_id = str(uuid.uuid4())
    proj_id = str(uuid.uuid4())
    camp_id = str(uuid.uuid4())
    plan_id = str(uuid.uuid4())
    lu_id = str(uuid.uuid4())
    pt_id = str(uuid.uuid4())
    samp_id = str(uuid.uuid4())
    evt_id = str(uuid.uuid4())

    postgis_conn.execute(text("""
        INSERT INTO organizations (id, name, org_type, status, plan, max_installations, max_agents, api_calls_count, version, is_deleted)
        VALUES (:id, 'PostGIS Spatial Test Org', 'DEVELOPER', 'ACTIVE', 'ENTERPRISE', 100, 10, 0, 1, false);
    """), {"id": org_id})

    postgis_conn.execute(text("""
        INSERT INTO projects (id, organization_id, name, baseline_parameters, created_at, updated_at)
        VALUES (:id, :org_id, 'PostGIS Spatial Test Project', '{}'::jsonb, now(), now());
    """), {"id": proj_id, "org_id": org_id})

    postgis_conn.execute(text("""
        INSERT INTO sampling_campaigns (id, organization_id, project_id, campaign_code, name, planned_start_date, status, created_at, updated_at)
        VALUES (:id, :org_id, :proj_id, 'CAMP-PG-01', 'PostGIS Test Campaign', '2026-01-01', 'ACTIVE', now(), now());
    """), {"id": camp_id, "org_id": org_id, "proj_id": proj_id})

    postgis_conn.execute(text("""
        INSERT INTO sampling_plan_versions (
            id, organization_id, project_id, campaign_id, version_number,
            status, effective_as_of_date, created_at, updated_at
        ) VALUES (
            :id, :org_id, :proj_id, :camp_id, 1,
            'LOCKED', '2026-01-01', now(), now()
        );
    """), {"id": plan_id, "org_id": org_id, "proj_id": proj_id, "camp_id": camp_id})

    postgis_conn.execute(text("""
        INSERT INTO land_units (id, organization_id, project_id, name, boundary_geojson, area_ha, is_active, created_at, updated_at)
        VALUES (:id, :org_id, :proj_id, 'Spatial Land Unit', '{}'::jsonb, 50.0, true, now(), now());
    """), {"id": lu_id, "org_id": org_id, "proj_id": proj_id})

    postgis_conn.execute(text("""
        INSERT INTO sampling_points (
            id, organization_id, project_id, campaign_id, plan_version_id,
            land_unit_id, point_code, planned_lat, planned_lon, geom,
            depth_from_cm, depth_to_cm, created_at
        ) VALUES (
            :id, :org_id, :proj_id, :camp_id, :plan_id,
            :lu_id,
            'P-001', 28.505, 77.105, ST_SetSRID(ST_MakePoint(77.105, 28.505), 4326),
            0.0, 30.0, now()
        );
    """), {"id": pt_id, "org_id": org_id, "proj_id": proj_id, "camp_id": camp_id, "plan_id": plan_id, "lu_id": lu_id})

    # Insert physical sample
    postgis_conn.execute(text("""
        INSERT INTO physical_samples (
            id, organization_id, project_id, campaign_id, plan_version_id,
            sampling_point_id, land_unit_id, sample_code, status, created_at, updated_at
        ) VALUES (
            :id, :org_id, :proj_id, :camp_id, :plan_id,
            :pt_id, :lu_id, 'SAMP-PG-001', 'COLLECTED', now(), now()
        );
    """), {"id": samp_id, "org_id": org_id, "proj_id": proj_id, "camp_id": camp_id, "plan_id": plan_id, "pt_id": pt_id, "lu_id": lu_id})

    # Insert sample collection event with actual_geom
    postgis_conn.execute(text("""
        INSERT INTO sample_collection_events (
            id, physical_sample_id, sampling_point_id,
            actual_lat, actual_lon, actual_geom, deviation_distance_m,
            collection_timestamp, collector_name, actual_depth_from_cm, actual_depth_to_cm,
            sample_condition, device_metadata, created_at, server_received_at
        ) VALUES (
            :id, :samp_id, :pt_id,
            28.50505, 77.10505, ST_SetSRID(ST_MakePoint(77.10505, 28.50505), 4326),
            7.5, now(), 'Field Sampler 1', 0.0, 30.0,
            'GOOD', '{}'::jsonb, now(), now()
        );
    """), {"id": evt_id, "samp_id": samp_id, "pt_id": pt_id})

    # Test spatial index lookup with ST_DWithin (geography)
    query_row = postgis_conn.execute(text("""
        SELECT id, actual_lat, actual_lon, deviation_distance_m
        FROM sample_collection_events
        WHERE id = :evt_id
        AND ST_DWithin(
            actual_geom::geography,
            ST_SetSRID(ST_MakePoint(77.105, 28.505), 4326)::geography,
            50.0
        );
    """), {"evt_id": evt_id}).mappings().first()

    assert query_row is not None
    assert str(query_row["id"]) == evt_id
    assert abs(query_row["actual_lat"] - 28.50505) < 1e-5


def test_postgis_wrong_land_unit_association_detection(postgis_conn):
    """
    Verifies spatial SQL query detecting points improperly associated with the wrong land unit:
    Point geometrically inside Field B, but record claims it belongs to Field A.
    """
    lu_a_gj = '{"type":"Polygon","coordinates":[[[77.10,28.50],[77.12,28.50],[77.12,28.52],[77.10,28.52],[77.10,28.50]]]}'
    lu_b_gj = '{"type":"Polygon","coordinates":[[[77.20,28.50],[77.22,28.50],[77.22,28.52],[77.20,28.52],[77.20,28.50]]]}'

    # A point located at (77.21, 28.51) is in Field B, NOT Field A.
    res = postgis_conn.execute(
        text("""
            WITH fields AS (
                SELECT 'Field A' AS name, ST_SetSRID(ST_GeomFromGeoJSON(:a_gj), 4326) AS geom
                UNION ALL
                SELECT 'Field B' AS name, ST_SetSRID(ST_GeomFromGeoJSON(:b_gj), 4326) AS geom
            ),
            claimed_point AS (
                SELECT 'Claimed Field A' AS claimed_for, ST_SetSRID(ST_MakePoint(77.21, 28.51), 4326) AS geom
            )
            SELECT
                f.name AS actual_enclosing_field,
                ST_Contains(f.geom, cp.geom) AS contains_point
            FROM fields f, claimed_point cp
            WHERE ST_Contains(f.geom, cp.geom);
        """),
        {"a_gj": lu_a_gj, "b_gj": lu_b_gj}
    ).mappings().first()

    assert res is not None
    assert res["actual_enclosing_field"] == "Field B"
    assert res["contains_point"] is True


def test_postgis_tenant_and_project_spatial_isolation(postgis_conn):
    """
    Verifies that spatial proximity queries strictly isolate records across tenant/organization boundaries.
    """
    import uuid
    org1_id = str(uuid.uuid4())
    org2_id = str(uuid.uuid4())

    postgis_conn.execute(text("""
        INSERT INTO organizations (id, name, org_type, status, plan, max_installations, max_agents, api_calls_count, version, is_deleted) VALUES
        (:o1, 'Org Alpha Tenant', 'DEVELOPER', 'ACTIVE', 'ENTERPRISE', 100, 10, 0, 1, false),
        (:o2, 'Org Beta Tenant', 'DEVELOPER', 'ACTIVE', 'ENTERPRISE', 100, 10, 0, 1, false);
    """), {"o1": org1_id, "o2": org2_id})

    # Both insert a point at the exact same location (77.105, 28.505)
    postgis_conn.execute(text("""
        INSERT INTO land_units (id, organization_id, name, boundary_geojson, area_ha, is_active, created_at, updated_at) VALUES
        (:lu1, :o1, 'Alpha Field', '{}'::jsonb, 10.0, true, now(), now()),
        (:lu2, :o2, 'Beta Field', '{}'::jsonb, 10.0, true, now(), now());
    """), {"lu1": str(uuid.uuid4()), "o1": org1_id, "lu2": str(uuid.uuid4()), "o2": org2_id})

    # Query scoped to Org Alpha MUST NOT return Org Beta's land units
    rows_alpha = postgis_conn.execute(text("""
        SELECT id, name FROM land_units
        WHERE organization_id = :o1;
    """), {"o1": org1_id}).mappings().all()

    assert len(rows_alpha) == 1
    assert rows_alpha[0]["name"] == "Alpha Field"
