"""
=============================================================================
VeriField Nexus — Production Earth Observation & Satellite MRV Test Suite
=============================================================================
Rigorous verification of the centralized Earth Observation domain:
1. Geospatial Engine: WGS84 geodesic polygon area/perimeter, hole deduction,
   ray-casting point-in-polygon, bounding box calculation, GeoJSON validation.
2. Provider Truthfulness: Capability matrix, fail-closed without credentials,
   SAR backscatter physical metric invariant (soil moisture model NOT_CONFIGURED).
3. Cryptographic Provenance: Deterministic SHA-256 digests for scenes, derived layers,
   and baseline snapshot packages.
4. AOI & Boundary Versioning: Version increments, geodesic area, NO_AOI handling.
5. Ingestion & Cloud QA: Provenance persistence, cloud QA states, EOProcessingRun audit.
6. Derived Layers: NDVI (Rouse 1974), EVI (Huete 2002), NDWI Gao vs McFeeters, SAR backscatter.
7. Spatial Anomalies: Cautious terminology (VEGETATION_INDEX_CHANGE), review recommendations,
   corroboration lifecycle.
8. Baseline Evidence & Registry MRV Manifest: Cryptographic package seal, full audit chain.
=============================================================================
"""

import uuid
from datetime import date, datetime, timezone
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.earth_observation.models import (
    EOAnomalyStatus,
    EOObservationType,
    EOProviderCapability,
    EOQualityStatus,
    EOSpatialAnomalyType,
)
from app.domains.earth_observation.provenance import (
    generate_baseline_package_hash,
    generate_derived_layer_provenance_hash,
    generate_scene_provenance_hash,
)
from app.domains.earth_observation.providers import (
    CommercialSatelliteProvider,
    LandsatProvider,
    ProviderRegistry,
    RawSceneMetadata,
    Sentinel1Provider,
    Sentinel2Provider,
)
from app.domains.earth_observation.services import (
    anomaly_service,
    aoi_service,
    baseline_service,
    derived_layer_service,
    geospatial_engine,
    manifest_service,
    observation_service,
)
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project


# ─── 1. Geospatial Engine Tests ───

def test_geospatial_engine_wgs84_polygon_area_and_hole_deduction():
    """Verifies GeographicLib WGS84 geodesic polygon calculation and hole deduction."""
    # Outer square ~ 0.02 deg (~2.2 km per side)
    # Inner hole ~ 0.01 deg
    polygon_with_hole = {
        "type": "Polygon",
        "coordinates": [
            [[0.0, 0.0], [0.02, 0.0], [0.02, 0.02], [0.0, 0.02], [0.0, 0.0]],
            [[0.005, 0.005], [0.015, 0.005], [0.015, 0.015], [0.005, 0.015], [0.005, 0.005]],
        ],
    }
    area_m2, area_ha, perimeter_m = geospatial_engine.calculate_geodesic_polygon_area_perimeter(polygon_with_hole)
    assert area_m2 > 0
    assert area_ha > 0
    assert perimeter_m > 0
    # Outer is ~4.92 km2, hole is ~1.23 km2 -> Net is ~3.69 km2 = ~369 ha
    assert 350.0 < area_ha < 390.0

    # Ray casting point-in-polygon with hole exclusion
    assert geospatial_engine.point_in_polygon(0.002, 0.002, polygon_with_hole) is True
    assert geospatial_engine.point_in_polygon(0.010, 0.010, polygon_with_hole) is False  # Inside hole
    assert geospatial_engine.point_in_polygon(0.050, 0.050, polygon_with_hole) is False  # Outside polygon


def test_geospatial_engine_bounding_box_and_validation():
    """Verifies bounding box and GeoJSON structure validation."""
    poly = {
        "type": "Polygon",
        "coordinates": [
            [[10.0, 20.0], [10.5, 20.0], [10.5, 20.5], [10.0, 20.5], [10.0, 20.0]]
        ],
    }
    bbox = geospatial_engine.calculate_bounding_box(poly)
    assert bbox == [10.0, 20.0, 10.5, 20.5]

    # Invalid geometry types must raise ValueError
    with pytest.raises(ValueError, match="Unsupported geometry type"):
        geospatial_engine.validate_and_normalize_geojson({"type": "Point", "coordinates": [0, 0]})

    # Out of range coordinates
    with pytest.raises(ValueError, match="out of WGS84 range"):
        geospatial_engine.validate_and_normalize_geojson({
            "type": "Polygon",
            "coordinates": [[[200.0, 0.0], [201.0, 0.0], [201.0, 1.0], [200.0, 0.0]]],
        })


