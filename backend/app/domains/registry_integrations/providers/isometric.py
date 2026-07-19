from typing import Any, Dict
from uuid import UUID
from app.core.config import settings
from .base import RegistryProvider

class IsometricProvider(RegistryProvider):
    def __init__(self):
        if not getattr(settings, "ENABLE_VERIFIED_REGISTRY_SYNC".lower(), False):
            raise NotImplementedError("IsometricProvider is disabled by feature flag ENABLE_VERIFIED_REGISTRY_SYNC.")
        
    async def authenticate(self) -> bool:
        raise NotImplementedError("Real integration pending.")

    async def validate_project(self, project_id: UUID) -> Dict[str, Any]:
        raise NotImplementedError("Real integration pending.")

    async def submit_bundle(self, project_id: UUID, payload: Dict[str, Any], idempotency_key: str) -> Dict[str, Any]:
        raise NotImplementedError("Real integration pending.")

    async def check_status(self, sync_id: UUID) -> Dict[str, Any]:
        raise NotImplementedError("Real integration pending.")

    async def retrieve_issuance(self, project_id: UUID) -> Dict[str, Any]:
        raise NotImplementedError("Real integration pending.")

    async def download_receipt(self, sync_id: UUID) -> bytes:
        raise NotImplementedError("Real integration pending.")
