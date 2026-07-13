import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.projects.models import Project
from app.domains.registry_integrations.models import (RegistryConfig,
                                                      RegistrySyncLog)

logger = logging.getLogger(__name__)


class UniversalRegistryMapper:
    """
    Universal Registry Abstraction Engine.
    Maps VeriField Projects, Activities, and Issuances into standard API payloads
    (Verra, Gold Standard, Puro, etc.) purely based on metadata mapping rules.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def sync_project_to_registry(
        self, project_id: uuid.UUID, registry_id: uuid.UUID
    ) -> RegistrySyncLog:

        # 1. Fetch Project & Registry
        project = await self.db.get(Project, project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        registry = await self.db.get(RegistryConfig, registry_id)
        if not registry:
            raise ValueError(f"Registry {registry_id} not found")

        # 2. Extract Mapping Rules
        rules = registry.mapping_rules_json.get("project_registration", {})
        if not rules:
            raise ValueError(
                f"No project_registration rules defined for registry {registry.name}"
            )

        # 3. Apply Mapping Rules to generate payload
        payload = {}
        for target_key, source_path in rules.items():
            # Simplistic JSONPath evaluator
            value = self._extract_value(project, source_path)
            payload[target_key] = value

        # 4. Generate Idempotency Key
        idempotency_key = f"registerProject-{project.id}-{registry.id}"

        # 5. Log Sync Request
        sync_log = RegistrySyncLog(
            registry_id=registry.id,
            project_id=project.id,
            action="registerProject",
            status="pending",
            idempotency_key=idempotency_key,
            request_payload=payload,
        )
        self.db.add(sync_log)
        await self.db.commit()

        # In a real scenario, this would dispatch an async task to HTTP POST the payload
        # and update the sync_log.status on callback.

        return sync_log

    def _extract_value(self, obj: Any, path: str) -> Any:
        """
        Extracts a value from an object using a dot-notation path (e.g., 'attributes.capacity').
        """
        parts = path.split(".")
        current = obj
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                return None
        return current
