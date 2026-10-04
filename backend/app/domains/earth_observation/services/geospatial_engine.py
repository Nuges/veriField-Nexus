"""
=============================================================================
VeriField Nexus — WGS84 Geodesic Spatial Engine
=============================================================================
Provides precise, platform-independent geospatial calculations:
- WGS84 ellipsoidal area and perimeter calculations via GeographicLib (exact geodesic).
- Topological point-in-polygon containment via ray casting with hole deduction.
- Bounding box extraction [min_lon, min_lat, max_lon, max_lat].
- GeoJSON validation, normalization, and ring closure.
- Supports GeoJSON Polygon and MultiPolygon geometries.
=============================================================================
"""

import json
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Tuple
from geographiclib.geodesic import Geodesic
from shapely.geometry import Point, shape, mapping
from shapely.validation import make_valid
from sqlalchemy import func


class SpatialBackendState(str, Enum):
    POSTGIS_ACTIVE = "POSTGIS_ACTIVE"
    SQLITE_SPATIAL_FALLBACK = "SQLITE_SPATIAL_FALLBACK"
    SPATIAL_BACKEND_UNAVAILABLE = "SPATIAL_BACKEND_UNAVAILABLE"


class GeospatialEngine:
    """
    Geospatial calculation engine utilizing WGS84 ellipsoid parameters (GeographicLib)
    authoritative in-memory topology (Shapely), and PostGIS SQL spatial expressions.
    """

    def __init__(self):
        self._geod = Geodesic.WGS84

    def validate_and_normalize_geojson(self, geometry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates GeoJSON Polygon or MultiPolygon geometry.
        Ensures coordinate ranges are valid WGS84 [-180..180], [-90..90]
        and rings are properly closed.
        """
        if not isinstance(geometry, dict):
            raise ValueError("Geometry must be a dictionary.")

        geom_type = geometry.get("type")
        if geom_type not in ("Polygon", "MultiPolygon"):
            raise ValueError(f"Unsupported geometry type: '{geom_type}'. Must be 'Polygon' or 'MultiPolygon'.")

        coordinates = geometry.get("coordinates")
        if not coordinates or not isinstance(coordinates, list):
            raise ValueError("Geometry 'coordinates' must be a non-empty list.")

        def _validate_and_close_ring(ring: List[List[float]]) -> List[List[float]]:
            if not isinstance(ring, list) or len(ring) < 3:
                raise ValueError("A linear ring must have at least 3 distinct positions.")

            # Check positions
            normalized_ring = []
            for pt in ring:
                if not isinstance(pt, (list, tuple)) or len(pt) < 2:
                    raise ValueError(f"Invalid coordinate position: {pt}")
                lon, lat = float(pt[0]), float(pt[1])
                if not (-180.0 <= lon <= 180.0):
                    raise ValueError(f"Longitude {lon} out of WGS84 range [-180, 180].")
                if not (-90.0 <= lat <= 90.0):
                    raise ValueError(f"Latitude {lat} out of WGS84 range [-90, 90].")
                normalized_ring.append([lon, lat])

            # Ensure closure
            first = normalized_ring[0]
            last = normalized_ring[-1]
            if not (math.isclose(first[0], last[0], abs_tol=1e-8) and math.isclose(first[1], last[1], abs_tol=1e-8)):
                normalized_ring.append([first[0], first[1]])

            if len(normalized_ring) < 4:
                raise ValueError("A closed linear ring must have at least 4 positions (including closure).")

            return normalized_ring

        if geom_type == "Polygon":
            normalized_coords = []
            for ring in coordinates:
                normalized_coords.append(_validate_and_close_ring(ring))
            return {"type": "Polygon", "coordinates": normalized_coords}

        elif geom_type == "MultiPolygon":
            normalized_mp = []
            for poly in coordinates:
                if not isinstance(poly, list) or len(poly) == 0:
                    raise ValueError("MultiPolygon components must be non-empty polygon coordinate lists.")
                poly_rings = []
                for ring in poly:
                    poly_rings.append(_validate_and_close_ring(ring))
                normalized_mp.append(poly_rings)
            return {"type": "MultiPolygon", "coordinates": normalized_mp}

        raise ValueError(f"Unhandled geometry type: {geom_type}")

    def calculate_geodesic_polygon_area_perimeter(
        self, geometry: Dict[str, Any]
    ) -> Tuple[float, float, float]:
        """
        Computes the exact WGS84 ellipsoidal area (m² and hectares) and perimeter (m).
        Accurately subtracts interior ring (hole) areas from the exterior ring.
        Returns: (area_m2, area_hectares, perimeter_m)
        """
        norm_geom = self.validate_and_normalize_geojson(geometry)
        geom_type = norm_geom["type"]
        coords = norm_geom["coordinates"]

        def _compute_ring(ring: List[List[float]]) -> Tuple[float, float]:
            poly = self._geod.Polygon()
            # In GeographicLib, AddPoint takes (latitude, longitude)
            # In GeoJSON, coordinate is [longitude, latitude]
            for pt in ring:
                poly.AddPoint(pt[1], pt[0])
            _, perimeter, area = poly.Compute()
            return abs(area), abs(perimeter)

        total_area_m2 = 0.0
        total_perimeter_m = 0.0

        polygons = [coords] if geom_type == "Polygon" else coords

        for poly in polygons:
            if not poly:
                continue
            # Exterior ring
            ext_area, ext_perim = _compute_ring(poly[0])
            poly_area = ext_area
            poly_perim = ext_perim

            # Interior rings (holes)
            for hole in poly[1:]:
                hole_area, hole_perim = _compute_ring(hole)
                poly_area -= hole_area
                poly_perim += hole_perim

            total_area_m2 += max(0.0, poly_area)
            total_perimeter_m += poly_perim

        total_hectares = total_area_m2 / 10000.0
        return round(total_area_m2, 2), round(total_hectares, 4), round(total_perimeter_m, 2)

    def calculate_bounding_box(self, geometry: Dict[str, Any]) -> List[float]:
        """
        Computes [min_lon, min_lat, max_lon, max_lat] for a Polygon or MultiPolygon.
        """
        norm_geom = self.validate_and_normalize_geojson(geometry)
        geom_type = norm_geom["type"]
        coords = norm_geom["coordinates"]

        min_lon = float("inf")
        min_lat = float("inf")
        max_lon = float("-inf")
        max_lat = float("-inf")

        polygons = [coords] if geom_type == "Polygon" else coords

        for poly in polygons:
            for ring in poly:
                for pt in ring:
                    lon, lat = pt[0], pt[1]
                    if lon < min_lon:
                        min_lon = lon
                    if lon > max_lon:
                        max_lon = lon
                    if lat < min_lat:
                        min_lat = lat
                    if lat > max_lat:
                        max_lat = lat

        return [round(min_lon, 6), round(min_lat, 6), round(max_lon, 6), round(max_lat, 6)]

    def geometry_to_shape(self, geometry: Dict[str, Any]):
        """
        Converts validated GeoJSON dictionary to an authoritative Shapely geometry.
        Automatically heals topology defects using shapely.validation.make_valid.
        """
        norm_geom = self.validate_and_normalize_geojson(geometry)
        geom = shape(norm_geom)
        if not geom.is_valid:
            geom = make_valid(geom)
        return geom

    def point_in_polygon(self, lon: float, lat: float, geometry: Dict[str, Any]) -> bool:
        """
        Authoritative topological point-in-polygon containment test using Shapely.
        Tests whether (lon, lat) point falls within the GeoJSON geometry.
        Accurately enforces exterior boundary containment and interior hole exclusion.
        """
        geom = self.geometry_to_shape(geometry)
        pt = Point(float(lon), float(lat))
        # contains: strictly inside; touches: on boundary; covers: inside or on boundary
        return bool(geom.contains(pt) or geom.covers(pt))

    def geometry_intersects(self, geom1: Dict[str, Any], geom2: Dict[str, Any]) -> bool:
        """
        Authoritative in-memory spatial intersection test between two geometries using Shapely.
        """
        s1 = self.geometry_to_shape(geom1)
        s2 = self.geometry_to_shape(geom2)
        return bool(s1.intersects(s2))

    def geometry_contains(self, container_geom: Dict[str, Any], contained_geom: Dict[str, Any]) -> bool:
        """
        Authoritative in-memory spatial containment test using Shapely.
        Returns True if container_geom completely contains contained_geom.
        """
        s1 = self.geometry_to_shape(container_geom)
        s2 = self.geometry_to_shape(contained_geom)
        return bool(s1.contains(s2) or s1.covers(s2))

    def geometry_within(self, contained_geom: Dict[str, Any], container_geom: Dict[str, Any]) -> bool:
        """
        Authoritative in-memory spatial within test using Shapely.
        Returns True if contained_geom is completely within container_geom.
        """
        s1 = self.geometry_to_shape(contained_geom)
        s2 = self.geometry_to_shape(container_geom)
        return bool(s1.within(s2))

    def geometry_intersection(self, geom1: Dict[str, Any], geom2: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Authoritative in-memory topological geometric intersection using Shapely.
        Returns GeoJSON mapping of intersection or None if disjoint.
        """
        s1 = self.geometry_to_shape(geom1)
        s2 = self.geometry_to_shape(geom2)
        inter = s1.intersection(s2)
        if inter.is_empty:
            return None
        return mapping(inter)

    # -------------------------------------------------------------------------
    # PostGIS Authoritative SQL Spatial Expressions
    # -------------------------------------------------------------------------

    @staticmethod
    def postgis_st_contains(geom_col: Any, target_geom: Any):
        """
        Constructs a PostGIS ST_Contains SQL expression.
        Accepts GeoJSON dict, WKT, or SQLAlchemy geometry column.
        """
        if isinstance(target_geom, dict):
            geom_expr = func.ST_SetSRID(func.ST_GeomFromGeoJSON(json.dumps(target_geom)), 4326)
        else:
            geom_expr = target_geom
        return func.ST_Contains(geom_col, geom_expr)

    @staticmethod
    def postgis_st_intersects(geom_col: Any, target_geom: Any):
        """
        Constructs a PostGIS ST_Intersects SQL expression.
        Accepts GeoJSON dict, WKT, or SQLAlchemy geometry column.
        """
        if isinstance(target_geom, dict):
            geom_expr = func.ST_SetSRID(func.ST_GeomFromGeoJSON(json.dumps(target_geom)), 4326)
        else:
            geom_expr = target_geom
        return func.ST_Intersects(geom_col, geom_expr)

    @staticmethod
    def postgis_st_within(geom_col: Any, container_geom: Any):
        """
        Constructs a PostGIS ST_Within SQL expression.
        Accepts GeoJSON dict, WKT, or SQLAlchemy geometry column.
        """
        if isinstance(container_geom, dict):
            geom_expr = func.ST_SetSRID(func.ST_GeomFromGeoJSON(json.dumps(container_geom)), 4326)
        else:
            geom_expr = container_geom
        return func.ST_Within(geom_col, geom_expr)

    @staticmethod
    def postgis_st_intersection(geom1: Any, geom2: Any):
        """
        Constructs a PostGIS ST_Intersection SQL expression.
        """
        def _to_expr(g: Any):
            if isinstance(g, dict):
                return func.ST_SetSRID(func.ST_GeomFromGeoJSON(json.dumps(g)), 4326)
            return g

        return func.ST_Intersection(_to_expr(geom1), _to_expr(geom2))

    @staticmethod
    def postgis_st_envelope(geom_col: Any):
        """
        Constructs a PostGIS ST_Envelope SQL expression.
        """
        return func.ST_Envelope(geom_col)

    @staticmethod
    async def detect_spatial_backend(session: Any) -> Dict[str, Any]:
        """
        Detects database spatial backend capabilities:
        - POSTGIS_ACTIVE: PostgreSQL with PostGIS extension active, geometry columns typed, GiST indexes enabled.
        - SQLITE_SPATIAL_FALLBACK: SQLite with in-memory Shapely topology and GeographicLib WGS84 geodesic calculations (supported for dev/test).
        - SPATIAL_BACKEND_UNAVAILABLE: PostgreSQL without PostGIS (unsupported), or neither database PostGIS nor Shapely available.
        """
        from sqlalchemy import text
        try:
            bind = session.bind if hasattr(session, "bind") else None
            dialect_name = bind.dialect.name if bind else "unknown"

            has_shapely = False
            try:
                import shapely  # noqa: F401
                has_shapely = True
            except ImportError:
                has_shapely = False

            if dialect_name == "postgresql":
                postgis_ver = None
                try:
                    res = await session.execute(text("SELECT postgis_version();"))
                    postgis_ver = res.scalar()
                except Exception:
                    postgis_ver = None

                if postgis_ver:
                    return {
                        "state": SpatialBackendState.POSTGIS_ACTIVE.value,
                        "postgis_version": str(postgis_ver),
                        "database_native_indexing": True,
                        "in_memory_topology": "Shapely 2.x + GeographicLib WGS84",
                        "production_ready": True,
                        "dialect": "postgresql",
                        "limitations": [],
                    }
                else:
                    return {
                        "state": SpatialBackendState.SPATIAL_BACKEND_UNAVAILABLE.value,
                        "postgis_version": None,
                        "database_native_indexing": False,
                        "in_memory_topology": "Shapely 2.x + GeographicLib WGS84" if has_shapely else None,
                        "production_ready": False,
                        "dialect": "postgresql",
                        "limitations": [
                            "PostgreSQL without PostGIS is UNSUPPORTED. PostGIS 3.3+ extension is required for spatial models and GeoAlchemy2 ST_AsEWKB functions.",
                        ],
                    }

            elif dialect_name == "sqlite":
                if has_shapely:
                    return {
                        "state": SpatialBackendState.SQLITE_SPATIAL_FALLBACK.value,
                        "postgis_version": None,
                        "database_native_indexing": False,
                        "in_memory_topology": "Shapely 2.x + GeographicLib WGS84",
                        "production_ready": False,
                        "dialect": "sqlite",
                        "limitations": [
                            "Development/test fallback only. Database-native GiST spatial indexing is unavailable.",
                            "Spatial containment and intersection queries evaluate in-memory.",
                        ],
                    }
                else:
                    return {
                        "state": SpatialBackendState.SPATIAL_BACKEND_UNAVAILABLE.value,
                        "postgis_version": None,
                        "database_native_indexing": False,
                        "in_memory_topology": None,
                        "production_ready": False,
                        "dialect": "sqlite",
                        "limitations": ["Shapely library unavailable for SQLite spatial fallback"],
                    }

            else:
                return {
                    "state": SpatialBackendState.SPATIAL_BACKEND_UNAVAILABLE.value,
                    "postgis_version": None,
                    "database_native_indexing": False,
                    "in_memory_topology": None,
                    "production_ready": False,
                    "dialect": dialect_name,
                    "limitations": [f"Unsupported database dialect '{dialect_name}' for spatial operations"],
                }

        except Exception as e:
            return {
                "state": SpatialBackendState.SPATIAL_BACKEND_UNAVAILABLE.value,
                "error": str(e),
                "database_native_indexing": False,
                "in_memory_topology": None,
                "production_ready": False,
                "dialect": "unknown",
                "limitations": ["Spatial backend check failed: " + str(e)],
            }


geospatial_engine = GeospatialEngine()
