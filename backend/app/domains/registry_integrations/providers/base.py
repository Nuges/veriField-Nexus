from abc import ABC, abstractmethod
from typing import Any, Dict
from uuid import UUID

class RegistryProvider(ABC):
    @abstractmethod
    async def authenticate(self) -> bool:
        pass

    @abstractmethod
    async def validate_project(self, project_id: UUID) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def submit_bundle(self, project_id: UUID, payload: Dict[str, Any], idempotency_key: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def check_status(self, sync_id: UUID) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def retrieve_issuance(self, project_id: UUID) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def download_receipt(self, sync_id: UUID) -> bytes:
        pass
