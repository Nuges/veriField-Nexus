"""
=============================================================================
VeriField Nexus — Agriculture Geospatial & Boundary Quality Engine
=============================================================================
Implements:
- WGS84 Ellipsoidal Geodesic Area and Perimeter Calculations (GeographicLib)
  (Identical to PostGIS ST_Area(geom::geography))
- MultiPolygon and Interior Hole Area Deductions
- Boundary Source Quality Classification (Segregated from Remote Sensing)
- GeoJSON Topology, Closure, Bounding, and Coordinate Validation
- Centroid Calculation
=============================================================================
"""

import math
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from geographiclib.geodesic import Geodesic


class BoundarySource(str, Enum):
    """
    Source classification for land unit boundaries.
    Strictly segregated from remote-sensing land-cover observations.
    """
    DECLARED = "DECLARED"
    GNSS_SURVEY = "GNSS_SURVEY"
    RTK_GNSS = "RTK_GNSS"
    CADASTRAL = "CADASTRAL"
    IMPORTED_GIS = "IMPORTED_GIS"
    MANUALLY_DRAWN = "MANUALLY_DRAWN"


class LandUnitType(str, Enum):
    """
    Methodology-aligned land unit hierarchy.
    """
    PARCEL = "PARCEL"
    FIELD = "FIELD"
    STRATUM = "STRATUM"
    MONITORING_PLOT = "MONITORING_PLOT"


def _compute_ring_geodesic(coords: List[List[float]]) -> Tuple[float, float]:
    """
    Computes (area_m2, perimeter_m) for a single closed LinearRing using GeographicLib WGS84.
    coords is a list of [longitude, latitude] or (lon, lat).
    GeographicLib AddPoint takes (latitude, longitude).
    """
    geod = Geodesic.WGS84
    poly = geod.Polygon()

    # GeoJSON LinearRing has first point == last point.
    # GeographicLib Polygon does not need the duplicated closing point.
    points_to_add = coords[:-1] if (len(coords) > 1 and coords[0] == coords[-1]) else coords

    for pt in points_to_add:
        lon, lat = pt[0], pt[1]
        poly.AddPoint(lat, lon)

    num, perimeter, area = poly.Compute()
    return abs(area), abs(perimeter)


def compute_geodesic_area_ha(geometry: Dict[str, Any]) -> Tuple[float, float]:
    """
    Computes exact WGS84 ellipsoidal geodesic area (hectares) and perimeter (meters).
    Handles:
    - GeoJSON Polygon with interior holes (holes are subtracted from exterior)
    - GeoJSON MultiPolygon (sums components)
    - GeoJSON Feature (extracts geometry)

    Returns:
        (area_ha, perimeter_m)
    """
    if not geometry:
        raise ValueError("Geometry dictionary cannot be empty")

    geom_type = geometry.get("type")
    if geom_type == "Feature":
        geometry = geometry.get("geometry", {})
        geom_type = geometry.get("type")

    coords = geometry.get("coordinates")
    if not coords or not geom_type:
        raise ValueError(f"Invalid GeoJSON geometry: type='{geom_type}', coordinates missing")

    total_area_m2 = 0.0
    total_perimeter_m = 0.0

    if geom_type == "Polygon":
        # coords is list of rings: coords[0] is exterior, coords[1:] are interior holes
        if not coords or len(coords[0]) < 3:
            raise ValueError("Polygon must have at least one exterior ring with at least 3 vertices")

        exterior_area_m2, exterior_perim_m = _compute_ring_geodesic(coords[0])
        holes_area_m2 = 0.0
        holes_perim_m = 0.0

        for hole_ring in coords[1:]:
            if len(hole_ring) >= 3:
                h_area, h_perim = _compute_ring_geodesic(hole_ring)
                holes_area_m2 += h_area
                holes_perim_m += h_perim

        net_area_m2 = max(0.0, exterior_area_m2 - holes_area_m2)
        total_area_m2 = net_area_m2
        total_perimeter_m = exterior_perim_m + holes_perim_m

    elif geom_type == "MultiPolygon":
        # coords is list of polygon coordinate arrays
        for poly_coords in coords:
            if not poly_coords or len(poly_coords[0]) < 3:
                continue
            ext_area, ext_perim = _compute_ring_geodesic(poly_coords[0])
            holes_area = 0.0
            holes_perim = 0.0
            for hole_ring in poly_coords[1:]:
                if len(hole_ring) >= 3:
                    h_a, h_p = _compute_ring_geodesic(hole_ring)
                    holes_area += h_a
                    holes_perim += h_p
            total_area_m2 += max(0.0, ext_area - holes_area)
            total_perimeter_m += (ext_perim + holes_perim)

    else:
        raise ValueError(f"Unsupported geometry type for area calculation: '{geom_type}'. Must be Polygon or MultiPolygon.")

    area_ha = round(total_area_m2 / 10000.0, 4)
    perimeter_m = round(total_perimeter_m, 2)
    return area_ha, perimeter_m


