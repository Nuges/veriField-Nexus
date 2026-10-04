"""
=============================================================================
VeriField Nexus — USGS / NASA Landsat 8/9 Historical Provider
=============================================================================
Landsat 8/9 OLI / TIRS 30m provider:
- Provides historical temporal baseline observations (2013–present).
- Spatial resolution: 30m multispectral (Bands 1–7) & 100m thermal (TIRS).
- Truthful runtime capability: reports NOT_CONFIGURED when USGS / AWS credentials absent.
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


class LandsatProvider(EarthObservationProvider):
    """
    USGS / NASA Landsat 8/9 Provider for historical baseline context.
    Supports authoritative live STAC discovery from Element84 Earth Search.
    """

    PROVIDER_CODE = "LANDSAT_8_9"
    PLATFORM = "Landsat-8/9"
    SENSOR = "OLI-TIRS"
    PRODUCT_CODE = "LANDSAT_C2_L2"
    SPATIAL_RESOLUTION_M = 30.0

    def __init__(
        self,
        api_key: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        test_mode: bool = False,
        use_live_stac: Optional[bool] = None,
    ):
        self.api_key = api_key or os.getenv("USGS_EROS_API_KEY")
        self.username = username or os.getenv("USGS_EROS_USERNAME")
        self.password = password or os.getenv("USGS_EROS_PASSWORD")
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
        if self._use_live_stac or self.api_key or (self.username and self.password):
            return EOProviderCapability.LIVE_CONFIGURED
        return EOProviderCapability.NOT_CONFIGURED

    def search_scenes(
        self,
        bounding_box: List[float],
        date_from: datetime,
        date_to: datetime,
        max_cloud_cover: float = 30.0,
    ) -> List[RawSceneMetadata]:
        capability = self.get_capability_state()
        if capability == EOProviderCapability.NOT_CONFIGURED:
            return []

        if self._test_mode:
            scene_id = f"LC09_L2SP_146040_{date_from.strftime('%Y%m%d')}_02_T1_SYNTHETIC"
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
                    processing_level="L2SP",
                    cloud_cover_pct=5.1,
                    raw_band_uris={
                        "SR_B2": f"s3://usgs-landsat/{scene_id}_SR_B2.TIF",
                        "SR_B3": f"s3://usgs-landsat/{scene_id}_SR_B3.TIF",
                        "SR_B4": f"s3://usgs-landsat/{scene_id}_SR_B4.TIF",
                        "SR_B5": f"s3://usgs-landsat/{scene_id}_SR_B5.TIF",
                        "ST_B10": f"s3://usgs-landsat/{scene_id}_ST_B10.TIF",
                    },
                    raw_band_checksums={
                        "SR_B2": "aaaabbbbccccdddd1111222233334444555566667777888899990000aaaabbbb",
                        "SR_B3": "bbbbccccdddd1111222233334444555566667777888899990000aaaabbbbcccc",
                        "SR_B4": "ccccdddd1111222233334444555566667777888899990000aaaabbbbccccdddd",
                        "SR_B5": "dddd1111222233334444555566667777888899990000aaaabbbbccccdddd1111",
                        "ST_B10": "1111222233334444555566667777888899990000aaaabbbbccccdddd11112222",
                    },
                    asset_uri=f"s3://usgs-landsat/{scene_id}_MTL.xml",
                    quality_status=EOQualityStatus.USABLE,
                    quality_flags={"cloud_cover_pct": 5.1, "tier": "Tier 1"},
                    lineage_manifest={
                        "collection": "Collection 2",
                        "tier": "T1",
                        "correction": "Surface Reflectance LaSRC",
                    },
                )
            ]

        # Live STAC discovery from Element84 public Earth Search
        if self._use_live_stac:
            dt_from_str = date_from.strftime("%Y-%m-%dT%H:%M:%SZ")
            dt_to_str = date_to.strftime("%Y-%m-%dT%H:%M:%SZ")
            dt_range = f"{dt_from_str}/{dt_to_str}"
            items = default_stac_client.search_items(
                collections=["landsat-c2-l2"],
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
                        processing_level="L2SP",
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
        return {b: f"https://landsatlook.usgs.gov/data/{scene_id}_{b}.TIF" for b in band_names}
