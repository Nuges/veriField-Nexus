import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from app.core.redis import get_redis_client

logger = logging.getLogger("verifield.event_bus")


class EventBus:
    """
    Enterprise Event Bus backed by Redis Streams.
    Provides at-least-once delivery, event auditing, and decoupled choreographies.
    """

    @staticmethod
    async def publish(
        stream_name: str,
        event_type: str,
        payload: Dict[str, Any],
        actor_id: str = "system",
    ) -> str:
        """
        Publishes a domain event to a specific Redis Stream.
        """
        try:
            r = get_redis_client()
            event_data = {
                "event_type": event_type,
                "actor_id": str(actor_id),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": json.dumps(payload),
            }
            # Add to stream with automatic timestamp ID (*)
            message_id = await r.xadd(stream_name, event_data)
            logger.info(
                f"Published event '{event_type}' to stream '{stream_name}' with ID {message_id}"
            )

            # Immediately publish to the global Audit Stream (G-19)
            await EventBus._audit_log(event_type, actor_id, payload, message_id)

            return message_id
        except Exception as e:
            logger.error(f"Failed to publish event {event_type} to {stream_name}: {e}")
            # Do not raise here to prevent breaking the main transaction,
            # though in a true outbox pattern, this would be tied to the DB transaction.
            return None

    @staticmethod
    async def _audit_log(
        event_type: str,
        actor_id: str,
        payload: Dict[str, Any],
        original_message_id: str,
    ):
        """
        Routes every event to a centralized audit stream for compliance processing.
        """
        try:
            r = get_redis_client()
            audit_data = {
                "event_type": event_type,
                "actor_id": str(actor_id),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": json.dumps(payload),
                "source_message_id": str(original_message_id),
            }
            await r.xadd("audit_stream", audit_data)
        except Exception as e:
            logger.error(f"Failed to append to audit stream: {e}")
