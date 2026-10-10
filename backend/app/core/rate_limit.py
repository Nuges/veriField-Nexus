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

import os
import time
import logging
from collections import defaultdict
from typing import Dict, List, Optional
from fastapi import Request, HTTPException, status
from app.core.config import settings

logger = logging.getLogger("verifield.rate_limit")

# Default trusted loopback / internal proxy addresses
TRUSTED_PROXIES = {"127.0.0.1", "::1", "localhost", "testclient"}

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


def extract_client_ip(request: Request) -> str:
    """
    Extract client IP address safely considering reverse proxy architecture.
    Only trusts X-Forwarded-For / X-Real-IP if the direct TCP peer (request.client.host)
    is an accredited reverse proxy. Prevents header spoofing attacks from direct clients.
    """
    socket_host = request.client.host if request.client else "unknown"

    # Assemble trusted proxies from defaults and environment settings
    trusted_set = set(TRUSTED_PROXIES)
    configured = getattr(settings, "trusted_proxies", None) or os.getenv("TRUSTED_PROXIES", "")
    if isinstance(configured, str) and configured:
        trusted_set.update(p.strip() for p in configured.split(",") if p.strip())
    elif isinstance(configured, (list, set, tuple)):
        trusted_set.update(configured)

    if socket_host in trusted_set:
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # The client's IP is the first IP in the chain before proxy hops
            return forwarded_for.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

    return socket_host


def rate_limit(limit: int = 5, window_seconds: int = 60, key_prefix: str = "auth"):
    """
    FastAPI dependency factory for endpoint rate limiting.
    
    Usage:
        @router.post("/login", dependencies=[Depends(rate_limit(limit=10, window_seconds=60, key_prefix="login"))])
    """
    async def _dependency(request: Request):
        client_ip = extract_client_ip(request)
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


async def check_login_rate_limit(
    request: Request,
    account_identifier: Optional[str] = None,
    account_limit: Optional[int] = None,
    ip_gateway_limit: Optional[int] = None,
    window_seconds: Optional[int] = None,
) -> None:
    """
    Rate limiter designed for authentication behind shared NATs / institutional gateways.
    
    Enforces dual-bucket sliding-window rate limiting:
    1. Per-Account limit (default 15/60s): strictly limits brute force attacks against
       any single account, regardless of whether IP is shared.
    2. Per-Gateway IP limit (default 100/60s): prevents broad credential-stuffing sweeps
       originating from a single gateway across multiple accounts.
    
    Key properties:
    - Legitimate users sharing an office NAT/cellular proxy are not locked out merely
      because another colleague entered the wrong password.
    - Unknown/nonexistent accounts increment identically, preventing user enumeration.
    - Fully configurable via environment/settings.
    """
    client_ip = extract_client_ip(request)

    act_limit = (
        account_limit
        if account_limit is not None
        else getattr(settings, "LOGIN_RATE_LIMIT_PER_ACCOUNT", 15)
    )
    gw_limit = (
        ip_gateway_limit
        if ip_gateway_limit is not None
        else getattr(settings, "LOGIN_RATE_LIMIT_PER_GATEWAY_IP", 100)
    )
    win_sec = (
        window_seconds
        if window_seconds is not None
        else getattr(settings, "LOGIN_RATE_LIMIT_WINDOW_SECONDS", 60)
    )

    # 1. Per-Account Check (normalized identifier)
    if account_identifier and account_identifier.strip():
        normalized = account_identifier.strip().lower()
        account_key = f"login:account:{normalized}"
        allowed_account = await check_rate_limit(
            account_key, limit=act_limit, window_seconds=win_sec
        )
        if not allowed_account:
            logger.warning(
                f"Rate limit exceeded for account {normalized} (limit={act_limit}/{win_sec}s)"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
                headers={"Retry-After": str(win_sec)},
            )

    # 2. Gateway IP Ceiling Check
    gateway_key = f"login:gateway:{client_ip}"
    allowed_ip = await check_rate_limit(
        gateway_key, limit=gw_limit, window_seconds=win_sec
    )
    if not allowed_ip:
        logger.warning(
            f"Rate limit exceeded for gateway IP {client_ip} (limit={gw_limit}/{win_sec}s)"
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
            headers={"Retry-After": str(win_sec)},
        )
