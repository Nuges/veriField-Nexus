from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_bus import EventBus
from app.domains.verification.models import AuditReport, VerificationTask
from app.domains.verification.repository import VerificationRepository
from app.domains.verification.schemas import (AuditReportCreate,
                                              VerificationTaskCreate)


class VerificationService:
    def __init__(self, repository: VerificationRepository):
        self.repository = repository

    async def get_task(self, task_id: UUID) -> Optional[VerificationTask]:
        return await self.repository.get_task_by_id(task_id)

    async def create_verification_task(
        self,
        payload: VerificationTaskCreate,
        actor_id: UUID,
        db: Optional[AsyncSession] = None,
    ) -> VerificationTask:
        task = VerificationTask(
            project_id=payload.project_id,
            verifier_id=payload.verifier_id,
            status="ASSIGNED",
            findings={},
        )
        created = await self.repository.create_task(task)

        if db:
            await EventBus.publish(
                stream_name="verification_events",
                event_type="TaskAssigned",
                payload={
                    "task_id": str(created.id),
                    "project_id": str(created.project_id),
                },
                actor_id=str(actor_id),
            )

        return created

    async def submit_audit_report(
        self,
        payload: AuditReportCreate,
        actor_id: UUID,
        db: Optional[AsyncSession] = None,
    ) -> AuditReport:
        report = AuditReport(
            project_id=payload.project_id,
            vvb_org_id=payload.vvb_org_id,
            report_uri=payload.report_uri,
            report_hash=payload.report_hash,
            is_positive_opinion=payload.is_positive_opinion,
        )
        created = await self.repository.create_audit_report(report)

        if db:
            await EventBus.publish(
                stream_name="verification_events",
                event_type="AuditReportSubmitted",
                payload={
                    "report_id": str(created.id),
                    "project_id": str(created.project_id),
                    "is_positive": created.is_positive_opinion,
                },
                actor_id=str(actor_id),
            )

        return created
