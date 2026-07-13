from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.organizations.models import Organization


class OrganizationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(
        self, org_id: UUID, include_deleted: bool = False
    ) -> Optional[Organization]:
        stmt = select(Organization).where(Organization.id == org_id)
        if not include_deleted:
            stmt = stmt.where(Organization.is_deleted == False)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[Organization]:
        stmt = select(Organization).where(
            Organization.name == name, Organization.is_deleted == False
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_all(self, skip: int = 0, limit: int = 100) -> List[Organization]:
        stmt = (
            select(Organization)
            .where(Organization.is_deleted == False)
            .offset(skip)
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def create(self, org: Organization) -> Organization:
        self.db.add(org)
        await self.db.commit()
        await self.db.refresh(org)
        return org

    async def update(
        self, org_id: UUID, updates: Dict[str, Any], current_version: int
    ) -> Optional[Organization]:
        stmt = (
            update(Organization)
            .where(Organization.id == org_id)
            .where(Organization.version == current_version)
            .where(Organization.is_deleted == False)
            .values(**updates, version=Organization.version + 1)
            .returning(Organization)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalar_one_or_none()

    async def soft_delete(self, org_id: UUID) -> bool:
        stmt = (
            update(Organization)
            .where(Organization.id == org_id)
            .where(Organization.is_deleted == False)
            .values(
                is_deleted=True,
                deleted_at=datetime.now(timezone.utc),
                status="ARCHIVED",
                version=Organization.version + 1,
            )
            .returning(Organization.id)
        )
        res = await self.db.execute(stmt)
        await self.db.commit()
        return res.scalar_one_or_none() is not None
