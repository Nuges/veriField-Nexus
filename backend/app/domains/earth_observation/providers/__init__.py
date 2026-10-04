"""
=============================================================================
VeriField Nexus — Earth Observation Providers Package
=============================================================================
"""

from app.domains.earth_observation.providers.base import (
    EarthObservationProvider,
    RawSceneMetadata,
)
from app.domains.earth_observation.providers.commercial import CommercialSatelliteProvider
from app.domains.earth_observation.providers.landsat import LandsatProvider
from app.domains.earth_observation.providers.registry import (
    ProviderRegistry,
    default_registry,
    get_default_provider_registry,
)
from app.domains.earth_observation.providers.sentinel1 import Sentinel1Provider
from app.domains.earth_observation.providers.sentinel2 import Sentinel2Provider

__all__ = [
    "EarthObservationProvider",
    "RawSceneMetadata",
    "Sentinel2Provider",
    "Sentinel1Provider",
    "LandsatProvider",
    "CommercialSatelliteProvider",
    "ProviderRegistry",
    "default_registry",
    "get_default_provider_registry",
]