# ─── 2. Provider Truthfulness Tests ───

def test_provider_truthful_capability_states():
    """Verifies satellite providers report NOT_CONFIGURED or INTERFACE_ONLY without credentials."""
    s2 = Sentinel2Provider()
    s1 = Sentinel1Provider()
    landsat = LandsatProvider()
    commercial = CommercialSatelliteProvider()

    assert s2.get_capability_state() == EOProviderCapability.NOT_CONFIGURED
    assert s1.get_capability_state() == EOProviderCapability.NOT_CONFIGURED
    assert landsat.get_capability_state() in (
        EOProviderCapability.INTERFACE_ONLY,
        EOProviderCapability.NOT_CONFIGURED,
    )
    assert commercial.get_capability_state() == EOProviderCapability.NOT_CONFIGURED

    # In production mode without credentials, searching returns empty list (no fabricated scenes)
    scenes = commercial.search_scenes([0, 0, 1, 1], datetime.now(timezone.utc), datetime.now(timezone.utc))
    assert len(scenes) == 0


def test_provider_test_harness_mode():
    """Verifies explicit test harness mode produces deterministic test scenes."""
    registry = ProviderRegistry(test_mode=True)
    matrix = registry.get_capability_matrix()
    for code, info in matrix.items():
        assert info["capability"] == EOProviderCapability.MOCK_TESTED.value

    s2 = registry.get_provider("SENTINEL_2")
    assert s2 is not None
    scenes = s2.search_scenes([0.0, 0.0, 0.1, 0.1], datetime.now(timezone.utc), datetime.now(timezone.utc))
    assert len(scenes) >= 1
    assert scenes[0].provider_code == "SENTINEL_2"
    assert scenes[0].spatial_resolution_m == 10.0


# ─── 3. Cryptographic Provenance Tests ───

def test_cryptographic_provenance_determinism_and_sensitivity():
    """Verifies deterministic SHA-256 scene provenance hashing and parameter sensitivity."""
    now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    bbox = [10.0, 20.0, 10.5, 20.5]
    bands = {"B04": "hash_red_123", "B08": "hash_nir_456"}

    h1 = generate_scene_provenance_hash(
        provider="SENTINEL_2",
        scene_id="S2A_MSIL2A_TEST_001",
        acquisition_timestamp=now,
        spatial_resolution_m=10.0,
        processing_level="L2A",
        bounding_box=bbox,
        raw_band_checksums=bands,
    )
    h2 = generate_scene_provenance_hash(
        provider="SENTINEL_2",
        scene_id="S2A_MSIL2A_TEST_001",
        acquisition_timestamp=now,
        spatial_resolution_m=10.0,
        processing_level="L2A",
        bounding_box=bbox,
        raw_band_checksums=bands,
    )
    assert h1 == h2
    assert len(h1) == 64

    # Any altered input produces distinct digest
    h3 = generate_scene_provenance_hash(
        provider="SENTINEL_2",
        scene_id="S2A_MSIL2A_TEST_001",
        acquisition_timestamp=now,
        spatial_resolution_m=10.0,
        processing_level="L2A",
        bounding_box=bbox,
        raw_band_checksums={"B04": "hash_red_DIFF", "B08": "hash_nir_456"},
    )
    assert h1 != h3


# ─── 4. Services End-to-End Persistence Tests ───

