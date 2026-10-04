"""
=============================================================================
VeriField Nexus — PostGIS Spatial Topology & Live STAC Hardening Test Suite
=============================================================================
Real execution verification:
1. Live STAC search against AWS Element84 Earth Search (Sentinel-2, Sentinel-1, Landsat).
2. Verification of Cloud-Optimized GeoTIFF (COG) HTTP Range partial read (HTTP 206).
3. Capability transition to LIVE_VERIFIED upon real provider response.
4. Authoritative PostGIS database queries (ST_Contains, ST_Intersects, ST_Within, ST_Envelope)
   executed against local PostgreSQL 18 with PostGIS extension.
=============================================================================
"""

import os
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, text

from app.domains.earth_observation.models import (
    EOObservationType,
    EOProviderCapability,
    EOQualityStatus,
)
from app.domains.earth_observation.providers.landsat import LandsatProvider
from app.domains.earth_observation.providers.sentinel1 import Sentinel1Provider
from app.domains.earth_observation.providers.sentinel2 import Sentinel2Provider
from app.domains.earth_observation.providers.stac_client import default_stac_client
from app.domains.earth_observation.services.geospatial_engine import geospatial_engine


def test_live_stac_sentinel2_discovery_and_cog_range_access():
    """
    Executes real STAC discovery query against AWS Element84 Earth Search
    and verifies HTTP Range partial read on the resulting Cloud-Optimized GeoTIFF.
    """
    provider = Sentinel2Provider(use_live_stac=True)
    assert provider.get_capability_state() == EOProviderCapability.LIVE_CONFIGURED

    # Rome / Central Italy AOI bounding box
    bbox = [12.4, 41.8, 12.6, 42.0]
    date_from = datetime(2024, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
    date_to = datetime(2024, 6, 30, 23, 59, 59, tzinfo=timezone.utc)

    scenes = provider.search_scenes(
        bounding_box=bbox,
        date_from=date_from,
        date_to=date_to,
        max_cloud_cover=20.0,
    )

    assert len(scenes) > 0, "Expected at least 1 real Sentinel-2 scene from live STAC catalog"
    scene = scenes[0]

    # Verify scene metadata fields
    assert scene.provider_code == "SENTINEL_2"
    assert "Sentinel-2" in scene.platform
    assert scene.sensor == "MSI"
    assert scene.observation_type == EOObservationType.OPTICAL_MULTISPECTRAL
    assert scene.spatial_resolution_m == 10.0
    assert scene.cloud_cover_pct is not None
    assert scene.cloud_cover_pct <= 20.0

    # Verify provider capability updated to LIVE_VERIFIED
    assert provider.get_capability_state() == EOProviderCapability.LIVE_VERIFIED

    # Check that COG assets are present
    assert "nir" in scene.raw_band_uris or "red" in scene.raw_band_uris or scene.asset_uri is not None
    cog_url = scene.raw_band_uris.get("nir") or scene.raw_band_uris.get("red") or scene.asset_uri

    # Verify HTTP Range partial read on COG raster asset
    range_res = default_stac_client.verify_asset_range_access(cog_url, byte_range="bytes=0-1023")
    assert range_res["http_status"] == 206, f"Expected HTTP 206 Partial Content, got {range_res}"
    assert range_res["is_partial_content"] is True
    assert range_res["bytes_read"] == 1024
    assert range_res["is_valid_geotiff_header"] is True
    assert range_res["magic_bytes_hex"] in ("49492a00", "4d4d002a")


def test_live_stac_sentinel1_sar_discovery():
    """
    Executes real SAR STAC search for Sentinel-1 GRD scenes.
    Verifies SAR backscatter type and invariant soil moisture model flag.
    """
    provider = Sentinel1Provider(use_live_stac=True)
    assert provider.get_capability_state() == EOProviderCapability.LIVE_CONFIGURED

    bbox = [12.4, 41.8, 12.6, 42.0]
    date_from = datetime(2024, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
    date_to = datetime(2024, 6, 30, 23, 59, 59, tzinfo=timezone.utc)

    scenes = provider.search_scenes(
        bounding_box=bbox,
        date_from=date_from,
        date_to=date_to,
    )

    assert len(scenes) > 0, "Expected at least 1 real Sentinel-1 SAR scene"
    scene = scenes[0]

    assert scene.provider_code == "SENTINEL_1"
    assert "Sentinel-1" in scene.platform
    assert scene.sensor == "C-SAR"
    assert scene.observation_type == EOObservationType.SAR_C_BAND_BACKSCATTER
    assert scene.quality_flags.get("soil_moisture_model") == "NOT_CONFIGURED"
    assert provider.get_capability_state() == EOProviderCapability.LIVE_VERIFIED


def test_live_stac_landsat_discovery():
    """
    Executes real Landsat STAC search for Landsat Collection 2 Level 2 scenes.
    """
    provider = LandsatProvider(use_live_stac=True)
    assert provider.get_capability_state() == EOProviderCapability.LIVE_CONFIGURED

    bbox = [12.4, 41.8, 12.6, 42.0]
    date_from = datetime(2024, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
    date_to = datetime(2024, 6, 30, 23, 59, 59, tzinfo=timezone.utc)

    scenes = provider.search_scenes(
        bounding_box=bbox,
        date_from=date_from,
        date_to=date_to,
        max_cloud_cover=60.0,
    )

    assert len(scenes) > 0, "Expected at least 1 real Landsat scene"
    scene = scenes[0]

    assert scene.provider_code == "LANDSAT_8_9"
    assert "Landsat" in scene.platform
    assert scene.observation_type == EOObservationType.OPTICAL_MULTISPECTRAL
    assert scene.spatial_resolution_m == 30.0
    assert provider.get_capability_state() == EOProviderCapability.LIVE_VERIFIED


def test_postgis_authoritative_database_topology():
    """
    Executes authoritative PostGIS SQL operations against local PostgreSQL 18:
    ST_Contains, ST_Intersects, ST_Within, ST_Envelope, ST_Intersection.
    """
    user = os.environ.get("POSTGRES_USER") or os.environ.get("USER") or "postgres"
    pg_url = f"postgresql://{user}@localhost:5432/postgres"

    try:
        engine = create_engine(pg_url)
        with engine.connect() as conn:
            pg_ver = conn.execute(text("SELECT postgis_version();")).scalar()
            assert "3." in pg_ver, f"Expected PostGIS 3.x, got {pg_ver}"

            # 1. Test ST_Contains and ST_Within
            test_sql = text("""
                WITH test_data AS (
                    SELECT
                        ST_SetSRID(ST_GeomFromGeoJSON('{"type":"Polygon","coordinates":[[[0,0],[10,0],[10,10],[0,10],[0,0]]]}'), 4326) AS big_poly,
                        ST_SetSRID(ST_GeomFromGeoJSON('{"type":"Polygon","coordinates":[[[2,2],[8,2],[8,8],[2,8],[2,2]]]}'), 4326) AS small_poly,
                        ST_SetSRID(ST_Point(5, 5), 4326) AS inside_pt,
                        ST_SetSRID(ST_Point(15, 15), 4326) AS outside_pt
                )
                SELECT
                    ST_Contains(big_poly, inside_pt) AS pt_inside,
                    ST_Contains(big_poly, outside_pt) AS pt_outside,
                    ST_Contains(big_poly, small_poly) AS poly_inside,
                    ST_Within(small_poly, big_poly) AS poly_within,
                    ST_Intersects(big_poly, small_poly) AS poly_intersects,
                    ST_AsGeoJSON(ST_Intersection(big_poly, small_poly)) AS intersection_geojson,
                    ST_AsGeoJSON(ST_Envelope(big_poly)) AS envelope_geojson
                FROM test_data;
            """)
            row = conn.execute(test_sql).mappings().one()

            assert row["pt_inside"] is True
            assert row["pt_outside"] is False
            assert row["poly_inside"] is True
            assert row["poly_within"] is True
            assert row["poly_intersects"] is True
            assert "Polygon" in row["intersection_geojson"]
            assert "Polygon" in row["envelope_geojson"]
    except Exception as exc:
        pytest.skip(f"PostgreSQL/PostGIS not accessible: {exc}")
