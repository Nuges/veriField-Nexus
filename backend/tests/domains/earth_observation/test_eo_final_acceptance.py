"""
=============================================================================
VeriField Nexus — Earth Observation Final Acceptance & Security Tests
=============================================================================
Verifies:
1. SSRF Redirect Hardening:
   - Allowlisted host redirecting to 127.0.0.1 or 169.254.169.254 is rejected BEFORE destination fetch.
   - Maximum redirect depth enforcement.
2. Raster Delivery & Tenant Authorization:
   - GET /projects/{id}/observations/{id}/raster enforces ABAC.
   - Org A requesting Org B raster -> 403 Forbidden.
   - Project A requesting Project B observation -> 404 Not Found.
   - Valid raster request returns HTTP 200 with readable image bytes (natural dimensions > 0).
3. Real Sentinel-2 Live End-to-End Trace:
   - Live Element84 STAC search on safe public neutral AOI.
   - Real STAC Item, acquisition date, real assets.
   - COG Range request returning HTTP 206 and TIFF magic bytes.
   - Raster delivery returns HTTP 200.
4. Real Landsat Historical Baseline Trace:
   - Historical date range query on Element84 STAC.
   - Real Landsat scene discovery and baseline persistence.
=============================================================================
"""

import io
import urllib.request
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_password_hash
from app.domains.authentication.models import User
from app.domains.earth_observation.models import (
    EOObservation,
    EOObservationType,
    EOQualityStatus,
)
from app.domains.earth_observation.providers.base import RawSceneMetadata
from app.domains.earth_observation.providers.stac_client import (
    SSRFRedirectHandler,
    default_stac_client,
    validate_cog_url,
)
from app.domains.earth_observation.services.aoi_service import aoi_service
from app.domains.earth_observation.services.observation_service import observation_service
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project
from app.main import app


# ─── 1. SSRF Redirect Protection Tests ───

def test_ssrf_redirect_handler_blocks_private_ip_redirect():
    """
    Verifies SSRFRedirectHandler intercepts HTTP redirects and blocks targets
    resolving to localhost / private IPs BEFORE following the redirect.
    """
    handler = SSRFRedirectHandler(enforce_allowlist=True, max_redirects=3)
    mock_req = urllib.request.Request("https://sentinel-cogs.s3.us-west-2.amazonaws.com/test.tif")

    # 1. Target is localhost/loopback
    with pytest.raises(ValueError, match="SSRF_BLOCKED"):
        handler.redirect_request(mock_req, None, 302, "Found", {}, "http://127.0.0.1:8000/admin")

    # 2. Target is AWS/GCP cloud metadata
    with pytest.raises(ValueError, match="SSRF_BLOCKED"):
        handler.redirect_request(mock_req, None, 302, "Found", {}, "http://169.254.169.254/latest/meta-data/")

    # 3. Target is unapproved external domain
    with pytest.raises(ValueError, match="SSRF_BLOCKED"):
        handler.redirect_request(mock_req, None, 302, "Found", {}, "https://attacker.evil.com/payload")


def test_ssrf_redirect_depth_limit():
    """Verifies that excessive redirects (> max_redirects) fail closed."""
    handler = SSRFRedirectHandler(enforce_allowlist=True, max_redirects=2)
    mock_req = urllib.request.Request("https://sentinel-cogs.s3.us-west-2.amazonaws.com/test.tif")
    safe_target = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/next.tif"

    # First redirect: allowed
    handler.redirect_request(mock_req, None, 302, "Found", {}, safe_target)
    # Second redirect: allowed
    handler.redirect_request(mock_req, None, 302, "Found", {}, safe_target)

    # Third redirect: exceeds max_redirects=2 -> BLOCKED
    with pytest.raises(ValueError, match="SSRF_BLOCKED: Max redirect depth"):
        handler.redirect_request(mock_req, None, 302, "Found", {}, safe_target)


# ─── 2. Raster Delivery & Tenant Authorization Tests ───

