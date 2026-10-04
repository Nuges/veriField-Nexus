"""
=============================================================================
VeriField Nexus — Earth Observation Provider Registry
=============================================================================
Central registry and lifecycle manager for all satellite data providers:
- Sentinel-2 (Copernicus Optical)
- Sentinel-1 (Copernicus SAR Backscatter)
- Landsat 8/9 (USGS/NASA Optical Historical)
- Commercial Satellite Provider (PlanetScope / SkySat)

Ensures that:
1. Truthful capability states are dynamically interrogated.
2. In production without credentials, providers report NOT_CONFIGURED or INTERFACE_ONLY.
3. Test harness mode (test_mode=True) can be injected cleanly for end-to-end integration tests.
=============================================================================
"""

import logging
from typing import Any, Dict, List, Optional, Type

from app.domains.earth_observation.models import EOProviderCapability
from app.domains.earth_observation.providers.base import EarthObservationProvider
from app.domains.earth_observation.providers.commercial import CommercialSatelliteProvider
from app.domains.earth_observation.providers.landsat import LandsatProvider
from app.domains.earth_observation.providers.sentinel1 import Sentinel1Provider
from app.domains.earth_observation.providers.sentinel2 import Sentinel2Provider

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """
    Registry for discovering and obtaining satellite observation providers.
    """

    def __init__(self, test_mode: bool = False):
        self._test_mode = test_mode
        self._providers: Dict[str, EarthObservationProvider] = {}
        self._initialize_default_providers()

    def _initialize_default_providers(self) -> None:
        """Instantiates default provider adapters."""
        s2 = Sentinel2Provider(test_mode=self._test_mode)
        s1 = Sentinel1Provider(test_mode=self._test_mode)
        landsat = LandsatProvider(test_mode=self._test_mode)
        commercial = CommercialSatelliteProvider(test_mode=self._test_mode)

        self.register_provider(s2)
        self.register_provider(s1)
        self.register_provider(landsat)
        self.register_provider(commercial)

    def register_provider(self, provider: EarthObservationProvider) -> None:
        """Registers a provider instance."""
        code = provider.get_provider_code()
        self._providers[code] = provider
        logger.info(
            "Registered EO Provider: %s (Capability: %s)",
            code,
            provider.get_capability_state().value,
        )

    def get_provider(self, provider_code: str) -> Optional[EarthObservationProvider]:
        """Returns provider by code, or None if not found."""
        return self._providers.get(provider_code)

    def list_providers(self) -> List[EarthObservationProvider]:
        """Returns list of all registered providers."""
        return list(self._providers.values())

    def get_capability_matrix(self) -> Dict[str, Dict[str, Any]]:
        """
        Returns runtime capability state and granular lifecycle states for every registered provider.
        """
        matrix: Dict[str, Dict[str, Any]] = {}
        for code, prov in self._providers.items():
            state = prov.get_capability_state()
            granular = prov.get_granular_capabilities() if hasattr(prov, "get_granular_capabilities") else {}
            matrix[code] = {
                "provider_code": code,
                "capability": state.value,
                "is_configured": "true" if prov.is_configured() else "false",
                "granular_capabilities": granular,
            }
        return matrix


# Global default registry instance
default_registry = ProviderRegistry(test_mode=False)


def get_default_provider_registry(test_mode: bool = False) -> ProviderRegistry:
    """Returns provider registry (optionally initialized in test mode)."""
    if test_mode:
        return ProviderRegistry(test_mode=True)
    return default_registry
