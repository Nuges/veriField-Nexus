"""
=============================================================================
VeriField Nexus — Copernicus Sentinel-2 Optical Provider
=============================================================================
Sentinel-2 MSI (Multispectral Instrument) 10m / 20m optical provider:
- Bands: B02 (Blue), B03 (Green), B04 (Red), B08 (NIR), B11 (SWIR-1), B12 (SWIR-2)
- Capabilities:
  * Truthful status: INTERFACE_ONLY / NOT_CONFIGURED when API credentials absent.
  * In explicit test mode (test harness): MOCK_TESTED with synthetic test scenes.
  * Never fabricates fake satellite observations in production.
=============================================================================
"""

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.domains.earth_observation.models import (
    EOObservationType,
    EOProviderCapability,
    EOQualityStatus,
)
from app.domains.earth_observation.providers.base import (
    EarthObservationProvider,
    RawSceneMetadata,
)
from app.domains.earth_observation.providers.stac_client import default_stac_client


class Sentinel2Provider(EarthObservationProvider):
    """
    Copernicus Sentinel-2 MSI Optical Provider.
    Supports authoritative live STAC discovery from Element84 Earth Search
    and COG raster asset access.
    """

    PROVIDER_CODE = "SENTINEL_2"
    PLATFORM = "Sentinel-2"
    SENSOR = "MSI"
    PRODUCT_CODE = "S2_MSI_L2A"
    SPATIAL_RESOLUTION_M = 10.0

    def __init__(
        self,
        api_key: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        test_mode: bool = False,
        use_live_stac: Optional[bool] = None,
    ):
        self.api_key = api_key or os.getenv("COPERNICUS_API_KEY")
        self.client_id = client_id or os.getenv("COPERNICUS_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("COPERNICUS_CLIENT_SECRET")
        self._test_mode = test_mode
        if use_live_stac is not None:
            self._use_live_stac = use_live_stac
        else:
            self._use_live_stac = os.getenv("EO_LIVE_STAC_ENABLED", "0") in ("1", "true", "True")
        self._verified_at: Optional[datetime] = None

    def get_provider_code(self) -> str:
        return self.PROVIDER_CODE

    def get_capability_state(self) -> EOProviderCapability:
        if self._test_mode:
            return EOProviderCapability.MOCK_TESTED
        if self._verified_at:
            return EOProviderCapability.LIVE_VERIFIED
        if self._use_live_stac or self.api_key or (self.client_id and self.client_secret):
            return EOProviderCapability.LIVE_CONFIGURED
        return EOProviderCapability.NOT_CONFIGURED

    def search_scenes(
        self,
        bounding_box: List[float],
        date_from: datetime,
        date_to: datetime,
        max_cloud_cover: float = 30.0,
    ) -> List[RawSceneMetadata]:
        """
        Searches for Sentinel-2 L2A scenes via live STAC catalog or deterministic test harness.
        """
        capability = self.get_capability_state()
        if capability == EOProviderCapability.NOT_CONFIGURED:
            return []

        if self._test_mode:
            # Deterministic synthetic test scene for isolated offline test suites
            scene_id = f"S2B_MSIL2A_{date_from.strftime('%Y%m%d')}_SYNTHETIC_TEST"
            cloud_pct = 4.2
            quality = EOQualityStatus.USABLE if cloud_pct <= max_cloud_cover else EOQualityStatus.CLOUD_OBSCURED

            min_lon, min_lat, max_lon, max_lat = bounding_box if len(bounding_box) >= 4 else [0.0, 0.0, 1.0, 1.0]
            geojson = {
                "type": "Polygon",
                "coordinates": [[
                    [min_lon, min_lat],
                    [max_lon, min_lat],
                    [max_lon, max_lat],
                    [min_lon, max_lat],
                    [min_lon, min_lat]
                ]]
            }

            return [
                RawSceneMetadata(
                    scene_id=scene_id,
                    provider_code=self.PROVIDER_CODE,
                    platform=self.PLATFORM,
                    sensor=self.SENSOR,
                    product_code=self.PRODUCT_CODE,
                    observation_type=EOObservationType.OPTICAL_MULTISPECTRAL,
                    acquisition_timestamp=date_from,
                    spatial_resolution_m=self.SPATIAL_RESOLUTION_M,
                    bounding_box=[min_lon, min_lat, max_lon, max_lat],
                    geometry_geojson=geojson,
                    processing_level="L2A",
                    cloud_cover_pct=cloud_pct,
                    raw_band_uris={
                        "B02": f"s3://copernicus-sentinel2/{scene_id}/B02.jp2",
                        "B03": f"s3://copernicus-sentinel2/{scene_id}/B03.jp2",
                        "B04": f"s3://copernicus-sentinel2/{scene_id}/B04.jp2",
                        "B08": f"s3://copernicus-sentinel2/{scene_id}/B08.jp2",
                        "B11": f"s3://copernicus-sentinel2/{scene_id}/B11.jp2",
                    },
                    raw_band_checksums={
                        "B02": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                        "B03": "a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcdef0",
                        "B04": "f1e2d3c4b5a697887766554433221100ffeeddccbbaa99887766554433221100",
                        "B08": "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                        "B11": "fedcba0987654321fedcba0987654321fedcba0987654321fedcba0987654321",
                    },
                    asset_uri=f"s3://copernicus-sentinel2/{scene_id}/manifest.safe",
                    quality_status=quality,
                    quality_flags={"cloud_cover_evaluated": True, "shadow_detected": False},
                    lineage_manifest={
                        "processor": "Sen2Cor",
                        "processor_version": "2.11",
                        "atmospheric_correction": "BOA_SURFACE_REFLECTANCE",
                    },
                )
            ]

        # Live STAC discovery from Element84 public Earth Search
        if self._use_live_stac:
            dt_from_str = date_from.strftime("%Y-%m-%dT%H:%M:%SZ")
            dt_to_str = date_to.strftime("%Y-%m-%dT%H:%M:%SZ")
            dt_range = f"{dt_from_str}/{dt_to_str}"
            items = default_stac_client.search_items(
                collections=["sentinel-2-l2a"],
                bbox=bounding_box if len(bounding_box) >= 4 else None,
                datetime_range=dt_range,
                max_cloud_cover=max_cloud_cover,
                limit=5,
            )
            if items:
                self._verified_at = datetime.now(timezone.utc)
                scenes = []
                for item in items:
                    scene = default_stac_client.map_stac_item_to_raw_scene(
                        item=item,
                        provider_code=self.PROVIDER_CODE,
                        platform=self.PLATFORM,
                        sensor=self.SENSOR,
                        product_code=self.PRODUCT_CODE,
                        observation_type=EOObservationType.OPTICAL_MULTISPECTRAL,
                        spatial_resolution_m=self.SPATIAL_RESOLUTION_M,
                        processing_level="L2A",
                    )
                    scenes.append(scene)
                return scenes

        return []

    def get_scene_metadata(self, scene_id: str) -> Optional[RawSceneMetadata]:
        if self._test_mode:
            now = datetime.now(timezone.utc)
            results = self.search_scenes([0.0, 0.0, 1.0, 1.0], now, now)
            return results[0] if results else None
        return None

    def resolve_asset_urls(self, scene_id: str, band_names: List[str]) -> Dict[str, str]:
        if not self.is_configured():
            return {}
        return {b: f"https://browser.dataspace.copernicus.eu/assets/{scene_id}/{b}.jp2" for b in band_names}
