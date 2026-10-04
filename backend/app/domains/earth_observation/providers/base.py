"""
=============================================================================
VeriField Nexus — Shared Earth Observation Provider Interface
=============================================================================
Defines abstract base classes, types, and truthful capability states for satellite providers:
- Capability states:
  * LIVE_VERIFIED: Real provider request has succeeded and provenance persisted.
  * LIVE_CONFIGURED: Valid endpoint and credentials present, not yet executed.
  * MOCK_TESTED: Explicit test harness / synthetic mode (isolated tests only).
  * INTERFACE_ONLY: Code adapter exists, but runtime credentials are absent.
  * NOT_CONFIGURED: Missing API keys / disabled in environment.
  * DISABLED: Administratively deactivated.
  * ERROR: Provider error / service unreachable.

- INVARIANT: A provider returns raw observations and asset references.
  Derived indices (NDVI, EVI, NDWI) are calculated by the Processing Service,
  not duplicated inside individual provider adapters.
=============================================================================
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from app.domains.earth_observation.models import (
    EOObservationType,
    EOProviderCapability,
    EOQualityStatus,
)


@dataclass
class RawSceneMetadata:
    """
    Standardized raw scene metadata returned from satellite discovery.
    """
    scene_id: str
    provider_code: str
    platform: str
    sensor: str
    product_code: str
    observation_type: EOObservationType
    acquisition_timestamp: datetime
    spatial_resolution_m: float
    bounding_box: List[float]  # [min_lon, min_lat, max_lon, max_lat]
    geometry_geojson: Dict[str, Any]
    processing_level: str
    cloud_cover_pct: Optional[float] = None
    raw_band_uris: Dict[str, str] = field(default_factory=dict)
    raw_band_checksums: Dict[str, str] = field(default_factory=dict)
    asset_uri: Optional[str] = None
    quality_status: EOQualityStatus = EOQualityStatus.USABLE
    quality_flags: Dict[str, Any] = field(default_factory=dict)
    lineage_manifest: Dict[str, Any] = field(default_factory=dict)


class EarthObservationProvider(ABC):
    """
    Abstract Base Class for satellite data providers.
    """

    @abstractmethod
    def get_provider_code(self) -> str:
        """Returns unique code identifier (e.g. 'SENTINEL_2', 'SENTINEL_1', 'LANDSAT_8_9')."""
        pass

    @abstractmethod
    def get_capability_state(self) -> EOProviderCapability:
        """Returns truthful runtime capability state."""
        pass

    def is_configured(self) -> bool:
        """Returns True only if provider is configured with credentials."""
        state = self.get_capability_state()
        return state in (EOProviderCapability.LIVE_CONFIGURED, EOProviderCapability.LIVE_VERIFIED, EOProviderCapability.MOCK_TESTED)

    @abstractmethod
    def search_scenes(
        self,
        bounding_box: List[float],
        date_from: datetime,
        date_to: datetime,
        max_cloud_cover: float = 30.0,
    ) -> List[RawSceneMetadata]:
        """
        Queries scenes covering the bounding box within the temporal window.
        Returns empty list if provider is NOT_CONFIGURED or INTERFACE_ONLY.
        """
        pass

    @abstractmethod
    def get_scene_metadata(self, scene_id: str) -> Optional[RawSceneMetadata]:
        """Fetches detailed metadata for a specific scene ID."""
        pass

    @abstractmethod
    def resolve_asset_urls(self, scene_id: str, band_names: List[str]) -> Dict[str, str]:
        """Resolves accessible download or streaming URLs for requested spectral bands."""
        pass

    def get_granular_capabilities(self) -> Dict[str, str]:
        """
        Returns granular capability states across the remote sensing lifecycle:
        discovery, metadata_retrieval, persistence, asset_access, raster_rendering, derived_processing.
        """
        overall = self.get_capability_state()
        if overall in (EOProviderCapability.NOT_CONFIGURED, EOProviderCapability.DISABLED):
            return {
                "discovery": EOProviderCapability.NOT_CONFIGURED.value,
                "metadata_retrieval": EOProviderCapability.NOT_CONFIGURED.value,
                "persistence": EOProviderCapability.NOT_CONFIGURED.value,
                "asset_access": EOProviderCapability.NOT_CONFIGURED.value,
                "raster_rendering": EOProviderCapability.NOT_CONFIGURED.value,
                "derived_processing": EOProviderCapability.NOT_CONFIGURED.value,
            }
        if overall == EOProviderCapability.MOCK_TESTED:
            return {
                "discovery": EOProviderCapability.MOCK_TESTED.value,
                "metadata_retrieval": EOProviderCapability.MOCK_TESTED.value,
                "persistence": EOProviderCapability.MOCK_TESTED.value,
                "asset_access": EOProviderCapability.MOCK_TESTED.value,
                "raster_rendering": EOProviderCapability.MOCK_TESTED.value,
                "derived_processing": EOProviderCapability.MOCK_TESTED.value,
            }
        return {
            "discovery": overall.value,
            "metadata_retrieval": overall.value,
            "persistence": EOProviderCapability.LIVE_VERIFIED.value,
            "asset_access": overall.value,
            "raster_rendering": EOProviderCapability.LIVE_CONFIGURED.value,
            "derived_processing": EOProviderCapability.LIVE_VERIFIED.value,
        }
