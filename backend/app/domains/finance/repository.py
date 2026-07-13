from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.finance.models import Transaction


class FinanceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, tx_id: UUID) -> Optional[Transaction]:
        stmt = select(Transaction).where(Transaction.id == tx_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_for_org(
        self, org_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Transaction]:
        stmt = (
            select(Transaction)
            .where(
                (Transaction.from_org_id == org_id) | (Transaction.to_org_id == org_id)
            )
            .order_by(Transaction.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def create(self, tx: Transaction) -> Transaction:
        self.db.add(tx)
        await self.db.commit()
        await self.db.refresh(tx)
        return tx

    async def update_status(self, tx_id: UUID, status: str) -> Optional[Transaction]:
        stmt = (
            update(Transaction)
            .where(Transaction.id == tx_id)
            .values(status=status)
            .returning(Transaction)
        )
        res = await self.db.execute(stmt)
        await self.db.commit()
        return res.scalar_one_or_none()
