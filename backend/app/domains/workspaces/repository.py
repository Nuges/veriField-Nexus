from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.workspaces.models import Property


class PropertyRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(
        self, prop_id: UUID, organization_id: Optional[UUID] = None
    ) -> Optional[Property]:
        stmt = select(Property).where(Property.id == prop_id)
        if organization_id:
            stmt = stmt.where(Property.organization_id == organization_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_by_organization(self, organization_id: UUID) -> List[Property]:
        stmt = select(Property).where(Property.organization_id == organization_id)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def list_properties_paginated(
        self,
        organization_id: Optional[UUID],
        page: int = 1,
        per_page: int = 100,
        user_role: Optional[str] = None,
    ) -> tuple[List[Property], int]:
        from sqlalchemy import func

        stmt = select(Property)
        count_stmt = select(func.count(Property.id))

        conditions = []
        if user_role != "SUPER_ADMIN":
            if organization_id:
                conditions.append(Property.organization_id == organization_id)
            else:
                conditions.append(Property.organization_id is None)

        if conditions:
            from sqlalchemy import and_

            stmt = stmt.where(and_(*conditions))
            count_stmt = count_stmt.where(and_(*conditions))

        # Count total
        count_res = await self.db.execute(count_stmt)
        total = count_res.scalar() or 0

        # Paginate and sort
        offset = (page - 1) * per_page
        stmt = stmt.order_by(Property.created_at.desc()).offset(offset).limit(per_page)

        res = await self.db.execute(stmt)
        items = list(res.scalars().all())

        return items, total

    async def create(self, prop: Property) -> Property:
        self.db.add(prop)
        await self.db.commit()
        await self.db.refresh(prop)
        return prop

    async def update(self, prop: Property) -> Property:
        await self.db.commit()
        await self.db.refresh(prop)
        return prop

    async def delete(self, prop: Property) -> None:
        await self.db.delete(prop)
        await self.db.commit()
