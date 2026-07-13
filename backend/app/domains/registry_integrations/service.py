import logging
from typing import Any, Dict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import RegistryConfig, RegistrySyncLog

logger = logging.getLogger(__name__)


class BaseRegistryAdapter:
    async def register_project(
        self, project_id: UUID, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        return {"status": "unsupported_in_base_class"}

    async def issue_credits(
        self, project_id: UUID, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        return {"status": "unsupported_in_base_class"}

    async def retire_credits(
        self, project_id: UUID, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        return {"status": "unsupported_in_base_class"}


import httpx


class VerraAdapter(BaseRegistryAdapter):
    def __init__(self, api_key: str = "mock_key"):
        self.api_key = api_key
        self.base_url = "https://api.verra.org/v1"

    async def register_project(
        self, project_id: UUID, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/projects",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            response.raise_for_status()
            return response.json()

    async def issue_credits(
        self, project_id: UUID, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/projects/{project_id}/issue",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            response.raise_for_status()
            return response.json()

    async def retire_credits(
        self, project_id: UUID, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/retirements",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            response.raise_for_status()
            return response.json()


class GoldStandardAdapter(BaseRegistryAdapter):
    def __init__(self, api_key: str = "mock_key"):
        self.api_key = api_key
        self.base_url = "https://api.goldstandard.org/v1"

    async def register_project(
        self, project_id: UUID, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/projects",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            response.raise_for_status()
            return response.json()

    async def issue_credits(
        self, project_id: UUID, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/projects/{project_id}/issue",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            response.raise_for_status()
            return response.json()

    async def retire_credits(
        self, project_id: UUID, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/retirements",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            response.raise_for_status()
            return response.json()


class RegistryFederationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.adapters = {
            "verra": VerraAdapter(),
            "gold_standard": GoldStandardAdapter(),
        }

    async def sync_action(
        self,
        registry_id: UUID,
        project_id: UUID,
        action: str,
        payload: Dict[str, Any],
        idempotency_key: str,
    ) -> RegistrySyncLog:
        # 1. Check idempotency
        stmt = select(RegistrySyncLog).where(
            RegistrySyncLog.idempotency_key == idempotency_key
        )
        existing = (await self.db.execute(stmt)).scalars().first()
        if existing:
            return existing

        # 2. Get registry config
        config = await self.db.get(RegistryConfig, registry_id)
        if not config:
            raise ValueError(f"Registry config {registry_id} not found")

        adapter = self.adapters.get(config.adapter_type)
        if not adapter:
            raise ValueError(f"Adapter {config.adapter_type} not implemented")

        # 3. Create Sync Log (Pending)
        log = RegistrySyncLog(
            registry_id=registry_id,
            project_id=project_id,
            action=action,
            status="pending",
            idempotency_key=idempotency_key,
            request_payload=payload,
        )
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)

        # 4. Execute Adapter
        try:
            if action == "registerProject":
                result = await adapter.register_project(project_id, payload)
            elif action == "issueCredits":
                result = await adapter.issue_credits(project_id, payload)
            elif action == "retireCredits":
                result = await adapter.retire_credits(project_id, payload)
            else:
                raise ValueError(f"Unknown action {action}")

            log.status = "success"
            log.response_payload = result

        except Exception as e:
            log.status = "failed"
            log.error_message = str(e)

        await self.db.commit()
        await self.db.refresh(log)
        return log
