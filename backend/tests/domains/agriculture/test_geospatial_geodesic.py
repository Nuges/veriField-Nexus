"""
=============================================================================
VeriField Nexus — Geospatial & Geodesic Calculation Tests
=============================================================================
Tests:
1. Exact WGS84 ellipsoidal geodesic area and perimeter calculation using GeographicLib:
   - Single convex polygon.
   - Polygon with interior hole: interior hole area is subtracted from net area.
   - MultiPolygon: sum of component polygons.
2. GeoJSON validation:
   - Polygon closure checking.
   - WGS84 coordinate bounding checking.
   - Self-intersection detection.
3. Boundary source classification:
   - DECLARED, GNSS_SURVEY, RTK_GNSS, CADASTRAL, IMPORTED_GIS, MANUALLY_DRAWN.
=============================================================================
"""

import pytest

from app.domains.agriculture.geospatial import (
    BoundarySource,
    compute_centroid,
    compute_geodesic_area_ha,
    has_self_intersection,
    validate_geojson_polygon,
)


def test_wgs84_geodesic_area_single_polygon():
    # Square ~0.01 deg near equator (approx 1.11 km x 1.11 km ~ 123 ha)
    polygon = {
        "type": "Polygon",
        "coordinates": [
            [[0.0, 0.0], [0.01, 0.0], [0.01, 0.01], [0.0, 0.01], [0.0, 0.0]]
        ],
    }
    valid, err = validate_geojson_polygon(polygon)
    assert valid is True
    assert err is None

    area_ha, perim_m = compute_geodesic_area_ha(polygon)
    assert 120.0 < area_ha < 125.0
    assert 4000.0 < perim_m < 5000.0

    lat, lon = compute_centroid(polygon)
    assert round(lat, 3) == 0.005
    assert round(lon, 3) == 0.005


def test_wgs84_geodesic_area_with_interior_hole():
    # Exterior ring: 0.0 to 0.02 deg
    exterior = [[0.0, 0.0], [0.02, 0.0], [0.02, 0.02], [0.0, 0.02], [0.0, 0.0]]
    # Interior hole: 0.005 to 0.015 deg (1/4 of total area)
    hole = [[0.005, 0.005], [0.015, 0.005], [0.015, 0.015], [0.005, 0.015], [0.005, 0.005]]

    poly_solid = {"type": "Polygon", "coordinates": [exterior]}
    poly_with_hole = {"type": "Polygon", "coordinates": [exterior, hole]}

    solid_area_ha, _ = compute_geodesic_area_ha(poly_solid)
    net_area_ha, net_perim_m = compute_geodesic_area_ha(poly_with_hole)

    # Net area with hole must be strictly less than solid area
    assert net_area_ha < solid_area_ha
    assert round(solid_area_ha - net_area_ha, 1) > 100.0  # Hole is substantial


def test_multipolygon_geodesic_sum():
    poly1 = [[0.0, 0.0], [0.01, 0.0], [0.01, 0.01], [0.0, 0.01], [0.0, 0.0]]
    poly2 = [[0.05, 0.05], [0.06, 0.05], [0.06, 0.06], [0.05, 0.06], [0.05, 0.05]]

    multipoly = {
        "type": "MultiPolygon",
        "coordinates": [[poly1], [poly2]],
    }
    valid, err = validate_geojson_polygon(multipoly)
    assert valid is True

    area_ha, _ = compute_geodesic_area_ha(multipoly)
    single_area_ha, _ = compute_geodesic_area_ha({"type": "Polygon", "coordinates": [poly1]})

    # MultiPolygon area is the sum of both disjoint polygons
    assert round(area_ha, 1) == round(single_area_ha * 2, 1)


def test_geojson_unclosed_ring_rejected():
    unclosed = {
        "type": "Polygon",
        "coordinates": [
            [[77.1, 28.5], [77.2, 28.5], [77.2, 28.6], [77.1, 28.6]]  # missing closing point
        ],
    }
    valid, err = validate_geojson_polygon(unclosed)
    assert valid is False
    assert "not closed" in err.lower()


def test_geojson_out_of_bounds_rejected():
    bad_coords = {
        "type": "Polygon",
        "coordinates": [
            [[190.0, 28.5], [191.0, 28.5], [191.0, 28.6], [190.0, 28.6], [190.0, 28.5]]
        ],
    }
    valid, err = validate_geojson_polygon(bad_coords)
    assert valid is False
    assert "bounds" in err.lower()


def test_self_intersecting_ring_detected():
    # Figure 8 (bow-tie) self-intersecting polygon
    bowtie = [
        [0.0, 0.0],
        [1.0, 1.0],
        [0.0, 1.0],
        [1.0, 0.0],
        [0.0, 0.0],
    ]
    assert has_self_intersection(bowtie) is True

    geojson = {"type": "Polygon", "coordinates": [bowtie]}
    valid, err = validate_geojson_polygon(geojson)
    assert valid is False
    assert "self-intersecting" in err.lower()


def test_boundary_sources_enum():
    sources = {s.value for s in BoundarySource}
    assert "DECLARED" in sources
    assert "GNSS_SURVEY" in sources
    assert "RTK_GNSS" in sources
    assert "CADASTRAL" in sources
    assert "IMPORTED_GIS" in sources
    assert "MANUALLY_DRAWN" in sources