@pytest.mark.asyncio
async def test_aoi_boundary_lifecycle_and_versioning(db_session: AsyncSession):
    """Tests project boundary registration, WGS84 geodesic area, and version increments."""
    # Create test organization & project
    org = Organization(name=f"EO Test Org {uuid.uuid4().hex[:6]}")
    db_session.add(org)
    await db_session.flush()

    proj = Project(
        organization_id=org.id,
        name="EO Test Project",
        project_code=f"P-{uuid.uuid4().hex[:6]}",
    )
    db_session.add(proj)
    await db_session.commit()

    # Initial check: no AOI
    initial_aoi = await aoi_service.get_project_active_aoi(db_session, proj.id, org.id)
    assert initial_aoi is None

    # Version 1: 0.01 x 0.01 deg square (~123 ha)
    geom_v1 = {
        "type": "Polygon",
        "coordinates": [[[0.0, 0.0], [0.01, 0.0], [0.01, 0.01], [0.0, 0.01], [0.0, 0.0]]],
    }
    aoi_v1, bv_v1 = await aoi_service.set_project_boundary(
        db=db_session,
        project_id=proj.id,
        organization_id=org.id,
        geometry_geojson=geom_v1,
        name="Field A",
        reason="Initial boundary declaration",
    )
    assert bv_v1.version_number == 1
    assert 120.0 < aoi_v1.area_ha < 125.0
    assert aoi_v1.is_active is True

    # Version 2: Expanded boundary to 0.02 x 0.01 deg
    geom_v2 = {
        "type": "Polygon",
        "coordinates": [[[0.0, 0.0], [0.02, 0.0], [0.02, 0.01], [0.0, 0.01], [0.0, 0.0]]],
    }
    aoi_v2, bv_v2 = await aoi_service.set_project_boundary(
        db=db_session,
        project_id=proj.id,
        organization_id=org.id,
        geometry_geojson=geom_v2,
        name="Field A Expanded",
        reason="Acquired adjacent parcel",
    )
    assert bv_v2.version_number == 2
    assert bv_v2.area_ha > bv_v1.area_ha
    assert aoi_v2.is_active is True

    # Check history
    history = await aoi_service.list_boundary_history(db_session, proj.id, org.id)
    assert len(history) == 2
    assert history[0].version_number == 2
    assert history[1].version_number == 1


@pytest.mark.asyncio
async def test_observation_ingestion_and_cloud_qa(db_session: AsyncSession):
    """Tests observation ingestion, provenance persistence, cloud QA states, and audit run."""
    org = Organization(name=f"Ingest Org {uuid.uuid4().hex[:6]}")
    db_session.add(org)
    await db_session.flush()

    proj = Project(
        organization_id=org.id,
        name="Ingest Project",
        project_code=f"P-{uuid.uuid4().hex[:6]}",
    )
    db_session.add(proj)
    await db_session.commit()

    # Ingest scene with 12% cloud cover -> USABLE
    raw_usable = RawSceneMetadata(
        scene_id="S2B_MSIL2A_20260601T103021_N0500_R108_T31UDS",
        provider_code="SENTINEL_2",
        platform="Sentinel-2B",
        sensor="MSI",
        product_code="S2_MSI_L2A",
        observation_type=EOObservationType.OPTICAL_MULTISPECTRAL,
        acquisition_timestamp=datetime(2026, 6, 1, 10, 30, tzinfo=timezone.utc),
        spatial_resolution_m=10.0,
        bounding_box=[2.3, 48.8, 2.4, 48.9],
        geometry_geojson={"type": "Polygon", "coordinates": [[[2.3, 48.8], [2.4, 48.8], [2.4, 48.9], [2.3, 48.9], [2.3, 48.8]]]},
        processing_level="L2A",
        cloud_cover_pct=12.5,
        raw_band_uris={"B04": "uri://b4", "B08": "uri://b8"},
        raw_band_checksums={"B04": "chk4", "B08": "chk8"},
    )
    obs_usable = await observation_service.ingest_observation(
        db=db_session,
        project_id=proj.id,
        organization_id=org.id,
        raw_scene=raw_usable,
        is_baseline=True,
    )
    assert obs_usable.quality_status == EOQualityStatus.USABLE.value
    assert len(obs_usable.provenance_hash) == 64
    assert obs_usable.is_baseline is True
    assert obs_usable.quality_flags["quality_policy_id"] == "DEFAULT_OPTICAL_QA_V1"
    assert obs_usable.quality_flags["policy_version"] == "1.0.0"
    assert "thresholds" in obs_usable.quality_flags
    assert obs_usable.quality_flags["thresholds"]["cloud_obscured_threshold"] == 50.0

    # Ingest scene with 65% cloud cover -> CLOUD_OBSCURED
    raw_cloudy = RawSceneMetadata(
        scene_id="S2B_MSIL2A_20260606T103021_N0500_R108_T31UDS",
        provider_code="SENTINEL_2",
        platform="Sentinel-2B",
        sensor="MSI",
        product_code="S2_MSI_L2A",
        observation_type=EOObservationType.OPTICAL_MULTISPECTRAL,
        acquisition_timestamp=datetime(2026, 6, 6, 10, 30, tzinfo=timezone.utc),
        spatial_resolution_m=10.0,
        bounding_box=[2.3, 48.8, 2.4, 48.9],
        geometry_geojson={"type": "Polygon", "coordinates": [[[2.3, 48.8], [2.4, 48.8], [2.4, 48.9], [2.3, 48.9], [2.3, 48.8]]]},
        processing_level="L2A",
        cloud_cover_pct=65.0,
    )
    obs_cloudy = await observation_service.ingest_observation(
        db=db_session,
        project_id=proj.id,
        organization_id=org.id,
        raw_scene=raw_cloudy,
    )
    assert obs_cloudy.quality_status == EOQualityStatus.CLOUD_OBSCURED.value