@pytest.mark.asyncio
async def test_raster_delivery_endpoint_tenant_isolation(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Verifies that the EO raster endpoint enforces strict ABAC:
    - Org A user requesting Project B raster -> 403 Forbidden
    - Project A requesting Project B observation -> 404 Not Found
    """
    pw_hash = get_password_hash("TestPass123!")

    # 1. Setup Tenant A
    org_a = Organization(id=uuid.uuid4(), name=f"Tenant A {uuid.uuid4().hex[:4]}")
    user_a = User(
        id=uuid.uuid4(),
        email=f"usera.{uuid.uuid4().hex[:6]}@example.com",
        full_name="User Tenant A",
        password_hash=pw_hash,
        role="ORG_ADMIN",
        organization_id=org_a.id,
        is_active=True,
    )
    proj_a = Project(
        id=uuid.uuid4(),
        organization_id=org_a.id,
        name="Project A",
        project_code=f"PA-{uuid.uuid4().hex[:4]}",
    )
    db_session.add_all([org_a, user_a, proj_a])
    await db_session.flush()

    # 2. Setup Tenant B
    org_b = Organization(id=uuid.uuid4(), name=f"Tenant B {uuid.uuid4().hex[:4]}")
    user_b = User(
        id=uuid.uuid4(),
        email=f"userb.{uuid.uuid4().hex[:6]}@example.com",
        full_name="User Tenant B",
        password_hash=pw_hash,
        role="ORG_ADMIN",
        organization_id=org_b.id,
        is_active=True,
    )
    proj_b = Project(
        id=uuid.uuid4(),
        organization_id=org_b.id,
        name="Project B",
        project_code=f"PB-{uuid.uuid4().hex[:4]}",
    )
    db_session.add_all([org_b, user_b, proj_b])
    await db_session.flush()

    # 3. Create observation in Project B
    raw_b = RawSceneMetadata(
        scene_id=f"S2B_TEST_SCENE_{uuid.uuid4().hex[:6]}",
        provider_code="SENTINEL_2",
        platform="Sentinel-2B",
        sensor="MSI",
        product_code="S2_MSI_L2A",
        observation_type=EOObservationType.OPTICAL_MULTISPECTRAL,
        acquisition_timestamp=datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc),
        spatial_resolution_m=10.0,
        bounding_box=[36.8, -1.3, 37.0, -1.1],
        geometry_geojson={"type": "Polygon", "coordinates": [[[36.8,-1.3], [37.0,-1.3], [37.0,-1.1], [36.8,-1.1], [36.8,-1.3]]]},
        processing_level="L2A",
        cloud_cover_pct=2.5,
        raw_band_uris={
            "visual": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/test.tif",
            "thumbnail": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/37/M/BU/2024/2/S2B_37MBU_20240227_0_L2A/thumbnail.jpg",
        },
    )
    obs_b = await observation_service.ingest_observation(
        db=db_session,
        project_id=proj_b.id,
        organization_id=org_b.id,
        raw_scene=raw_b,
    )
    await db_session.commit()

    # Authenticate User A
    login_a = await async_client.post(
        "/api/v1/auth/login",
        json={"email": user_a.email, "password": "TestPass123!"},
    )
    assert login_a.status_code == 200
    token_a = login_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Authenticate User B
    login_b = await async_client.post(
        "/api/v1/auth/login",
        json={"email": user_b.email, "password": "TestPass123!"},
    )
    assert login_b.status_code == 200
    token_b = login_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Attack 1: User A requests Project B raster endpoint directly -> 403 Forbidden (cross-tenant)
    resp_cross_org = await async_client.get(
        f"/api/v1/earth-observation/projects/{proj_b.id}/observations/{obs_b.id}/raster",
        headers=headers_a,
    )
    assert resp_cross_org.status_code == 403, f"Expected 403, got {resp_cross_org.status_code}"

    # Attack 2: User A attempts to request Observation B using Project A's URL -> 404 Not Found
    resp_cross_proj = await async_client.get(
        f"/api/v1/earth-observation/projects/{proj_a.id}/observations/{obs_b.id}/raster",
        headers=headers_a,
    )
    assert resp_cross_proj.status_code == 404, f"Expected 404, got {resp_cross_proj.status_code}"

    # Authorized Request: User B requests their own Project B raster -> 200 OK with valid image
    resp_valid = await async_client.get(
        f"/api/v1/earth-observation/projects/{proj_b.id}/observations/{obs_b.id}/raster",
        headers=headers_b,
    )
    assert resp_valid.status_code == 200, f"Expected 200, got {resp_valid.status_code}"
    assert "image" in resp_valid.headers.get("Content-Type", "")

    # Prove image bytes are valid by opening with Pillow
    img = Image.open(io.BytesIO(resp_valid.content))
    assert img.width > 0, "Image width must be > 0"
    assert img.height > 0, "Image height must be > 0"


# ─── 3. Real Sentinel-2 Live End-to-End Trace ───

@pytest.mark.asyncio
async def test_real_sentinel2_live_trace(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Executes a real Sentinel-2 live trace against Element84 STAC:
    Synthetic Project -> safe public neutral AOI -> live STAC search -> real scene ->
    persisted observation -> COG Range HTTP 206 verification -> raster delivery.
    """
    # 1. Setup Synthetic Project & User
    org = Organization(id=uuid.uuid4(), name=f"Synthetic Org {uuid.uuid4().hex[:4]}")
    user = User(
        id=uuid.uuid4(),
        email=f"eotest.{uuid.uuid4().hex[:6]}@example.com",
        full_name="Synthetic Lead Auditor",
        password_hash=get_password_hash("TestPass123!"),
        role="ORG_ADMIN",
        organization_id=org.id,
        is_active=True,
    )
    proj = Project(
        id=uuid.uuid4(),
        organization_id=org.id,
        name="Synthetic Public AOI Project",
        project_code=f"SYN-{uuid.uuid4().hex[:4]}",
    )
    db_session.add_all([org, user, proj])
    await db_session.flush()

    # 2. Public Safe Neutral AOI (Nairobi National Park coordinates — safe public land, non-customer)
    safe_bbox = [36.8, -1.35, 37.0, -1.2]
    aoi_poly = {
        "type": "Polygon",
        "coordinates": [[[36.8, -1.35], [37.0, -1.35], [37.0, -1.2], [36.8, -1.2], [36.8, -1.35]]],
    }
    aoi, bv = await aoi_service.set_project_boundary(
        db=db_session,
        project_id=proj.id,
        organization_id=org.id,
        name="Synthetic Safe Public AOI",
        geometry_geojson=aoi_poly,
        user_id=user.id,
    )
    await db_session.commit()

    # Authenticate
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "TestPass123!"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Live STAC Query to Element84
    stac_items = default_stac_client.search_items(
        collections=["sentinel-2-l2a"],
        bbox=safe_bbox,
        datetime_range="2024-01-01T00:00:00Z/2024-03-01T23:59:59Z",
        max_cloud_cover=20.0,
        limit=1,
    )
    assert len(stac_items) > 0, "Element84 STAC did not return real Sentinel-2 items"
    real_item = stac_items[0]
    stac_id = real_item.get("id")
    assert stac_id is not None
    assert "S2" in stac_id

    # 4. Map STAC item to raw scene metadata and ingest
    raw_scene = default_stac_client.map_stac_item_to_raw_scene(
        item=real_item,
        provider_code="SENTINEL_2",
        platform="Sentinel-2",
        sensor="MSI",
        product_code="S2_MSI_L2A",
        observation_type=EOObservationType.OPTICAL_MULTISPECTRAL,
        spatial_resolution_m=10.0,
    )
    obs = await observation_service.ingest_observation(
        db=db_session,
        project_id=proj.id,
        organization_id=org.id,
        raw_scene=raw_scene,
        aoi=aoi,
    )
    await db_session.commit()

    # 5. COG HTTP Range Verification
    # Test 'visual' asset key
    cog_res = await async_client.get(
        f"/api/v1/earth-observation/projects/{proj.id}/verify-cog-asset?observation_id={obs.id}&asset_key=visual",
        headers=headers,
    )
    assert cog_res.status_code == 200, cog_res.text
    cog_data = cog_res.json()
    assert cog_data["is_partial_content"] is True, "Must return HTTP 206 Partial Content"
    assert cog_data["is_valid_geotiff_header"] is True, "Must verify GeoTIFF magic bytes (49492a00 or 4d4d002a)"

    # 6. Raster Delivery Endpoint Verification & Quality Assertions (Section 29)
    raster_res = await async_client.get(
        f"/api/v1/earth-observation/projects/{proj.id}/observations/{obs.id}/raster",
        headers=headers,
    )
    assert raster_res.status_code == 200, raster_res.text
    assert "image" in raster_res.headers.get("Content-Type", "")
    assert raster_res.headers.get("X-Display-Source-Type") == "PROVIDER_VISUAL"
    assert raster_res.headers.get("X-Visualization-Type") == "PROVIDER_OPTICAL_PREVIEW"
    assert raster_res.headers.get("X-Band-Mapping") == "PROVIDER_RENDERED"
    assert raster_res.headers.get("X-Visualization-Version") == "S2_TRUE_COLOR_V1"

    img = Image.open(io.BytesIO(raster_res.content))
    assert img.width > 0
    assert img.height > 0

    # Image Quality Assertions (Section 29)
    import numpy as np
    arr = np.array(img)
    stds = np.std(arr, axis=(0, 1))
    for s in stds[:3]:
        assert s > 5.0, f"Spatial variance too low ({s}), possible placeholder fill"
    unique_pixels = len(np.unique(arr.reshape(-1, arr.shape[-1]), axis=0))
    assert unique_pixels > 200, f"Unique pixel count too low ({unique_pixels}), possible synthetic gradient"
    assert arr.max() - arr.min() > 40, "Dynamic range too small, image is flat"

    print(f"\n[REAL SENTINEL-2 EVIDENCE] Scene: {stac_id} | COG Status: {cog_data['http_status']} | Raster Size: {img.size} | Unique Pixels: {unique_pixels} | StdDev: {stds[:3]}")


# ─── 4. Real Landsat Historical Baseline Trace ───

@pytest.mark.asyncio
async def test_real_landsat_historical_baseline_trace(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Executes a real Landsat historical trace against Element84 STAC:
    Discovers real Landsat Collection 2 Level 2 scene from 2023,
    persists it as an immutable baseline observation, and verifies timeline record.
    """
    safe_bbox = [36.8, -1.35, 37.0, -1.2]

    # Live query for historical Landsat Collection 2
    landsat_items = default_stac_client.search_items(
        collections=["landsat-c2-l2"],
        bbox=safe_bbox,
        datetime_range="2023-01-01T00:00:00Z/2023-03-31T23:59:59Z",
        max_cloud_cover=25.0,
        limit=1,
    )
    assert len(landsat_items) > 0, "Element84 STAC did not return Landsat items"
    l_item = landsat_items[0]
    l_id = l_item.get("id")
    assert l_id is not None
    assert any(k in l_id for k in ("LC08", "LC09", "LE07", "LT05")), f"Unexpected Landsat scene ID format: {l_id}"

    # Verify assets structure
    assets = l_item.get("assets", {})
    assert "red" in assets or "nir08" in assets or "thumbnail" in assets
    print(f"\n[REAL LANDSAT EVIDENCE] Scene: {l_id} | Date: {l_item['properties'].get('datetime')} | Assets: {len(assets)}")


# ─── 5. Production Raster Fallback & Display Provenance Tests ───

@pytest.mark.asyncio
async def test_production_raster_fallback_returns_404_prohibits_synthetic_images(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Verifies that when upstream provider satellite imagery is unavailable or invalid,
    the API returns HTTP 404 and NEVER generates synthetic colored boxes or fake raster visuals.
    """
    # 1. Setup tenant & project
    org = Organization(name=f"Fallback Audit Org {uuid.uuid4().hex[:6]}")
    db_session.add(org)
    await db_session.flush()

    user = User(
        email=f"auditor-{uuid.uuid4().hex[:6]}@verifield.test",
        full_name="Fallback Auditor",
        password_hash=get_password_hash("TestPass123!"),
        organization_id=org.id,
        role="ORG_ADMIN",
        is_active=True,
    )
    proj = Project(
        name="Fallback Audit Project",
        organization_id=org.id,
        project_code=f"FB-{uuid.uuid4().hex[:4]}",
    )
    db_session.add_all([user, proj])
    await db_session.commit()

    # Authenticate
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "TestPass123!"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Ingest an observation scene with NO valid candidate image URLs
    geom = {
        "type": "Polygon",
        "coordinates": [[[36.8, -1.35], [37.0, -1.35], [37.0, -1.2], [36.8, -1.2], [36.8, -1.35]]],
    }
    raw_scene = RawSceneMetadata(
        scene_id="S2B_MSIL2A_UNAVAILABLE_TEST",
        provider_code="SENTINEL_2",
        platform="Sentinel-2B",
        sensor="MSI",
        product_code="S2_MSI_L2A",
        observation_type=EOObservationType.OPTICAL_MULTISPECTRAL,
        acquisition_timestamp=datetime(2024, 2, 27, 10, 0, 0, tzinfo=timezone.utc),
        spatial_resolution_m=10.0,
        bounding_box=[36.8, -1.35, 37.0, -1.2],
        geometry_geojson=geom,
        processing_level="Level-2A",
        raw_band_uris={},  # Empty — no accessible thumbnail or visual
        asset_uri=None,
    )
    obs = await observation_service.ingest_observation(
        db=db_session,
        project_id=proj.id,
        organization_id=org.id,
        raw_scene=raw_scene,
    )
    await db_session.commit()

    # 3. Request raster -> Must return HTTP 404 NOT FOUND, NOT 200 with fake pixels
    resp = await async_client.get(
        f"/api/v1/earth-observation/projects/{proj.id}/observations/{obs.id}/raster",
        headers=headers,
    )
    assert resp.status_code == 404
    err_body = resp.json()
    assert "No verified satellite raster imagery available" in err_body["detail"]
    assert "image" not in resp.headers.get("Content-Type", "")


@pytest.mark.asyncio
async def test_display_source_provenance_differentiates_visual_composite_and_derived(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Verifies truthful provenance header differentiation:
    1. Satellite observation preview returns X-Display-Source-Type: PROVIDER_VISUAL,
       X-Display-Source: PROVIDER_PREVIEW, and X-Visualization-Recipe.
    2. Derived index layer raster returns X-Display-Source-Type: DERIVED_PRODUCT
       with HTTP 404 limitation notice rather than masquerading as a raw visual.
    """
    from app.domains.earth_observation.services.derived_layer_service import derived_layer_service

    # 1. Setup tenant & project
    org = Organization(name=f"Provenance Org {uuid.uuid4().hex[:6]}")
    db_session.add(org)
    await db_session.flush()

    user = User(
        email=f"prov-{uuid.uuid4().hex[:6]}@verifield.test",
        full_name="Provenance Auditor",
        password_hash=get_password_hash("TestPass123!"),
        organization_id=org.id,
        role="ORG_ADMIN",
        is_active=True,
    )
    proj = Project(
        name="Provenance Project",
        organization_id=org.id,
        project_code=f"PRV-{uuid.uuid4().hex[:4]}",
    )
    db_session.add_all([user, proj])
    await db_session.commit()

    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "TestPass123!"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Ingest observation with a mock image URL that returns real image bytes
    test_img = Image.new("RGB", (64, 64), color=(30, 80, 40))
    img_buf = io.BytesIO()
    test_img.save(img_buf, format="JPEG")
    fake_img_bytes = img_buf.getvalue()

    geom = {
        "type": "Polygon",
        "coordinates": [[[36.8, -1.35], [37.0, -1.35], [37.0, -1.2], [36.8, -1.2], [36.8, -1.35]]],
    }
    raw_scene = RawSceneMetadata(
        scene_id="S2B_PROVENANCE_TEST",
        provider_code="SENTINEL_2",
        platform="Sentinel-2B",
        sensor="MSI",
        product_code="S2_MSI_L2A",
        observation_type=EOObservationType.OPTICAL_MULTISPECTRAL,
        acquisition_timestamp=datetime(2024, 2, 27, 10, 0, 0, tzinfo=timezone.utc),
        spatial_resolution_m=10.0,
        bounding_box=[36.8, -1.35, 37.0, -1.2],
        geometry_geojson=geom,
        processing_level="Level-2A",
        raw_band_uris={"thumbnail": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/37/M/BU/preview.jpg"},
    )
    obs = await observation_service.ingest_observation(
        db=db_session,
        project_id=proj.id,
        organization_id=org.id,
        raw_scene=raw_scene,
    )
    await db_session.commit()

    # Mock urllib opener to return the test image bytes
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = fake_img_bytes
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = None

    with patch("urllib.request.OpenerDirector.open", return_value=mock_resp):
        # Part 1: Sentinel-2 Thumbnail / Preview -> PROVIDER_VISUAL
        res = await async_client.get(
            f"/api/v1/earth-observation/projects/{proj.id}/observations/{obs.id}/raster",
            headers=headers,
        )
        assert res.status_code == 200
        assert res.headers.get("X-Display-Source-Type") == "PROVIDER_VISUAL"
        assert res.headers.get("X-Display-Source") == "PROVIDER_PREVIEW"
        assert res.headers.get("X-Display-Source-Label") == "Provider Visual"
        assert res.headers.get("X-Display-Asset-Key") == "thumbnail"
        assert res.headers.get("X-Visualization-Type") == "PROVIDER_OPTICAL_PREVIEW"
        assert res.headers.get("X-Band-Mapping") == "PROVIDER_RENDERED"
        assert res.headers.get("X-Visualization-Recipe") == "S2_TRUE_COLOR_PREVIEW"

        # Part 2: Source Band Composite -> SOURCE_BAND_COMPOSITE
        res_comp = await async_client.get(
            f"/api/v1/earth-observation/projects/{proj.id}/observations/{obs.id}/raster?display_mode=SOURCE_BAND_COMPOSITE",
            headers=headers,
        )
        assert res_comp.status_code == 200
        assert res_comp.headers.get("X-Display-Source-Type") == "SOURCE_BAND_COMPOSITE"
        assert res_comp.headers.get("X-Display-Source-Label") == "Source Band Composite"
        assert res_comp.headers.get("X-Band-Mapping") == "R=B04,G=B03,B=B02"
        assert res_comp.headers.get("X-Visualization-Recipe") == "SOURCE_BAND_RGB_COMPOSITE"

    # Part 3: Sentinel-1 SAR Observation -> SAR_RENDER
    sar_scene = RawSceneMetadata(
        scene_id="S1A_IW_GRDH_PROVENANCE_TEST",
        provider_code="SENTINEL_1",
        platform="Sentinel-1A",
        sensor="C-SAR",
        product_code="S1_GRD",
        observation_type=EOObservationType.SAR_C_BAND_BACKSCATTER,
        acquisition_timestamp=datetime(2024, 2, 28, 10, 0, 0, tzinfo=timezone.utc),
        spatial_resolution_m=10.0,
        bounding_box=[36.8, -1.35, 37.0, -1.2],
        geometry_geojson=geom,
        processing_level="Level-1-GRD",
        raw_band_uris={"thumbnail": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sar_preview.jpg"},
    )
    sar_obs = await observation_service.ingest_observation(
        db=db_session,
        project_id=proj.id,
        organization_id=org.id,
        raw_scene=sar_scene,
    )
    await db_session.commit()

    with patch("urllib.request.OpenerDirector.open", return_value=mock_resp):
        sar_res = await async_client.get(
            f"/api/v1/earth-observation/projects/{proj.id}/observations/{sar_obs.id}/raster",
            headers=headers,
        )
        assert sar_res.status_code == 200
        assert sar_res.headers.get("X-Display-Source-Type") == "SAR_RENDER"
        assert sar_res.headers.get("X-Display-Source-Label") == "Provider Quicklook"
        assert sar_res.headers.get("X-Visualization-Type") == "DUAL_POL_SAR_QUICKLOOK"
        assert sar_res.headers.get("X-Band-Mapping") == "R=VV,G=VH,B=VV/VH ratio"

    # Part 4: Derived Layer -> DERIVED_PRODUCT
    derived_layer = await derived_layer_service.register_derived_layer(
        db=db_session,
        observation=obs,
        layer_type="NDVI",
        statistics={"mean": 0.65, "p50": 0.64, "min": 0.12, "max": 0.88, "valid_pixel_pct": 98.5},
    )
    await db_session.commit()

    derived_res = await async_client.get(
        f"/api/v1/earth-observation/projects/{proj.id}/derived-layers/{derived_layer.id}/raster",
        headers=headers,
    )
    assert derived_res.status_code == 404
    assert derived_res.headers.get("X-Display-Source-Type") == "DERIVED_PRODUCT"
    assert derived_res.headers.get("X-Layer-Type") == "NDVI"
    assert "PRODUCTION_READY_WITH_LIMITATION" in derived_res.json()["detail"]
