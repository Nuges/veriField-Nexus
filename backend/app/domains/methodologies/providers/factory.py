import logging
from .base import MethodologyRegistryProvider
from .generic import GenericMethodologyProvider

logger = logging.getLogger(__name__)

class MethodologyProviderFactory:
    @staticmethod
    def get_provider(methodology_code: str) -> MethodologyRegistryProvider:
        # For CIOS, we dynamically resolve the provider.
        # In a fully fleshed out system, we would map 'GS_TPDDTEC' to a TpddtecProvider, etc.
        logger.info(f"Resolving methodology provider for: {methodology_code}")
        
        # Fallback to Generic
        return GenericMethodologyProvider()
