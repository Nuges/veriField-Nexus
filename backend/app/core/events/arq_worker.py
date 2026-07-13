import logging

from arq.connections import RedisSettings

from app.core.config import settings
from app.core.events.dispatcher import dispatch_async_event
from app.core.redis import close_redis, get_redis_client

logger = logging.getLogger("verifield.worker")


async def handle_async_event(ctx, event_json: str):
    """Arq task wrapper that forwards event JSON payloads to the dispatcher."""
    logger.info("Executing handle_async_event task...")
    await dispatch_async_event(event_json)


async def startup(ctx):
    logger.info("Background worker starting up...")
    get_redis_client()


async def shutdown(ctx):
    logger.info("Background worker shutting down...")
    await close_redis()


class WorkerSettings:
    """Settings class parsed by the arq CLI to launch the worker processes."""

    functions = [handle_async_event]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    on_startup = startup
    on_shutdown = shutdown
