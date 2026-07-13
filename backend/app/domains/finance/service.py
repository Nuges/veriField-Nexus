from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_bus import EventBus
from app.domains.finance.models import Transaction
from app.domains.finance.repository import FinanceRepository
from app.domains.finance.schemas import TransactionCreate


class FinanceService:
    def __init__(self, repository: FinanceRepository):
        self.repository = repository

    async def get_transaction(self, tx_id: UUID) -> Optional[Transaction]:
        return await self.repository.get_by_id(tx_id)

    async def list_org_transactions(
        self, org_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Transaction]:
        return await self.repository.list_for_org(org_id, skip=skip, limit=limit)

    async def process_transaction(
        self,
        payload: TransactionCreate,
        actor_id: UUID,
        db: Optional[AsyncSession] = None,
    ) -> Transaction:
        tx = Transaction(
            from_org_id=payload.from_org_id,
            to_org_id=payload.to_org_id,
            amount=payload.amount,
            currency=payload.currency,
            project_id=payload.project_id,
            metadata_json=payload.metadata_json,
            status="COMPLETED",
        )
        created = await self.repository.create(tx)

        if db:
            await EventBus.publish(
                stream_name="finance_events",
                event_type="TransactionCompleted",
                payload={"tx_id": str(created.id), "amount": created.amount},
                actor_id=str(actor_id),
            )

        return created
