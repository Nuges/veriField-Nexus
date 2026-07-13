from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.authentication.models import User


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(
        self, user_id: UUID, organization_id: Optional[UUID] = None
    ) -> Optional[User]:
        stmt = select(User).where(User.id == user_id, User.is_deleted == False)
        if organization_id:
            stmt = stmt.where(User.organization_id == organization_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email, User.is_deleted == False)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_phone(self, phone: str) -> Optional[User]:
        stmt = select(User).where(User.phone == phone, User.is_deleted == False)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_by_organization(
        self, organization_id: UUID, limit: int = 100, offset: int = 0
    ) -> List[User]:
        stmt = (
            select(User)
            .where(User.organization_id == organization_id, User.is_deleted == False)
            .limit(limit)
            .offset(offset)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def create(self, user: User) -> User:
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update(self, user: User) -> User:
        """
        Optimistic concurrency control:
        Handled by SQLAlchemy's version_id_col mapper arg.
        """
        from sqlalchemy.orm.exc import StaleDataError

        try:
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
            return user
        except StaleDataError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Update failed: the record was modified by another transaction.",
            )

    async def soft_delete(self, user: User) -> User:
        user.is_deleted = True
        user.deleted_at = datetime.now(timezone.utc)
        user.status = "deleted"
        user.is_active = False
        return await self.update(user)
