from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_bus import EventBus
from app.domains.evidence.models import Evidence
from app.domains.evidence.repository import EvidenceRepository
from app.domains.evidence.schemas import EvidenceCreate, EvidenceUpdate


class EvidenceService:
    def __init__(self, repository: EvidenceRepository):
        self.repository = repository

    async def get_evidence(self, evidence_id: UUID) -> Optional[Evidence]:
        return await self.repository.get_by_id(evidence_id)

    async def list_evidence(
        self, activity_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Evidence]:
        return await self.repository.list_by_activity(
            activity_id, skip=skip, limit=limit
        )

    async def upload_evidence(
        self,
        payload: EvidenceCreate,
        uploader_id: UUID,
        db: Optional[AsyncSession] = None,
    ) -> Evidence:
        evidence = Evidence(
            activity_id=payload.activity_id,
            file_uri=payload.file_uri,
            file_hash=payload.file_hash,
            evidence_type=payload.evidence_type,
            metadata_json=payload.metadata_json,
            uploaded_by=uploader_id,
            status="PENDING",
        )
        created = await self.repository.create(evidence)

        if db:
            await EventBus.publish(
                stream_name="evidence_events",
                event_type="EvidenceUploaded",
                payload={
                    "id": str(created.id),
                    "activity_id": str(created.activity_id),
                },
                actor_id=str(uploader_id),
            )

        return created

    async def verify_evidence(
        self,
        evidence_id: UUID,
        payload: EvidenceUpdate,
        verifier_id: UUID,
        db: Optional[AsyncSession] = None,
    ) -> Optional[Evidence]:
        evidence = await self.repository.get_by_id(evidence_id)
        if not evidence:
            return None

        updated = await self.repository.update_status(
            evidence_id, payload.status, verifier_id
        )

        if db and updated:
            await EventBus.publish(
                stream_name="evidence_events",
                event_type="EvidenceVerified",
                payload={"id": str(updated.id), "status": payload.status},
                actor_id=str(verifier_id),
            )

        return updated
