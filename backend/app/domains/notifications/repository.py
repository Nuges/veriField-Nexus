from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.notifications.models import Notification


class NotificationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, notification_id: UUID) -> Optional[Notification]:
        stmt = select(Notification).where(Notification.id == notification_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_for_user(
        self, user_id: UUID, skip: int = 0, limit: int = 100, unread_only: bool = False
    ) -> List[Notification]:
        stmt = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            stmt = stmt.where(not Notification.is_read)
        stmt = stmt.order_by(Notification.created_at.desc()).offset(skip).limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def create(self, notification: Notification) -> Notification:
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)
        return notification

    async def mark_as_read(self, notification_id: UUID) -> Optional[Notification]:
        stmt = (
            update(Notification)
            .where(Notification.id == notification_id)
            .values(is_read=True)
            .returning(Notification)
        )
        res = await self.db.execute(stmt)
        await self.db.commit()
        return res.scalar_one_or_none()

    async def mark_all_as_read(self, user_id: UUID) -> bool:
        stmt = (
            update(Notification)
            .where(Notification.user_id == user_id)
            .where(not Notification.is_read)
            .values(is_read=True)
        )
        await self.db.execute(stmt)
        await self.db.commit()
        return True
