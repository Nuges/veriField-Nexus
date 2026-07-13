import logging

from arq import create_pool
from arq.connections import RedisSettings

from app.core.config import settings
from app.core.events.base import BaseEvent
from app.core.events.registry import get_subscribers

logger = logging.getLogger("verifield.events")


async def publish_event(event: BaseEvent):
    """
    Publishes an event to both local in-memory subscribers and background task queue.
    """
    logger.info(f"Publishing event: {event.event_type} (ID: {event.event_id})")

    # 1. Dispatch to synchronous / in-process handlers
    subscribers = get_subscribers(event.event_type)
    for callback in subscribers:
        try:
            # Run subscriber callback asynchronously
            await callback(event)
        except Exception as e:
            logger.error(
                f"Error in subscriber callback {callback.__name__} for event {event.event_type}: {e}"
            )

    # 2. Queue the event to the background workers (arq) for asynchronous processing
    try:
        redis_settings = RedisSettings.from_dsn(settings.redis_url)
        arq_pool = await create_pool(redis_settings)
        await arq_pool.enqueue_job("handle_async_event", event.model_dump_json())
        await arq_pool.close()
    except Exception as e:
        logger.error(
            f"Failed to queue event {event.event_type} to background worker: {e}"
        )
