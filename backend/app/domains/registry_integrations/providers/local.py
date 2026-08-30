import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.domains.registry_integrations.models import RegistrySyncLog
from .base import RegistryProvider

logger = logging.getLogger(__name__)

class LocalRegistryProvider(RegistryProvider):
    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db

    async def authenticate(self) -> bool:
        return True

    async def validate_project(self, project_id: UUID) -> Dict[str, Any]:
        return {"valid": True, "details": "Local validation passed."}

    async def submit_bundle(self, project_id: UUID, payload: Dict[str, Any], idempotency_key: str) -> Dict[str, Any]:
        # Simulates submission and transitions to 'Queued'
        return {
            "status": "Queued",
            "message": "Bundle submitted to local registry queue",
            "idempotency_key": idempotency_key,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    async def check_status(self, sync_id: UUID) -> Dict[str, Any]:
        # Simulates checking status and progressing through the state machine
        # Queued -> Validating -> Submitted -> Accepted -> Issued
        log = await self.db.get(RegistrySyncLog, sync_id)
        if not log:
            return {"status": "Not Found"}
            
        current_status = log.status
        next_status = current_status
        
        if current_status == "Queued":
            next_status = "Validating"
        elif current_status == "Validating":
            next_status = "Submitted"
        elif current_status == "Submitted":
            next_status = "Accepted"
        elif current_status == "Accepted":
            next_status = "Issued"
            
        if next_status != current_status:
            log.status = next_status
            await self.db.commit()
            
        return {"status": next_status, "sync_id": str(sync_id)}

    async def retrieve_issuance(self, project_id: UUID) -> Dict[str, Any]:
        if self.db:
            from app.domains.assets.models import Asset
            from app.domains.activities.models import Activity
            a_stmt = select(Asset.id).where(Asset.project_id == project_id)
            a_res = await self.db.execute(a_stmt)
            asset_ids = a_res.scalars().all()
            if asset_ids:
                act_stmt = select(Activity).where(Activity.asset_id.in_(asset_ids))
                act_res = await self.db.execute(act_stmt)
                acts = act_res.scalars().all()
                total_kg = 0.0
                for a in acts:
                    data = a.activity_data or {}
                    if isinstance(data, dict):
                        if "emission_reduction_kg" in data:
                            total_kg += float(data["emission_reduction_kg"])
                        elif "carbon_offset_tons" in data:
                            total_kg += float(data["carbon_offset_tons"]) * 1000.0
                return {"issued_credits": round(total_kg / 1000.0, 4), "project_id": str(project_id)}
        return {"issued_credits": 0.0, "project_id": str(project_id)}

    async def download_receipt(self, sync_id: UUID) -> bytes:
        return b"Receipt content (Local Registry)"