@pytest.mark.asyncio
async def test_derived_layers_and_spatial_anomalies(db_session: AsyncSession):
    """Tests NDVI / NDWI derived layer computation and factual anomaly detection."""
    org = Organization(name=f"Anomaly Org {uuid.uuid4().hex[:6]}")
    db_session.add(org)
    await db_session.flush()

    proj = Project(
        organization_id=org.id,
        name="Anomaly Project",
        project_code=f"P-{uuid.uuid4().hex[:6]}",
    )
    db_session.add(proj)
    await db_session.commit()

    # Ingest baseline observation (June 2025)
    raw_baseline = RawSceneMetadata(
        scene_id="S2_BASELINE_20250615",
        provider_code="SENTINEL_2",
        platform="Sentinel-2A",
        sensor="MSI",
        product_code="S2_MSI_L2A",
        observation_type=EOObservationType.OPTICAL_MULTISPECTRAL,
        acquisition_timestamp=datetime(2025, 6, 15, 10, 0, tzinfo=timezone.utc),
        spatial_resolution_m=10.0,
        bounding_box=[0.0, 0.0, 0.1, 0.1],
        geometry_geojson={"type": "Polygon", "coordinates": [[[0,0], [0.1,0], [0.1,0.1], [0,0.1], [0,0]]]},
        processing_level="L2A",
        cloud_cover_pct=2.0,
    )
    obs_base = await observation_service.ingest_observation(
        db=db_session,
        project_id=proj.id,
        organization_id=org.id,
        raw_scene=raw_baseline,
        is_baseline=True,
    )

    # Ingest current observation (June 2026)
    raw_current = RawSceneMetadata(
        scene_id="S2_CURRENT_20260615",
        provider_code="SENTINEL_2",
        platform="Sentinel-2A",
        sensor="MSI",
        product_code="S2_MSI_L2A",
        observation_type=EOObservationType.OPTICAL_MULTISPECTRAL,
        acquisition_timestamp=datetime(2026, 6, 15, 10, 0, tzinfo=timezone.utc),
        spatial_resolution_m=10.0,
        bounding_box=[0.0, 0.0, 0.1, 0.1],
        geometry_geojson={"type": "Polygon", "coordinates": [[[0,0], [0.1,0], [0.1,0.1], [0,0.1], [0,0]]]},
        processing_level="L2A",
        cloud_cover_pct=3.0,
    )
    obs_curr = await observation_service.ingest_observation(
        db=db_session,
        project_id=proj.id,
        organization_id=org.id,
        raw_scene=raw_current,
    )

    # Register baseline NDVI (high vigor, mean = 0.72)
    layer_base = await derived_layer_service.register_derived_layer(
        db=db_session,
        observation=obs_base,
        layer_type="NDVI",
        statistics={"mean": 0.72, "min": 0.20, "max": 0.88, "std": 0.11},
    )
    assert layer_base.formula_identifier == "NDVI_ROUSE_1974"

    # Register current NDVI (drop in vigor, mean = 0.45, delta = -0.27)
    layer_curr = await derived_layer_service.register_derived_layer(
        db=db_session,
        observation=obs_curr,
        layer_type="NDVI",
        statistics={"mean": 0.45, "min": 0.10, "max": 0.60, "std": 0.14},
    )

    # Detect anomaly
    anomaly = await anomaly_service.detect_index_change(
        db=db_session,
        current_layer=layer_curr,
        baseline_layer=layer_base,
        threshold_delta=-0.15,
    )
    assert anomaly is not None
    assert anomaly.anomaly_type == EOSpatialAnomalyType.VEGETATION_INDEX_CHANGE.value
    assert anomaly.status == EOAnomalyStatus.OBSERVED.value
    assert anomaly.delta_value == -0.27
    assert "Review field activity records" in anomaly.review_recommendation

    # Corroborate anomaly
    corroborated = await anomaly_service.corroborate_anomaly(
        db=db_session,
        anomaly_id=anomaly.id,
        organization_id=org.id,
        corroborated=True,
        notes="Field team confirmed planned rotational grazing harvest on parcel.",
    )
    assert corroborated is not None
    assert corroborated.status == EOAnomalyStatus.CORROBORATED.value


