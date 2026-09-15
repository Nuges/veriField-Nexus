"""
=============================================================================
VeriField Nexus — Earth Observation (EO) Provider Abstraction
=============================================================================
Defines abstract base classes, common types, and invariants for satellite feeds:
- Invariant 1: Satellite index != Carbon.
  Spectral indices (NDVI, EVI, NDMI) indicate photosynthetic activity or canopy
  water, NOT carbon stocks or carbon credits.
- Invariant 2: SAR is a proxy or backscatter feature, never direct "Soil Moisture"
  without a calibrated ground-coupled model.
- Invariant 3: Lineage provenance is cryptographically verifiable via SHA-256.
=============================================================================
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class EOProviderType(str, Enum):
    SENTINEL_2 = "SENTINEL_2"
    SENTINEL_1 = "SENTINEL_1"
    LANDSAT_8_9 = "LANDSAT_8_9"
    PLANET_SCOPE = "PLANET_SCOPE"
    SKYSAT = "SKYSAT"


class ObservationType(str, Enum):
    OPTICAL_MULTISPECTRAL = "OPTICAL_MULTISPECTRAL"
    SAR_C_BAND_BACKSCATTER = "SAR_C_BAND_BACKSCATTER"
    THERMAL_INFRARED = "THERMAL_INFRARED"
    HIGH_RES_OPTICAL = "HIGH_RES_OPTICAL"


@dataclass
class SceneMetadata:
    scene_id: str
    provider: EOProviderType
    observation_type: ObservationType
    acquisition_timestamp: datetime
    cloud_coverage_pct: Optional[float]
    spatial_resolution_m: float
    processing_level: str
    bounding_box: List[float]  # [min_lon, min_lat, max_lon, max_lat]
    provenance_hash: str
    raw_band_uris: Dict[str, str] = field(default_factory=dict)
    derived_indices: Dict[str, float] = field(default_factory=dict)
    lineage_manifest: Dict[str, Any] = field(default_factory=dict)


class EarthObservationProvider(ABC):
    """
    Abstract Base Class for Earth Observation data providers.
    """

    @abstractmethod
    def get_provider_type(self) -> EOProviderType:
        """Returns provider enum type."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Returns True if provider credentials / API endpoints are configured."""
        pass

    @abstractmethod
    def search_scenes(
        self,
        bounding_box: List[float],
        date_from: datetime,
        date_to: datetime,
        max_cloud_cover: float = 30.0,
    ) -> List[SceneMetadata]:
        """
        Searches available satellite scenes covering the target bounding box.
        """
        pass

    @abstractmethod
    def compute_indices_for_polygon(
        self,
        scene_id: str,
        polygon_geojson: Dict[str, Any],
    ) -> Dict[str, float]:
        """
        Extracts/computes spectral indices or backscatter features over a polygon.
        """
        pass
