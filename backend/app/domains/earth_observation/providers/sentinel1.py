"""
=============================================================================
VeriField Nexus — Copernicus Sentinel-1 SAR Provider
=============================================================================
Sentinel-1 C-band Synthetic Aperture Radar (SAR) Provider:
- Products: Ground Range Detected (GRD), Interferometric Wide (IW)
- Polarizations: VV (Vertical transmit/Vertical receive), VH (Vertical transmit/Horizontal receive)

SCIENTIFIC INVARIANT:
- Raw observation is "Sentinel-1 SAR Backscatter" (decibels dB or amplitude).
- SAR backscatter is a physical radar reflectivity metric, NEVER direct "Soil Moisture".
- A soil moisture estimate may exist ONLY if a ground-calibrated model is configured
  with explicit predictors, validation metrics, and uncertainty.
- Without an active calibrated model: SOIL_MOISTURE_MODEL is NOT_CONFIGURED.
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


class Sentinel1Provider(EarthObservationProvider):
    """
    Copernicus Sentinel-1 C-Band Synthetic Aperture Radar (SAR) Provider.
    Supports authoritative live STAC discovery from Element84 Earth Search.
    """

    PROVIDER_CODE = "SENTINEL_1"
    PLATFORM = "Sentinel-1"
    SENSOR = "C-SAR"
    PRODUCT_CODE = "S1_SAR_GRD"
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

    def get_granular_capabilities(self) -> Dict[str, str]:
        base = super().get_granular_capabilities()
        # Invariant: SAR C-band soil moisture model is NOT_CONFIGURED without calibrated in-situ sensors
        base["derived_processing"] = "NOT_CONFIGURED (Calibrated in-situ ground sensors required)"
        return base

    def search_scenes(
        self,
        bounding_box: List[float],
        date_from: datetime,
        date_to: datetime,
        max_cloud_cover: float = 100.0,  # Radar penetrates clouds
    ) -> List[RawSceneMetadata]:
        capability = self.get_capability_state()
        if capability == EOProviderCapability.NOT_CONFIGURED:
            return []

        if self._test_mode:
            scene_id = f"S1A_IW_GRDH_1SDV_{date_from.strftime('%Y%m%d')}_SYNTHETIC_TEST"
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
                    observation_type=EOObservationType.SAR_C_BAND_BACKSCATTER,
                    acquisition_timestamp=date_from,
                    spatial_resolution_m=self.SPATIAL_RESOLUTION_M,
                    bounding_box=[min_lon, min_lat, max_lon, max_lat],
                    geometry_geojson=geojson,
                    processing_level="GRD",
                    cloud_cover_pct=None,  # Not applicable to SAR microwave
                    raw_band_uris={
                        "VV": f"s3://copernicus-sentinel1/{scene_id}/measurement/s1a-iw-grd-vv.tiff",
                        "VH": f"s3://copernicus-sentinel1/{scene_id}/measurement/s1a-iw-grd-vh.tiff",
                    },
                    raw_band_checksums={
                        "VV": "11223344556677889900aabbccddeeff11223344556677889900aabbccddeeff",
                        "VH": "ffeeddccbbaa99887766554433221100ffeeddccbbaa99887766554433221100",
                    },
                    asset_uri=f"s3://copernicus-sentinel1/{scene_id}/manifest.safe",
                    quality_status=EOQualityStatus.USABLE,
                    quality_flags={
                        "polarization": "VV_VH",
                        "orbit_direction": "DESCENDING",
                        "radiometric_calibration": "GAMMA0",
                        "speckle_filter": "LEE_REFINED",
                        "soil_moisture_model": "NOT_CONFIGURED",
                    },
                    lineage_manifest={
                        "sensor": "C-SAR",
                        "mode": "IW",
                        "polarization": ["VV", "VH"],
                        "processing_algorithm": "ESA_SNAP_ThermalNoiseRemoval_Calibrate_TerrainCorrection",
                    },
                )
            ]

        # Live STAC discovery from Element84 public Earth Search
        if self._use_live_stac:
            dt_from_str = date_from.strftime("%Y-%m-%dT%H:%M:%SZ")
            dt_to_str = date_to.strftime("%Y-%m-%dT%H:%M:%SZ")
            dt_range = f"{dt_from_str}/{dt_to_str}"
            items = default_stac_client.search_items(
                collections=["sentinel-1-grd"],
                bbox=bounding_box if len(bounding_box) >= 4 else None,
                datetime_range=dt_range,
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
                        observation_type=EOObservationType.SAR_C_BAND_BACKSCATTER,
                        spatial_resolution_m=self.SPATIAL_RESOLUTION_M,
                        processing_level="GRD",
                    )
                    scene.quality_flags["soil_moisture_model"] = "NOT_CONFIGURED"
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
        return {b: f"https://browser.dataspace.copernicus.eu/assets/s1/{scene_id}/{b}.tiff" for b in band_names}
