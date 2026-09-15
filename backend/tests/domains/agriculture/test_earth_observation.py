"""
=============================================================================
VeriField Nexus — Earth Observation (EO) Architecture & Provenance Tests
=============================================================================
Tests:
1. Open Sentinel-2 provider (10m multispectral NDVI, EVI, NDMI, SAVI, BSI).
2. Sentinel-1 SAR C-band backscatter:
   - Invariant: Labeled as 'SAR observation', 'backscatter feature', or
     'soil-moisture proxy'. NEVER labeled raw 'Soil Moisture'.
3. Landsat 8/9 provider (30m archive).
4. Commercial provider feature-flag gating (PlanetScope 3m, SkySat 50cm):
   - When disabled or missing keys, fail-closed without hallucinating scenes.
5. Cryptographic SHA-256 scene provenance generation:
   - Identical parameters yield identical digest.
   - Any parameter change yields different digest.
=============================================================================
"""

from datetime import datetime, timezone
import pytest

from app.domains.agriculture.earth_observation import (
    EOProviderType,
    LandsatProvider,
    ObservationType,
    PlanetScopeProvider,
    Sentinel1Provider,
    Sentinel2Provider,
    SkySatProvider,
    generate_scene_provenance_hash,
)


def test_sentinel2_optical_indices():
    provider = Sentinel2Provider()
    bbox = [77.1, 28.5, 77.2, 28.6]
    now = datetime.now(timezone.utc)

    scenes = provider.search_scenes(bbox, now, now)
    assert len(scenes) == 1
    scene = scenes[0]

    assert scene.provider == EOProviderType.SENTINEL_2
    assert scene.observation_type == ObservationType.OPTICAL_MULTISPECTRAL
    assert scene.spatial_resolution_m == 10.0
    assert "ndvi_mean" in scene.derived_indices
    assert "evi_mean" in scene.derived_indices
    assert "ndmi_mean" in scene.derived_indices
    assert "savi_mean" in scene.derived_indices
    assert "bsi_mean" in scene.derived_indices
    assert len(scene.provenance_hash) == 64


def test_sentinel1_sar_backscatter_and_proxy_labeling():
    provider = Sentinel1Provider()
    bbox = [77.1, 28.5, 77.2, 28.6]
    now = datetime.now(timezone.utc)

    scenes = provider.search_scenes(bbox, now, now)
    assert len(scenes) == 1
    scene = scenes[0]

    assert scene.provider == EOProviderType.SENTINEL_1
    assert scene.observation_type == ObservationType.SAR_C_BAND_BACKSCATTER

    # Invariant: SAR is proxy / backscatter, NEVER unlabeled direct "Soil Moisture"
    indices = scene.derived_indices
    assert "soil_moisture_proxy" in indices
    assert "soil_moisture" not in indices
    assert "sar_vv_backscatter_db" in indices
    assert "sar_vh_backscatter_db" in indices
    assert "sar_vh_vv_cross_ratio" in indices


def test_landsat_provider_30m_archive():
    provider = LandsatProvider()
    bbox = [77.1, 28.5, 77.2, 28.6]
    now = datetime.now(timezone.utc)

    scenes = provider.search_scenes(bbox, now, now)
    assert len(scenes) == 1
    scene = scenes[0]
    assert scene.provider == EOProviderType.LANDSAT_8_9
    assert scene.spatial_resolution_m == 30.0


def test_commercial_providers_feature_flag_gated():
    planet = PlanetScopeProvider()
    assert planet.is_configured() is False
    assert len(planet.search_scenes([77.1, 28.5, 77.2, 28.6], datetime.now(timezone.utc), datetime.now(timezone.utc))) == 0

    skysat = SkySatProvider()
    assert skysat.is_configured() is False
    assert len(skysat.search_scenes([77.1, 28.5, 77.2, 28.6], datetime.now(timezone.utc), datetime.now(timezone.utc))) == 0


def test_scene_provenance_hash_reproducibility():
    ts = datetime(2026, 6, 15, 10, 30, 0, tzinfo=timezone.utc)
    bbox = [77.1, 28.5, 77.2, 28.6]
    indices = {"ndvi_mean": 0.65, "evi_mean": 0.42}

    h1 = generate_scene_provenance_hash(
        provider="SENTINEL_2",
        scene_id="S2B_MSIL2A_TEST",
        acquisition_timestamp=ts,
        spatial_resolution_m=10.0,
        processing_level="L2A",
        bounding_box=bbox,
        indices_summary=indices,
    )
    h2 = generate_scene_provenance_hash(
        provider="SENTINEL_2",
        scene_id="S2B_MSIL2A_TEST",
        acquisition_timestamp=ts,
        spatial_resolution_m=10.0,
        processing_level="L2A",
        bounding_box=bbox,
        indices_summary=indices,
    )
    assert h1 == h2
    assert len(h1) == 64

    # Different NDVI produces different digest
    h3 = generate_scene_provenance_hash(
        provider="SENTINEL_2",
        scene_id="S2B_MSIL2A_TEST",
        acquisition_timestamp=ts,
        spatial_resolution_m=10.0,
        processing_level="L2A",
        bounding_box=bbox,
        indices_summary={"ndvi_mean": 0.66, "evi_mean": 0.42},
    )
    assert h1 != h3
