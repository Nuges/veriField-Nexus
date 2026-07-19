import logging
import asyncio

from app.core.config import settings
from app.core.events.base import BaseEvent
from app.core.events.registry import get_subscribers
from app.core.events.dispatcher import dispatch_async_event

logger = logging.getLogger("verifield.events")

# Track whether Redis/arq is actually reachable (tested once on first event)
_redis_available: bool | None = None


async def _try_redis_dispatch(event: BaseEvent) -> bool:
    """Attempt to enqueue via arq/Redis. Returns True on success."""
    global _redis_available
    if _redis_available is False:
        return False

    try:
        from arq import create_pool
        from arq.connections import RedisSettings

        redis_settings = RedisSettings.from_dsn(settings.redis_url)
        arq_pool = await asyncio.wait_for(create_pool(redis_settings), timeout=3.0)
        await arq_pool.enqueue_job("handle_async_event", event.model_dump_json())
        await arq_pool.close()
        _redis_available = True
        return True
    except Exception as e:
        _redis_available = False
        logger.warning(
            f"Redis/arq unavailable ({e}). Falling back to local dispatch for all future events."
        )
        return False


async def publish_event(event: BaseEvent):
    """
    Publishes an event to both local in-memory subscribers and background task queue.
    """
    logger.info(f"Publishing event: {event.event_type} (ID: {event.event_id})")

    # 1. Dispatch to synchronous / in-process handlers
    subscribers = get_subscribers(event.event_type)
    for callback in subscribers:
        try:
            await callback(event)
        except Exception as e:
            logger.error(
                f"Error in subscriber callback {callback.__name__} for event {event.event_type}: {e}"
            )

    # 2. Queue the event for asynchronous processing
    dispatched_via_redis = False
    if settings.redis_url and _redis_available is not False:
        dispatched_via_redis = await _try_redis_dispatch(event)

    if not dispatched_via_redis:
        # Run locally — await directly so it cannot be silently cancelled
        try:
            await dispatch_async_event(event.model_dump_json())
        except Exception as e:
            logger.error(
                f"Failed local dispatch for event {event.event_type}: {e}",
                exc_info=True,
            )
