import json
import logging
from typing import Any, Optional

from redis.asyncio import ConnectionPool, Redis

from app.core.config import settings

logger = logging.getLogger("verifield.redis")

# Global Redis Pool & Client
_pool: Optional[ConnectionPool] = None
redis_client: Optional[Redis] = None


def get_redis_client() -> Redis:
    global redis_client, _pool
    if redis_client is None:
        _pool = ConnectionPool.from_url(settings.redis_url, decode_responses=True)
        redis_client = Redis(connection_pool=_pool)
    return redis_client


async def close_redis():
    global redis_client, _pool
    if redis_client:
        await redis_client.aclose()
    if _pool:
        await _pool.disconnect()
    redis_client = None
    _pool = None


# --- Cache Helpers ---
async def cache_get(key: str) -> Optional[Any]:
    try:
        r = get_redis_client()
        val = await r.get(key)
        return json.loads(val) if val else None
    except Exception as e:
        logger.error(f"Redis cache_get error: {e}")
        return None


async def cache_set(key: str, value: Any, ttl: int = 3600):
    try:
        r = get_redis_client()
        await r.set(key, json.dumps(value), ex=ttl)
    except Exception as e:
        logger.error(f"Redis cache_set error: {e}")


async def cache_delete(key: str):
    try:
        r = get_redis_client()
        await r.delete(key)
    except Exception as e:
        logger.error(f"Redis cache_delete error: {e}")


# --- Distributed Locks ---
class RedisLock:
    def __init__(self, name: str, timeout: int = 10):
        self.name = f"lock:{name}"
        self.timeout = timeout
        self.client = get_redis_client()
        self.acquired = False

    async def __aenter__(self):
        # Set NX px (millisecond precision timeout)
        self.acquired = await self.client.set(self.name, "1", ex=self.timeout, nx=True)
        return self.acquired

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.acquired:
            await self.client.delete(self.name)


# --- Rate Limiter (Token Bucket / Sliding Window) ---
async def is_rate_limited(key: str, limit: int = 60, window_secs: int = 60) -> bool:
    """
    Returns True if the rate limit is exceeded.
    Using simple Redis transaction (incr + expire).
    """
    try:
        r = get_redis_client()
        full_key = f"rate_limit:{key}"
        current = await r.get(full_key)
        if current and int(current) >= limit:
            return True

        # Increment and set TTL if new
        pipe = r.pipeline()
        pipe.incr(full_key)
        pipe.expire(full_key, window_secs)
        await pipe.execute()
        return False
    except Exception as e:
        logger.error(f"Redis rate limiter error: {e}")
        return False
