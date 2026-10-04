"""
=============================================================================
VeriField Nexus — Authoritative PostGIS Integration Test Suite
=============================================================================
Direct deployment-level PostGIS validation:
1. Polygon geometry validation & closed ring coordinates
2. MultiPolygon geometry with disjoint components
3. Polygon with interior hole (donut) & area deduction
4. Containment tests (ST_Contains, ST_Within)
5. Intersection tests (ST_Intersects, ST_Intersection)
6. Non-intersection / Disjoint tests (ST_Disjoint)
7. Bounding box spatial operator (&&) and ST_MakeEnvelope
8. Ellipsoidal physical area calculation via ST_Area(geom::geography)
9. Tenant-scoped spatial queries (ABAC multi-tenant isolation)
10. Project-scoped spatial queries
=============================================================================
"""

import os
import uuid
import pytest
from sqlalchemy import create_engine, text


def get_postgis_engine():
    """
    Attempts to connect to a PostgreSQL instance with PostGIS enabled.
    Checks POSTGIS_TEST_URL or localhost:5432 (default PostgreSQL with PostGIS).
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
        pytest.skip("PostGIS is not available in the current test environment.")
    with engine.connect() as conn:
        yield conn


def test_postgis_01_polygon_creation_and_closure(postgis_conn):
    """Verifies valid WGS84 polygon creation, closed ring topology, and GeoJSON export."""
    sql = text("""
        SELECT
            ST_IsValid(ST_SetSRID(ST_GeomFromGeoJSON('{"type":"Polygon","coordinates":[[[12.4, 41.8],[12.6, 41.8],[12.6, 42.0],[12.4, 42.0],[12.4, 41.8]]]}'), 4326)) AS is_valid,
            ST_GeometryType(ST_SetSRID(ST_GeomFromGeoJSON('{"type":"Polygon","coordinates":[[[12.4, 41.8],[12.6, 41.8],[12.6, 42.0],[12.4, 42.0],[12.4, 41.8]]]}'), 4326)) AS geom_type;
    """)
    row = postgis_conn.execute(sql).mappings().one()
    assert row["is_valid"] is True
    assert row["geom_type"] == "ST_Polygon"


def test_postgis_02_multipolygon_geometry(postgis_conn):
    """Verifies MultiPolygon geometry handling across disjoint spatial components."""
    sql = text("""
        SELECT
            ST_IsValid(ST_SetSRID(ST_GeomFromGeoJSON('{"type":"MultiPolygon","coordinates":[[[[10,10],[12,10],[12,12],[10,12],[10,10]]],[[[20,20],[22,20],[22,22],[20,22],[20,20]]]]}'), 4326)) AS is_valid,
            ST_NumGeometries(ST_SetSRID(ST_GeomFromGeoJSON('{"type":"MultiPolygon","coordinates":[[[[10,10],[12,10],[12,12],[10,12],[10,10]]],[[[20,20],[22,20],[22,22],[20,22],[20,20]]]]}'), 4326)) AS num_geoms;
    """)
    row = postgis_conn.execute(sql).mappings().one()
    assert row["is_valid"] is True
    assert row["num_geoms"] == 2


def test_postgis_03_polygon_with_interior_hole(postgis_conn):
    """Verifies interior ring hole subtraction and hole non-containment."""
    # Outer ring: [0,0] to [10,10]. Interior hole: [3,3] to [7,7].
    sql = text("""
        WITH donut AS (
            SELECT ST_SetSRID(ST_GeomFromGeoJSON('{
                "type": "Polygon",
                "coordinates": [
                    [[0,0],[10,0],[10,10],[0,10],[0,0]],
                    [[3,3],[7,3],[7,7],[3,7],[3,3]]
                ]
            }'), 4326) AS geom
        )
        SELECT
            ST_NRings(geom) AS num_rings,
            ST_Contains(geom, ST_SetSRID(ST_Point(1, 1), 4326)) AS point_in_solid,
            ST_Contains(geom, ST_SetSRID(ST_Point(5, 5), 4326)) AS point_in_hole,
            ST_Area(geom::geography) < ST_Area(ST_Envelope(geom)::geography) AS hole_subtracted
        FROM donut;
    """)
    row = postgis_conn.execute(sql).mappings().one()
    assert row["num_rings"] == 2
    assert row["point_in_solid"] is True
    assert row["point_in_hole"] is False, "Point inside polygon hole MUST NOT be contained!"
    assert row["hole_subtracted"] is True


def test_postgis_04_containment_and_within(postgis_conn):
    """Verifies ST_Contains and ST_Within spatial relations."""
    sql = text("""
        WITH geoms AS (
            SELECT
                ST_SetSRID(ST_GeomFromGeoJSON('{"type":"Polygon","coordinates":[[[0,0],[10,0],[10,10],[0,10],[0,0]]]}'), 4326) AS parent_poly,
                ST_SetSRID(ST_GeomFromGeoJSON('{"type":"Polygon","coordinates":[[[2,2],[4,2],[4,4],[2,4],[2,2]]]}'), 4326) AS child_poly,
                ST_SetSRID(ST_Point(3, 3), 4326) AS inside_pt,
                ST_SetSRID(ST_Point(12, 12), 4326) AS outside_pt
        )
        SELECT
            ST_Contains(parent_poly, inside_pt) AS pt_contained,
            ST_Contains(parent_poly, outside_pt) AS pt_not_contained,
            ST_Contains(parent_poly, child_poly) AS poly_contained,
            ST_Within(child_poly, parent_poly) AS poly_within
        FROM geoms;
    """)
    row = postgis_conn.execute(sql).mappings().one()
    assert row["pt_contained"] is True
    assert row["pt_not_contained"] is False
    assert row["poly_contained"] is True
    assert row["poly_within"] is True


def test_postgis_05_intersection_and_overlap(postgis_conn):
    """Verifies ST_Intersects and ST_Intersection geometry derivation."""
    sql = text("""
        WITH geoms AS (
            SELECT
                ST_SetSRID(ST_GeomFromGeoJSON('{"type":"Polygon","coordinates":[[[0,0],[5,0],[5,5],[0,5],[0,0]]]}'), 4326) AS poly1,
                ST_SetSRID(ST_GeomFromGeoJSON('{"type":"Polygon","coordinates":[[[3,3],[8,3],[8,8],[3,8],[3,3]]]}'), 4326) AS poly2
        )
        SELECT
            ST_Intersects(poly1, poly2) AS intersects,
            ST_AsGeoJSON(ST_Intersection(poly1, poly2)) AS intersection_geojson,
            ST_Area(ST_Intersection(poly1, poly2)::geography) > 0 AS intersection_has_area
        FROM geoms;
    """)
    row = postgis_conn.execute(sql).mappings().one()
    assert row["intersects"] is True
    assert "Polygon" in row["intersection_geojson"]
    assert row["intersection_has_area"] is True


def test_postgis_06_non_intersection_and_disjoint(postgis_conn):
    """Verifies disjoint non-intersecting geometries return False."""
    sql = text("""
        WITH geoms AS (
            SELECT
                ST_SetSRID(ST_GeomFromGeoJSON('{"type":"Polygon","coordinates":[[[0,0],[2,0],[2,2],[0,2],[0,0]]]}'), 4326) AS poly1,
                ST_SetSRID(ST_GeomFromGeoJSON('{"type":"Polygon","coordinates":[[[10,10],[12,10],[12,12],[10,12],[10,10]]]}'), 4326) AS poly2
        )
        SELECT
            ST_Intersects(poly1, poly2) AS intersects,
            ST_Disjoint(poly1, poly2) AS disjoint,
            ST_IsEmpty(ST_Intersection(poly1, poly2)) AS intersection_is_empty
        FROM geoms;
    """)
    row = postgis_conn.execute(sql).mappings().one()
    assert row["intersects"] is False
    assert row["disjoint"] is True
    assert row["intersection_is_empty"] is True


def test_postgis_07_bounding_box_operators(postgis_conn):
    """Verifies PostGIS fast bounding-box overlap operator (&&) and ST_MakeEnvelope."""
    sql = text("""
        WITH bbox_test AS (
            SELECT
                ST_SetSRID(ST_GeomFromGeoJSON('{"type":"Polygon","coordinates":[[[12.4, 41.8],[12.6, 41.8],[12.6, 42.0],[12.4, 42.0],[12.4, 41.8]]]}'), 4326) AS geom,
                ST_MakeEnvelope(12.3, 41.7, 12.5, 41.9, 4326) AS query_envelope,
                ST_MakeEnvelope(15.0, 45.0, 16.0, 46.0, 4326) AS distant_envelope
        )
        SELECT
            (geom && query_envelope) AS bbox_overlaps,
            (geom && distant_envelope) AS distant_bbox_no_overlap
        FROM bbox_test;
    """)
    row = postgis_conn.execute(sql).mappings().one()
    assert row["bbox_overlaps"] is True
    assert row["distant_bbox_no_overlap"] is False


def test_postgis_08_physical_area_geography(postgis_conn):
    """Verifies ellipsoidal surface area calculation via ST_Area(geom::geography)."""
    # 0.2° x 0.2° box in Rome (lat ~41.9°)
    sql = text("""
        SELECT
            ST_Area(ST_SetSRID(ST_GeomFromGeoJSON('{"type":"Polygon","coordinates":[[[12.4, 41.8],[12.6, 41.8],[12.6, 42.0],[12.4, 42.0],[12.4, 41.8]]]}'), 4326)::geography) AS area_m2;
    """)
    area_m2 = postgis_conn.execute(sql).scalar()
    area_ha = area_m2 / 10000.0
    # Expected area ~36,866 ha for this 0.2x0.2 deg box at 41.9N
    assert 36000 <= area_ha <= 37500, f"Expected ~36,866 ha, got {area_ha}"


def test_postgis_09_tenant_scoped_spatial_query(postgis_conn):
    """
    Verifies multi-tenant spatial filtering:
    Tenant A AOI query must strictly return Tenant A geometries and exclude Tenant B.
    """
    org_a = str(uuid.uuid4())
    org_b = str(uuid.uuid4())

    setup_sql = text(f"""
        CREATE TEMP TABLE temp_spatial_fixtures (
            id UUID PRIMARY KEY,
            organization_id UUID NOT NULL,
            geom GEOMETRY(Geometry, 4326)
        );
        INSERT INTO temp_spatial_fixtures VALUES
            ('{uuid.uuid4()}', '{org_a}', ST_SetSRID(ST_Point(12.5, 41.9), 4326)),
            ('{uuid.uuid4()}', '{org_b}', ST_SetSRID(ST_Point(12.55, 41.95), 4326));
    """)
    postgis_conn.execute(setup_sql)

    query_aoi = '{"type":"Polygon","coordinates":[[[12.4, 41.8],[12.6, 41.8],[12.6, 42.0],[12.4, 42.0],[12.4, 41.8]]]}'
    tenant_a_query = text(f"""
        SELECT count(*)
        FROM temp_spatial_fixtures
        WHERE organization_id = '{org_a}'
          AND ST_Contains(ST_SetSRID(ST_GeomFromGeoJSON('{query_aoi}'), 4326), geom);
    """)
    count_a = postgis_conn.execute(tenant_a_query).scalar()
    assert count_a == 1, "Tenant A must find its 1 point"

    tenant_b_query = text(f"""
        SELECT count(*)
        FROM temp_spatial_fixtures
        WHERE organization_id = '{org_b}'
          AND ST_Contains(ST_SetSRID(ST_GeomFromGeoJSON('{query_aoi}'), 4326), geom);
    """)
    count_b = postgis_conn.execute(tenant_b_query).scalar()
    assert count_b == 1, "Tenant B must find its 1 point"

    cross_tenant_query = text(f"""
        SELECT count(*)
        FROM temp_spatial_fixtures
        WHERE organization_id = '{org_a}'
          AND id = (SELECT id FROM temp_spatial_fixtures WHERE organization_id = '{org_b}' LIMIT 1);
    """)
    cross_count = postgis_conn.execute(cross_tenant_query).scalar()
    assert cross_count == 0, "Cross-tenant query must return 0 records"


def test_postgis_10_project_scoped_spatial_query(postgis_conn):
    """
    Verifies project-scoped spatial filtering:
    Project P1 spatial boundary filters only observations inside Project P1.
    """
    proj_1 = str(uuid.uuid4())
    proj_2 = str(uuid.uuid4())

    setup_sql = text(f"""
        CREATE TEMP TABLE temp_project_spatial (
            id UUID PRIMARY KEY,
            project_id UUID NOT NULL,
            footprint_geom GEOMETRY(Geometry, 4326)
        );
        INSERT INTO temp_project_spatial VALUES
            ('{uuid.uuid4()}', '{proj_1}', ST_SetSRID(ST_GeomFromGeoJSON('{{"type":"Polygon","coordinates":[[[10,10],[11,10],[11,11],[10,11],[10,10]]]}}'), 4326)),
            ('{uuid.uuid4()}', '{proj_2}', ST_SetSRID(ST_GeomFromGeoJSON('{{"type":"Polygon","coordinates":[[[20,20],[21,20],[21,21],[20,21],[20,20]]]}}'), 4326));
    """)
    postgis_conn.execute(setup_sql)

    point_in_p1 = '{"type":"Point","coordinates":[10.5, 10.5]}'
    p1_query = text(f"""
        SELECT count(*)
        FROM temp_project_spatial
        WHERE project_id = '{proj_1}'
          AND ST_Contains(footprint_geom, ST_SetSRID(ST_GeomFromGeoJSON('{point_in_p1}'), 4326));
    """)
    assert postgis_conn.execute(p1_query).scalar() == 1

    p2_query = text(f"""
        SELECT count(*)
        FROM temp_project_spatial
        WHERE project_id = '{proj_2}'
          AND ST_Contains(footprint_geom, ST_SetSRID(ST_GeomFromGeoJSON('{point_in_p1}'), 4326));
    """)
    assert postgis_conn.execute(p2_query).scalar() == 0, "Point in P1 must not match P2"