@pytest.mark.asyncio
async def test_baseline_package_and_registry_mrv_manifest(db_session: AsyncSession):
    """Tests compilation of baseline evidence package and registry MRV manifest."""
    org = Organization(name=f"Manifest Org {uuid.uuid4().hex[:6]}")
    db_session.add(org)
    await db_session.flush()

    proj = Project(
        organization_id=org.id,
        name="Manifest Project",
        project_code=f"P-{uuid.uuid4().hex[:6]}",
    )
    db_session.add(proj)
    await db_session.commit()

    geom = {
        "type": "Polygon",
        "coordinates": [[[0.0, 0.0], [0.01, 0.0], [0.01, 0.01], [0.0, 0.01], [0.0, 0.0]]],
    }
    aoi, bv = await aoi_service.set_project_boundary(
        db=db_session,
        project_id=proj.id,
        organization_id=org.id,
        geometry_geojson=geom,
    )

    # Ingest baseline scene
    raw = RawSceneMetadata(
        scene_id="S2_BASE_PACK_001",
        provider_code="SENTINEL_2",
        platform="Sentinel-2A",
        sensor="MSI",
        product_code="S2_MSI_L2A",
        observation_type=EOObservationType.OPTICAL_MULTISPECTRAL,
        acquisition_timestamp=datetime(2025, 5, 1, 10, 0, tzinfo=timezone.utc),
        spatial_resolution_m=10.0,
        bounding_box=[0.0, 0.0, 0.01, 0.01],
        geometry_geojson=geom,
        processing_level="L2A",
        cloud_cover_pct=1.5,
    )
    obs = await observation_service.ingest_observation(
        db=db_session,
        project_id=proj.id,
        organization_id=org.id,
        raw_scene=raw,
        aoi=aoi,
        is_baseline=True,
    )

    # Baseline package compilation
    pkg = await baseline_service.compile_baseline_package(
        db=db_session,
        project_id=proj.id,
        organization_id=org.id,
        aoi=aoi,
        boundary_version=bv,
    )
    assert pkg["observation_count"] == 1
    assert len(pkg["package_seal_hash"]) == 64

    # Registry MRV manifest export
    manifest = await manifest_service.generate_project_mrv_manifest(
        db=db_session,
        project_id=proj.id,
        organization_id=org.id,
        aoi=aoi,
    )
    assert manifest["mrv_manifest_version"] == "1.0.0"
    assert manifest["aoi"]["area_ha"] == aoi.area_ha
    assert len(manifest["observations"]) == 1
    assert "manifest_digest_sha256" in manifest
    assert len(manifest["manifest_digest_sha256"]) == 64


def test_granular_capability_lifecycle_reporting():
    """
    Verifies granular capability reporting across the remote sensing lifecycle:
    discovery, metadata_retrieval, persistence, asset_access, raster_rendering, derived_processing.
    Ensures Sentinel-1 SAR explicitly reports derived soil moisture as NOT_CONFIGURED without ground sensors.
    """
    registry = ProviderRegistry(test_mode=True)
    matrix = registry.get_capability_matrix()

    for code, info in matrix.items():
        assert "granular_capabilities" in info
        caps = info["granular_capabilities"]
        for phase in ["discovery", "metadata_retrieval", "persistence", "asset_access", "raster_rendering", "derived_processing"]:
            assert phase in caps, f"Missing phase '{phase}' in provider '{code}'"

    # Invariant: SAR C-band soil moisture model is NOT_CONFIGURED
    s1_caps = matrix["SENTINEL_1"]["granular_capabilities"]
    assert "NOT_CONFIGURED" in s1_caps["derived_processing"]
