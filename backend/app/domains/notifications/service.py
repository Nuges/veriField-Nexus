from typing import List, Optional
from uuid import UUID

from app.domains.notifications.models import Notification
from app.domains.notifications.repository import NotificationRepository
from app.domains.notifications.schemas import NotificationCreate


class NotificationService:
    def __init__(self, repository: NotificationRepository):
        self.repository = repository

    async def get_notification(self, notification_id: UUID) -> Optional[Notification]:
        return await self.repository.get_by_id(notification_id)

    async def get_user_notifications(
        self, user_id: UUID, skip: int = 0, limit: int = 100, unread_only: bool = False
    ) -> List[Notification]:
        return await self.repository.list_for_user(
            user_id, skip=skip, limit=limit, unread_only=unread_only
        )

    async def create_notification(self, payload: NotificationCreate) -> Notification:
        notification = Notification(
            user_id=payload.user_id,
            title=payload.title,
            message=payload.message,
            type=payload.type,
            metadata_json=payload.metadata_json,
        )
        return await self.repository.create(notification)

    async def mark_read(self, notification_id: UUID) -> Optional[Notification]:
        return await self.repository.mark_as_read(notification_id)

    async def mark_all_read(self, user_id: UUID) -> bool:
        return await self.repository.mark_all_as_read(user_id)
