"""
=============================================================================
VeriField Nexus — Production Rate Limiting Infrastructure
=============================================================================
Provides production-grade token-bucket / sliding-window rate limiting for
sensitive authentication, signup, password management, and MFA endpoints.

Supports dual-mode execution:
1. Redis-backed distributed rate limiting in production clusters.
2. High-performance, in-memory sliding window fallback for standalone
   deployments and deterministic test environments.
=============================================================================
"""

import time
import logging
from collections import defaultdict
from typing import Dict, List, Optional
from fastapi import Request, HTTPException, status
from app.core.config import settings

logger = logging.getLogger("verifield.rate_limit")

# In-memory sliding window store: key -> list of timestamp floats
_memory_store: Dict[str, List[float]] = defaultdict(list)


def _cleanup_memory_store(now: float, window_seconds: int):
    """Periodically prune expired timestamps from the in-memory store."""
    expired_keys = []
    for k, timestamps in list(_memory_store.items()):
        valid = [t for t in timestamps if now - t < window_seconds]
        if valid:
            _memory_store[k] = valid
        else:
            expired_keys.append(k)
    for k in expired_keys:
        _memory_store.pop(k, None)


async def check_rate_limit(
    key: str,
    limit: int = 5,
    window_seconds: int = 60,
) -> bool:
    """
    Returns True if allowed, False if rate limit exceeded.
    Attempts Redis first; falls back to in-memory sliding window.
    """
    now = time.time()
    
    # 1. Try Redis if configured and reachable
    try:
        from app.core.redis import get_redis_client
        r = get_redis_client()
        full_key = f"rate_limit:{key}"
        
        pipe = r.pipeline()
        pipe.incr(full_key)
        pipe.expire(full_key, window_seconds)
        res = await pipe.execute()
        current_count = res[0]
        if current_count > limit:
            return False
        return True
    except Exception:
        # Fall back to in-memory sliding window store
        pass

    # 2. In-memory sliding window implementation
    timestamps = _memory_store[key]
    valid_timestamps = [t for t in timestamps if now - t < window_seconds]
    if len(valid_timestamps) >= limit:
        _memory_store[key] = valid_timestamps
        return False
    
    valid_timestamps.append(now)
    _memory_store[key] = valid_timestamps
    
    # Prune memory periodically
    if len(_memory_store) > 1000:
        _cleanup_memory_store(now, window_seconds)
        
    return True


def reset_rate_limits():
    """Clear in-memory rate limiting state (useful for test setup/teardown)."""
    _memory_store.clear()


def rate_limit(limit: int = 5, window_seconds: int = 60, key_prefix: str = "auth"):
    """
    FastAPI dependency factory for endpoint rate limiting.
    
    Usage:
        @router.post("/login", dependencies=[Depends(rate_limit(limit=10, window_seconds=60, key_prefix="login"))])
    """
    async def _dependency(request: Request):
        # Extract client IP address safely
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
            
        rate_key = f"{key_prefix}:{client_ip}"
        
        allowed = await check_rate_limit(rate_key, limit=limit, window_seconds=window_seconds)
        if not allowed:
            logger.warning(f"Rate limit exceeded for {rate_key} (limit={limit}/{window_seconds}s)")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
                headers={"Retry-After": str(window_seconds)},
            )
            
    return _dependency
