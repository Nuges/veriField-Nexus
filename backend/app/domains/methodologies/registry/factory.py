import logging
from typing import Dict, Type

from app.domains.methodologies.calculators.base import (
    BaseMethodologyCalculator, DynamicMetadataCalculator)

logger = logging.getLogger("verifield.methodology.factory")


class MethodologyFactory:
    """
    Factory Pattern for dynamically loading methodology calculators and validators.
    Defaults to the DynamicMetadataCalculator unless a custom strategy is registered.
    """

    def __init__(self):
        self._calculators: Dict[str, Type[BaseMethodologyCalculator]] = {}
        # Default fallback
        self._default_calculator = DynamicMetadataCalculator()

    def register_calculator(
        self, version_id: str, calculator_class: Type[BaseMethodologyCalculator]
    ) -> None:
        """
        Register a custom calculator for a specific methodology version.
        Only used for highly complex methodologies that cannot be handled via DB metadata.
        """
        self._calculators[str(version_id)] = calculator_class
        logger.info(
            f"Registered custom calculator for methodology version: {version_id}"
        )

    def get_calculator(self, version_id: str) -> BaseMethodologyCalculator:
        """
        Resolves the calculator for a given methodology version.
        Falls back to DynamicMetadataCalculator if no custom class is registered.
        """
        calc_class = self._calculators.get(str(version_id))
        if calc_class:
            return calc_class()
        return self._default_calculator


# Global Singleton
methodology_factory = MethodologyFactory()
