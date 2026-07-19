from .base import JurisdictionBoundaryProvider
from .geojson import GeoJSONBoundaryProvider
import logging

logger = logging.getLogger(__name__)

class JurisdictionProviderFactory:
    @staticmethod
    def get_provider(provider_type: str = "geojson") -> JurisdictionBoundaryProvider:
        if provider_type == "geojson":
            return GeoJSONBoundaryProvider()
            
        logger.warning(f"Jurisdiction provider {provider_type} not found, defaulting to GeoJSON.")
        return GeoJSONBoundaryProvider()
