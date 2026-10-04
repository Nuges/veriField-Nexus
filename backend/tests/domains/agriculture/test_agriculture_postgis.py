"""
VeriField Nexus — Agriculture MRV Phase 1: PostGIS Land Unit Spatial Tests
Authoritative runtime verification against PostgreSQL 15+ and PostGIS 3.3+.
Tests spatial geometry types, geodesic area, topological relationships,
bounding box operators, and multi-tenant/project scoping.
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


@pytest.fixture(scope="module")
def postgis_conn():
    engine = get_postgis_engine()
    if engine is None:
        pytest.skip("Real PostGIS database is not available in the current test environment.")
    with engine.connect() as conn:
        trans = conn.begin()
        yield conn
        trans.rollback()


def test_postgis_01_valid_polygon(postgis_conn):
    """Verifies valid WGS84 single polygon creation and geometry validation."""
    geojson = '{"type":"Polygon","coordinates":[[[-120.5,38.5],[-120.4,38.5],[-120.4,38.6],[-120.5,38.6],[-120.5,38.5]]]}'
    res = postgis_conn.execute(
        text("""
            SELECT
                ST_IsValid(ST_SetSRID(ST_GeomFromGeoJSON(:gj), 4326)) AS is_valid,
                ST_GeometryType(ST_SetSRID(ST_GeomFromGeoJSON(:gj), 4326)) AS geom_type,
                ST_SRID(ST_SetSRID(ST_GeomFromGeoJSON(:gj), 4326)) AS srid;
        """),
        {"gj": geojson},
    ).fetchone()
    assert res.is_valid is True
    assert res.geom_type == "ST_Polygon"
    assert res.srid == 4326


def test_postgis_02_valid_multipolygon(postgis_conn):
    """Verifies valid MultiPolygon geometry in PostGIS."""
    geojson = '{"type":"MultiPolygon","coordinates":[[[[-120.5,38.5],[-120.4,38.5],[-120.4,38.6],[-120.5,38.6],[-120.5,38.5]]],[[[-120.3,38.5],[-120.2,38.5],[-120.2,38.6],[-120.3,38.6],[-120.3,38.5]]]]}'
    res = postgis_conn.execute(
        text("""
            SELECT
                ST_IsValid(ST_SetSRID(ST_GeomFromGeoJSON(:gj), 4326)) AS is_valid,
                ST_GeometryType(ST_SetSRID(ST_GeomFromGeoJSON(:gj), 4326)) AS geom_type,
                ST_NumGeometries(ST_SetSRID(ST_GeomFromGeoJSON(:gj), 4326)) AS num_geoms;
        """),
        {"gj": geojson},
    ).fetchone()
    assert res.is_valid is True
    assert res.geom_type == "ST_MultiPolygon"
    assert res.num_geoms == 2


def test_postgis_03_invalid_self_intersection(postgis_conn):
    """Verifies self-intersecting bowtie polygon is detected as invalid by PostGIS."""
    bowtie = '{"type":"Polygon","coordinates":[[[0,0],[1,1],[0,1],[1,0],[0,0]]]}'
    res = postgis_conn.execute(
        text("""
            SELECT
                ST_IsValid(ST_SetSRID(ST_GeomFromGeoJSON(:gj), 4326)) AS is_valid,
                ST_IsValidReason(ST_SetSRID(ST_GeomFromGeoJSON(:gj), 4326)) AS reason;
        """),
        {"gj": bowtie},
    ).fetchone()
    assert res.is_valid is False
    assert "Self-intersection" in res.reason


def test_postgis_04_polygon_with_interior_hole(postgis_conn):
    """Verifies polygon with an interior donut hole correctly deducts area."""
    outer_gj = '{"type":"Polygon","coordinates":[[[-120.5,38.5],[-120.3,38.5],[-120.3,38.7],[-120.5,38.7],[-120.5,38.5]]]}'
    holed_gj = '{"type":"Polygon","coordinates":[[[-120.5,38.5],[-120.3,38.5],[-120.3,38.7],[-120.5,38.7],[-120.5,38.5]],[[-120.45,38.55],[-120.35,38.55],[-120.35,38.65],[-120.45,38.65],[-120.45,38.55]]]}'
    res = postgis_conn.execute(
        text("""
            SELECT
                ST_NRings(ST_SetSRID(ST_GeomFromGeoJSON(:holed), 4326)) AS num_rings,
                ST_Area(ST_SetSRID(ST_GeomFromGeoJSON(:outer), 4326)::geography) AS outer_area_m2,
                ST_Area(ST_SetSRID(ST_GeomFromGeoJSON(:holed), 4326)::geography) AS holed_area_m2;
        """),
        {"outer": outer_gj, "holed": holed_gj},
    ).fetchone()
    assert res.num_rings == 2
    assert res.holed_area_m2 < res.outer_area_m2
    assert res.holed_area_m2 > 0


def test_postgis_05_containment_within_project_boundary(postgis_conn):
    """Verifies PostGIS ST_Contains for land unit strictly inside project boundary."""
    project_poly = '{"type":"Polygon","coordinates":[[[-120.6,38.4],[-120.2,38.4],[-120.2,38.8],[-120.6,38.8],[-120.6,38.4]]]}'
    land_unit_poly = '{"type":"Polygon","coordinates":[[[-120.5,38.5],[-120.4,38.5],[-120.4,38.6],[-120.5,38.6],[-120.5,38.5]]]}'
    res = postgis_conn.execute(
        text("""
            SELECT
                ST_Contains(
                    ST_SetSRID(ST_GeomFromGeoJSON(:proj), 4326),
                    ST_SetSRID(ST_GeomFromGeoJSON(:unit), 4326)
                ) AS is_contained,
                ST_Within(
                    ST_SetSRID(ST_GeomFromGeoJSON(:unit), 4326),
                    ST_SetSRID(ST_GeomFromGeoJSON(:proj), 4326)
                ) AS is_within;
        """),
        {"proj": project_poly, "unit": land_unit_poly},
    ).fetchone()
    assert res.is_contained is True
    assert res.is_within is True


def test_postgis_06_partial_outside_boundary_case(postgis_conn):
    """Verifies land unit straddling project boundary is not contained, but intersects."""
    project_poly = '{"type":"Polygon","coordinates":[[[-120.6,38.4],[-120.2,38.4],[-120.2,38.8],[-120.6,38.8],[-120.6,38.4]]]}'
    # Straddles eastern border of project (-120.2)
    straddling_poly = '{"type":"Polygon","coordinates":[[[-120.3,38.5],[-120.1,38.5],[-120.1,38.6],[-120.3,38.6],[-120.3,38.5]]]}'
    res = postgis_conn.execute(
        text("""
            SELECT
                ST_Contains(
                    ST_SetSRID(ST_GeomFromGeoJSON(:proj), 4326),
                    ST_SetSRID(ST_GeomFromGeoJSON(:straddle), 4326)
                ) AS is_contained,
                ST_Intersects(
                    ST_SetSRID(ST_GeomFromGeoJSON(:proj), 4326),
                    ST_SetSRID(ST_GeomFromGeoJSON(:straddle), 4326)
                ) AS does_intersect,
                ST_Area(
                    ST_Difference(
                        ST_SetSRID(ST_GeomFromGeoJSON(:straddle), 4326),
                        ST_SetSRID(ST_GeomFromGeoJSON(:proj), 4326)
                    )::geography
                ) AS outside_area_m2;
        """),
        {"proj": project_poly, "straddle": straddling_poly},
    ).fetchone()
    assert res.is_contained is False
    assert res.does_intersect is True
    assert res.outside_area_m2 > 0


def test_postgis_07_geodesic_area(postgis_conn):
    """Verifies ellipsoidal WGS84 geodesic area in hectares using PostGIS geography."""
    # 0.1 degree x 0.1 degree box around lat 38.5: ~9500-9600 hectares
    poly = '{"type":"Polygon","coordinates":[[[-120.5,38.5],[-120.4,38.5],[-120.4,38.6],[-120.5,38.6],[-120.5,38.5]]]}'
    res = postgis_conn.execute(
        text("""
            SELECT
                ST_Area(ST_SetSRID(ST_GeomFromGeoJSON(:gj), 4326)::geography) / 10000.0 AS area_ha;
        """),
        {"gj": poly},
    ).scalar()
    assert 9000.0 < res < 10000.0


def test_postgis_08_bbox_query(postgis_conn):
    """Verifies PostGIS bounding box overlap (&&) and envelope intersection."""
    poly = '{"type":"Polygon","coordinates":[[[-120.5,38.5],[-120.4,38.5],[-120.4,38.6],[-120.5,38.6],[-120.5,38.5]]]}'
    res = postgis_conn.execute(
        text("""
            SELECT
                ST_SetSRID(ST_GeomFromGeoJSON(:gj), 4326) && ST_MakeEnvelope(-120.6, 38.4, -120.3, 38.7, 4326) AS bbox_hit,
                ST_SetSRID(ST_GeomFromGeoJSON(:gj), 4326) && ST_MakeEnvelope(-119.0, 37.0, -118.0, 37.5, 4326) AS bbox_miss;
        """),
        {"gj": poly},
    ).fetchone()
    assert res.bbox_hit is True
    assert res.bbox_miss is False


def test_postgis_09_tenant_and_project_scoped_land_unit_query(postgis_conn):
    """Verifies that spatial queries on land_units strictly filter by organization_id and project_id."""
    org_a = str(uuid.uuid4())
    org_b = str(uuid.uuid4())
    proj_a = str(uuid.uuid4())
    proj_b = str(uuid.uuid4())
    unit_a = str(uuid.uuid4())
    unit_b = str(uuid.uuid4())

    # Create dummy orgs and projects in transaction
    postgis_conn.execute(
        text("""
            INSERT INTO organizations (id, name, org_type, status, plan, max_installations, max_agents, api_calls_count, version, is_deleted)
            VALUES
                (:org_a, 'Org A', 'DEVELOPER', 'ACTIVE', 'ENTERPRISE', 100, 10, 0, 1, false),
                (:org_b, 'Org B', 'DEVELOPER', 'ACTIVE', 'ENTERPRISE', 100, 10, 0, 1, false);
        """),
        {"org_a": org_a, "org_b": org_b},
    )

    reg_id = str(uuid.uuid4())
    fam_id = str(uuid.uuid4())
    meth_id = str(uuid.uuid4())
    postgis_conn.execute(
        text("""
            INSERT INTO methodology_registries (id, code, name, is_active) VALUES (:reg_id, 'REG-TEST', 'Registry Test', true);
            INSERT INTO methodology_families (id, code, name) VALUES (:fam_id, 'AGRI-TEST', 'Agri Family Test');
            INSERT INTO methodologies (id, family_id, registry_id, code, name, is_active, ui_config, form_schema, recommendation_rules)
            VALUES (:meth_id, :fam_id, :reg_id, 'METH-TEST', 'Methodology Test', true, '{}'::jsonb, '{}'::jsonb, '{}'::jsonb);
        """),
        {"reg_id": reg_id, "fam_id": fam_id, "meth_id": meth_id},
    )

    postgis_conn.execute(
        text("""
            INSERT INTO projects (id, organization_id, name, methodology_id, project_code, baseline_parameters)
            VALUES
                (:proj_a, :org_a, 'Project A', :meth_id, 'PA-01', '{}'::jsonb),
                (:proj_b, :org_b, 'Project B', :meth_id, 'PB-01', '{}'::jsonb);
        """),
        {"proj_a": proj_a, "proj_b": proj_b, "org_a": org_a, "org_b": org_b, "meth_id": meth_id},
    )

    # Insert two land units at the same physical location but belonging to different tenants and projects
    poly_wkt = "POLYGON((-120.5 38.5, -120.4 38.5, -120.4 38.6, -120.5 38.6, -120.5 38.5))"
    postgis_conn.execute(
        text("""
            INSERT INTO land_units (id, organization_id, project_id, name, unit_type, boundary_geojson, geom, area_ha, is_active)
            VALUES
                (:unit_a, :org_a, :proj_a, 'Unit Org A', 'FIELD', '{"type":"Polygon"}'::jsonb, ST_SetSRID(ST_GeomFromText(:wkt), 4326), 9500.0, true),
                (:unit_b, :org_b, :proj_b, 'Unit Org B', 'FIELD', '{"type":"Polygon"}'::jsonb, ST_SetSRID(ST_GeomFromText(:wkt), 4326), 9500.0, true);
        """),
        {"unit_a": unit_a, "unit_b": unit_b, "org_a": org_a, "org_b": org_b, "proj_a": proj_a, "proj_b": proj_b, "wkt": poly_wkt},
    )

    # Spatial query for Org A must return Unit A only
    aoi_wkt = "POLYGON((-120.6 38.4, -120.3 38.4, -120.3 38.7, -120.6 38.7, -120.6 38.4))"
    res_a = postgis_conn.execute(
        text("""
            SELECT id FROM land_units
            WHERE organization_id = :org_id
              AND ST_Intersects(geom, ST_SetSRID(ST_GeomFromText(:aoi), 4326));
        """),
        {"org_id": org_a, "aoi": aoi_wkt},
    ).scalars().all()
    assert len(res_a) == 1
    assert str(res_a[0]) == unit_a

    # Spatial query for Project B must return Unit B only
    res_b = postgis_conn.execute(
        text("""
            SELECT id FROM land_units
            WHERE project_id = :proj_id
              AND ST_Intersects(geom, ST_SetSRID(ST_GeomFromText(:aoi), 4326));
        """),
        {"proj_id": proj_b, "aoi": aoi_wkt},
    ).scalars().all()
    assert len(res_b) == 1
    assert str(res_b[0]) == unit_b
