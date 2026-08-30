from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from .base import RegistryProvider
from .local import LocalRegistryProvider
from .verra import VerraProvider
from .gold_standard import GoldStandardProvider
from .national_registry import NationalRegistryProvider
from .article6 import Article6Provider
from .car import CARProvider
from .puro import PuroProvider
from .isometric import IsometricProvider


def get_registry_provider(provider_name: str, db: Optional[AsyncSession] = None) -> RegistryProvider:
    providers = {
        "local": LocalRegistryProvider,
        "verra": VerraProvider,
        "gold_standard": GoldStandardProvider,
        "national_registry": NationalRegistryProvider,
        "article6": Article6Provider,
        "car": CARProvider,
        "puro": PuroProvider,
        "isometric": IsometricProvider,
    }
    provider_class = providers.get(provider_name.lower())
    if not provider_class:
        raise ValueError(f"Unknown registry provider: {provider_name}")
    if provider_class is LocalRegistryProvider:
        return provider_class(db=db)
    return provider_class()


class RegistryProviderFactory:
    @staticmethod
    def get_provider(provider_name: str, db: Optional[AsyncSession] = None) -> RegistryProvider:
        return get_registry_provider(provider_name, db=db)

