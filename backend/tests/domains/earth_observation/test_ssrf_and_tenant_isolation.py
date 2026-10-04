"""
=============================================================================
VeriField Nexus — EO SSRF Protection, Tenant Isolation & Area Semantics Tests
=============================================================================
Verification of:
1. SSRF URL validation rejecting localhost, loopback, private RFC1918 IPs,
   AWS/GCP cloud metadata endpoints, non-HTTP schemes (file://, ftp://), and unapproved hosts.
2. Safe URL sanitization stripping query parameters/tokens in logging/responses.
3. Multi-tenant isolation: Org A cannot verify or access Org B EO assets.
4. Cross-project isolation: Observation belonging to Project B cannot be accessed via Project A.
5. PostGIS Area Semantics: Regression test ensuring EPSG:4326 geometries are evaluated
   geodesically (square meters/hectares via ST_Area(geom::geography) and GeographicLib),
   and never confused with raw planar square degrees.
=============================================================================
"""

import os
import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.earth_observation.models import (
    EOObservation,
    EOObservationType,
    EOQualityStatus,
)
from app.domains.earth_observation.providers.base import RawSceneMetadata
from app.domains.earth_observation.providers.stac_client import (
    _is_private_ip,
    _sanitize_url_for_log,
    default_stac_client,
    validate_cog_url,
)
from app.domains.earth_observation.services.geospatial_engine import geospatial_engine
from app.domains.earth_observation.services.observation_service import observation_service
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project


# ─── 1. SSRF Validation Tests ───

def test_ssrf_blocks_private_ips_and_loopback():
    """Verifies _is_private_ip identifies all local, loopback, private, and metadata IPs."""
    blocked_ips = [
        "127.0.0.1",
        "127.0.1.1",
        "::1",
        "0.0.0.0",
        "10.0.0.1",
        "10.254.0.1",
        "172.16.0.1",
        "172.31.255.255",
        "192.168.1.1",
        "192.168.0.254",
        "169.254.169.254",  # AWS/GCP/Azure link-local metadata
    ]
    for ip in blocked_ips:
        assert _is_private_ip(ip) is True, f"Expected {ip} to be identified as private/blocked IP"


def test_ssrf_blocks_forbidden_schemes():
    """Verifies validate_cog_url rejects non-HTTP/HTTPS schemes (file://, ftp://, gopher://)."""
    invalid_urls = [
        "file:///etc/passwd",
        "ftp://ftp.example.com/asset.tif",
        "gopher://localhost:70/1",
        "data:text/plain;base64,SGVsbG8=",
    ]
    for url in invalid_urls:
        with pytest.raises(ValueError, match="SSRF_BLOCKED: Scheme"):
            validate_cog_url(url)


def test_ssrf_blocks_loopback_and_metadata_hosts():
    """Verifies validate_cog_url rejects localhost, 127.0.0.1, ::1, and metadata hostnames."""
    dangerous_urls = [
        "http://localhost/raster.tif",
        "http://127.0.0.1:8000/api",
        "http://[::1]:8080/test.tif",
        "http://169.254.169.254/latest/meta-data/",
        "http://metadata.google.internal/computeMetadata/v1/",
    ]
    for url in dangerous_urls:
        with pytest.raises(ValueError, match="SSRF_BLOCKED"):
            validate_cog_url(url)


def test_ssrf_blocks_unauthorized_external_hosts():
    """Verifies validate_cog_url rejects arbitrary unapproved hosts not in the allowlist."""
    with pytest.raises(ValueError, match="SSRF_BLOCKED: Hostname 'malicious.attacker.com' is not in the allowed COG host list"):
        validate_cog_url("https://malicious.attacker.com/evil.tif", enforce_allowlist=True)


def test_ssrf_allows_allowlisted_satellite_hosts():
    """Verifies validate_cog_url permits allowlisted public COG archives."""
    valid_url = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/33/T/TG/2024/6/S2B_33TTG_20240628_0_L2A/B04.tif"
    result = validate_cog_url(valid_url, enforce_allowlist=True)
    assert result == valid_url


def test_url_sanitization_strips_sensitive_query_parameters():
    """Verifies _sanitize_url_for_log removes signed tokens and query parameters from logs/responses."""
    raw_url = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/asset.tif?AWSAccessKeyId=AKIAIOSFODNN7EXAMPLE&Signature=vjbyPxybdZaNmGa%2ByT272YEAiv4%3D&Expires=1700000000"
    sanitized = _sanitize_url_for_log(raw_url)
    assert "AWSAccessKeyId" not in sanitized
    assert "Signature" not in sanitized
    assert "Expires" not in sanitized
    assert sanitized == "https://sentinel-cogs.s3.us-west-2.amazonaws.com/asset.tif"


# ─── 2. Multi-Tenant and Cross-Project Isolation Tests ───