def compute_centroid(geometry: Dict[str, Any]) -> Tuple[float, float]:
    """
    Computes arithmetic centroid (latitude, longitude) from GeoJSON geometry.
    """
    geom_type = geometry.get("type")
    if geom_type == "Feature":
        geometry = geometry.get("geometry", {})
        geom_type = geometry.get("type")

    coords = geometry.get("coordinates", [])

    all_points: List[List[float]] = []

    if geom_type == "Polygon":
        if coords and len(coords) > 0:
            ring = coords[0]
            pts = ring[:-1] if (len(ring) > 1 and ring[0] == ring[-1]) else ring
            all_points.extend(pts)
    elif geom_type == "MultiPolygon":
        for poly_coords in coords:
            if poly_coords and len(poly_coords) > 0:
                ring = poly_coords[0]
                pts = ring[:-1] if (len(ring) > 1 and ring[0] == ring[-1]) else ring
                all_points.extend(pts)
    elif geom_type == "Point":
        return coords[1], coords[0]

    if not all_points:
        return 0.0, 0.0

    avg_lon = sum(pt[0] for pt in all_points) / len(all_points)
    avg_lat = sum(pt[1] for pt in all_points) / len(all_points)
    return round(avg_lat, 6), round(avg_lon, 6)


def _segments_intersect(p1: Tuple[float, float], p2: Tuple[float, float],
                        p3: Tuple[float, float], p4: Tuple[float, float]) -> bool:
    """Checks if line segment p1-p2 strictly intersects line segment p3-p4."""
    def ccw(a, b, c):
        return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])

    # Endpoints sharing vertex is not an invalid self-intersection
    if p1 == p3 or p1 == p4 or p2 == p3 or p2 == p4:
        return False

    return (ccw(p1, p3, p4) != ccw(p2, p3, p4)) and (ccw(p1, p2, p3) != ccw(p1, p2, p4))


def has_self_intersection(ring: List[List[float]]) -> bool:
    """
    Validates that a linear ring does not self-intersect.
    """
    pts = [(pt[0], pt[1]) for pt in ring]
    n = len(pts)
    if n < 4:
        return False

    for i in range(n - 1):
        for j in range(i + 2, n - 1):
            if i == 0 and j == n - 2:
                continue  # Adjacent segments meeting at closing point
            if _segments_intersect(pts[i], pts[i + 1], pts[j], pts[j + 1]):
                return True
    return False


def validate_geojson_polygon(geometry: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validates GeoJSON topology for land unit boundaries:
    - Geometry type is Polygon or MultiPolygon
    - Ring coordinate structure and depth
    - Ring closure (first vertex equals last vertex)
    - Valid WGS84 coordinate bounds: lon in [-180, 180], lat in [-90, 90]
    - Self-intersection checks

    Returns:
        (is_valid, error_message)
    """
    if not isinstance(geometry, dict):
        return False, "Geometry must be a JSON object"

    geom_type = geometry.get("type")
    if geom_type == "Feature":
        geometry = geometry.get("geometry", {})
        geom_type = geometry.get("type")

    if geom_type not in ("Polygon", "MultiPolygon"):
        return False, f"Invalid geometry type '{geom_type}'. Only 'Polygon' and 'MultiPolygon' are permitted for land units."

    coords = geometry.get("coordinates")
    if not coords or not isinstance(coords, list):
        return False, "Coordinates array is missing or invalid"

    polygons = [coords] if geom_type == "Polygon" else coords

    for poly_idx, poly in enumerate(polygons):
        if not isinstance(poly, list) or len(poly) == 0:
            return False, f"Polygon {poly_idx} must contain at least an exterior linear ring"

        for ring_idx, ring in enumerate(poly):
            if not isinstance(ring, list) or len(ring) < 4:
                return False, f"Ring {ring_idx} in polygon {poly_idx} must have at least 4 coordinate pairs (minimum 3 vertices + closing point)"

            # Check closure
            first_pt, last_pt = ring[0], ring[-1]
            if first_pt[0] != last_pt[0] or first_pt[1] != last_pt[1]:
                return False, f"Ring {ring_idx} in polygon {poly_idx} is not closed. First coordinate {first_pt} != last {last_pt}."

            # Check coordinate bounds
            for pt_idx, pt in enumerate(ring):
                if not isinstance(pt, (list, tuple)) or len(pt) < 2:
                    return False, f"Invalid vertex at index {pt_idx} in ring {ring_idx}: expected [lon, lat]"
                lon, lat = pt[0], pt[1]
                if not (-180.0 <= lon <= 180.0):
                    return False, f"Longitude {lon} out of WGS84 bounds [-180, 180] at vertex {pt_idx}"
                if not (-90.0 <= lat <= 90.0):
                    return False, f"Latitude {lat} out of WGS84 bounds [-90, 90] at vertex {pt_idx}"

            # Self-intersection check on exterior ring
            if ring_idx == 0 and has_self_intersection(ring):
                return False, f"Exterior ring in polygon {poly_idx} has self-intersecting segments"

    return True, None
