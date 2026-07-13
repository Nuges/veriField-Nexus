import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, Column, DateTime, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.event_bus import EventBus
from app.db.base import Base


class OutboxEvent(Base):
    """
    Transactional Outbox entity for CQRS readiness.
    Events are committed to this table in the same transaction as the domain state.
    A background relay worker subsequently reads and publishes these to the Event Bus.
    """

    __tablename__ = "outbox_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type = Column(String, nullable=False, index=True)
    stream_name = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    actor_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    published = Column(Boolean, default=False, index=True)
    published_at = Column(DateTime, nullable=True)


class EventOutboxManager:
    """
    Manager for the Transactional Outbox pattern.
    Guarantees atomic writes of domain state and events.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def stage_event(
        self, stream_name: str, event_type: str, payload: dict, actor_id: str = "system"
    ) -> OutboxEvent:
        """
        Stages an event to be published by writing it to the Outbox table.
        This MUST be called within an active database transaction alongside domain updates.
        """
        outbox_event = OutboxEvent(
            id=str(uuid.uuid4()),
            event_type=event_type,
            stream_name=stream_name,
            payload=payload,
            actor_id=actor_id,
            published=False,
        )
        self.db.add(outbox_event)
        # We do NOT commit here. The caller commits the transaction.
        return outbox_event

    async def relay_unpublished_events(self, limit: int = 100):
        """
        Intended to be called by a background CRON or worker.
        Reads unpublished events, pushes them to Redis via EventBus, and marks them published.
        """
        result = await self.db.execute(
            select(OutboxEvent)
            .where(not OutboxEvent.published)
            .order_by(OutboxEvent.created_at.asc())
            .limit(limit)
        )
        events = result.scalars().all()

        for event in events:
            # Publish to Redis Stream
            message_id = await EventBus.publish(
                stream_name=event.stream_name,
                event_type=event.event_type,
                payload=event.payload,
                actor_id=event.actor_id or "system",
            )

            if message_id:
                # Mark published
                event.published = True
                event.published_at = datetime.now(timezone.utc)

        if events:
            await self.db.commit()