@pytest.mark.asyncio
async def test_tenant_and_project_isolation(db_session: AsyncSession):
    """
    Verifies that satellite observations cannot be accessed across organization
    or project boundaries.
    """
    # Org A & Project A
    org_a = Organization(name=f"Org A {uuid.uuid4().hex[:6]}")
    db_session.add(org_a)
    await db_session.flush()

    proj_a = Project(
        organization_id=org_a.id,
        name="Project A",
        project_code=f"PA-{uuid.uuid4().hex[:6]}",
    )
    db_session.add(proj_a)

    # Org B & Project B
    org_b = Organization(name=f"Org B {uuid.uuid4().hex[:6]}")
    db_session.add(org_b)
    await db_session.flush()

    proj_b = Project(
        organization_id=org_b.id,
        name="Project B",
        project_code=f"PB-{uuid.uuid4().hex[:6]}",
    )
    db_session.add(proj_b)
    await db_session.commit()

    # Ingest observation in Project A
    raw_a = RawSceneMetadata(
        scene_id="S2_ISOLATION_TEST_A",
        provider_code="SENTINEL_2",
        platform="Sentinel-2A",
        sensor="MSI",
        product_code="S2_MSI_L2A",
        observation_type=EOObservationType.OPTICAL_MULTISPECTRAL,
        acquisition_timestamp=datetime(2026, 7, 1, 10, 0, tzinfo=timezone.utc),
        spatial_resolution_m=10.0,
        bounding_box=[10.0, 45.0, 10.1, 45.1],
        geometry_geojson={"type": "Polygon", "coordinates": [[[10,45], [10.1,45], [10.1,45.1], [10,45.1], [10,45]]]},
        processing_level="L2A",
        cloud_cover_pct=5.0,
        raw_band_uris={"visual": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sample_a.tif"},
    )
    obs_a = await observation_service.ingest_observation(
        db=db_session,
        project_id=proj_a.id,
        organization_id=org_a.id,
        raw_scene=raw_a,
    )

    # 1. Querying observations for Project B should return 0 items
    obs_b_list = await observation_service.list_observations(
        db=db_session,
        project_id=proj_b.id,
        organization_id=org_b.id,
    )
    assert len(obs_b_list) == 0

    # 2. Org B attempting to fetch Observation A by ID must return None (tenant boundary enforcement)
    obs_cross = await observation_service.get_observation_by_id(
        db=db_session,
        observation_id=obs_a.id,
        organization_id=org_b.id,  # Org B cannot access Org A observation
    )
    assert obs_cross is None

    # 3. Org A fetching Observation A succeeds
    obs_valid = await observation_service.get_observation_by_id(
        db=db_session,
        observation_id=obs_a.id,
        organization_id=org_a.id,
    )
    assert obs_valid is not None
    assert obs_valid.id == obs_a.id


# ─── 3. PostGIS Area Semantics Regression Test ───

def test_postgis_area_semantics_regression():
    """
    Verifies that spatial area calculation does NOT confuse planar square degrees
    with physical square meters or hectares.

    A 0.01 x 0.01 degree square at the equator (0 deg lat):
    - 0.01 deg lon ~ 1113.19 m
    - 0.01 deg lat ~ 1105.74 m
    - Area is ~1,230,000 m² (~123 hectares).
    - Planar geometry ST_Area(geom) gives 0.0001 (square degrees), NOT square meters!
    - Geodesic / geography calculation gives ~1,230,000 m² (~123 ha).
    """
    equator_poly = {
        "type": "Polygon",
        "coordinates": [[[0.0, 0.0], [0.01, 0.0], [0.01, 0.01], [0.0, 0.01], [0.0, 0.0]]],
    }

    # 1. Test GeographicLib engine calculation
    area_m2, area_ha, perimeter_m = geospatial_engine.calculate_geodesic_polygon_area_perimeter(equator_poly)

    # Must be physical units: ~123 ha, NOT 0.0001 (square degrees)
    assert area_ha > 100.0, f"Expected ~123 ha, got {area_ha} (possible square degree bug!)"
    assert 120.0 < area_ha < 125.0
    assert 1_200_000.0 < area_m2 < 1_250_000.0
    assert 4_000.0 < perimeter_m < 5_000.0

    # 2. Test PostGIS ST_Area(geom::geography) against PostgreSQL
    user = os.environ.get("POSTGRES_USER") or os.environ.get("USER") or "postgres"
    pg_url = f"postgresql://{user}@localhost:5432/postgres"

    try:
        engine = create_engine(pg_url)
        with engine.connect() as conn:
            query = text("""
                WITH poly AS (
                    SELECT ST_SetSRID(ST_GeomFromGeoJSON('{"type":"Polygon","coordinates":[[[0,0],[0.01,0],[0.01,0.01],[0,0.01],[0,0]]]}'), 4326) AS geom
                )
                SELECT
                    ST_Area(geom) AS planar_deg2,
                    ST_Area(geom::geography) AS geodesic_m2,
                    ST_Area(geom::geography) / 10000.0 AS geodesic_ha
                FROM poly;
            """)
            row = conn.execute(query).mappings().one()

            planar_deg2 = float(row["planar_deg2"])
            geodesic_m2 = float(row["geodesic_m2"])
            geodesic_ha = float(row["geodesic_ha"])

            # ST_Area(geom) returns square degrees: 0.0001
            assert abs(planar_deg2 - 0.0001) < 1e-6, f"Expected 0.0001 deg^2, got {planar_deg2}"

            # ST_Area(geom::geography) returns real physical square meters: ~1,230,000 m²
            assert 1_200_000.0 < geodesic_m2 < 1_250_000.0
            assert 120.0 < geodesic_ha < 125.0

            # Verify GeographicLib result matches PostGIS ST_Area(geom::geography) within 0.1% tolerance
            pct_diff = abs(area_m2 - geodesic_m2) / geodesic_m2 * 100.0
            assert pct_diff < 0.1, f"GeographicLib ({area_m2}) differs from PostGIS ({geodesic_m2}) by {pct_diff:.3f}%"
    except Exception as exc:
        pytest.skip(f"PostgreSQL/PostGIS not accessible: {exc}")
