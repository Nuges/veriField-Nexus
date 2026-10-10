import pytest
import uuid
from httpx import AsyncClient
from app.core.rate_limit import reset_rate_limits

@pytest.mark.asyncio
async def test_auth_rate_limiting_login_and_signup(async_client: AsyncClient):
    # Reset in-memory rate limiter and Redis keys
    reset_rate_limits()
    try:
        from app.core.redis import get_redis_client
        r = get_redis_client()
        keys = await r.keys("rate_limit:*")
        if keys:
            await r.delete(*keys)
    except Exception:
        pass

    shared_nat_ip = "198.51.100.55"
    headers = {"X-Forwarded-For": shared_nat_ip}

    # Test 1: Submitting 15 requests for a specific account under attack
    attacked_email = "victim_account@example.com"
    for i in range(15):
        resp = await async_client.post(
            "/api/v1/auth/login",
            json={"email": attacked_email, "password": f"WrongPassword_{i}!"},
            headers=headers,
        )
        assert resp.status_code in (401, 400, 422), f"Request {i+1} got unexpected status {resp.status_code}"

    # Test 2: 16th request against attacked_email must exceed account threshold and receive HTTP 429
    resp_limited = await async_client.post(
        "/api/v1/auth/login",
        json={"email": attacked_email, "password": "AnyPassword123!"},
        headers=headers,
    )
    assert resp_limited.status_code == 429
    assert resp_limited.json()["detail"] == "Too many requests. Please try again later."
    assert "Retry-After" in resp_limited.headers

    # Test 3: Shared NAT preservation — Colleague from the SAME gateway IP is NOT locked out!
    colleague_email = "colleague_agent@example.com"
    resp_colleague = await async_client.post(
        "/api/v1/auth/login",
        json={"email": colleague_email, "password": "ColleagueWrongPassword123!"},
        headers=headers,
    )
    # Colleague must NOT receive 429; their independent account bucket is clean
    assert resp_colleague.status_code in (401, 400, 422), f"Colleague was incorrectly throttled: {resp_colleague.status_code}"
    assert resp_colleague.status_code != 429

    # Test 4: Unrelated endpoint is unaffected
    resp_unrelated = await async_client.get("/api/v1/methodologies")
    assert resp_unrelated.status_code in (200, 401, 403)
    assert resp_unrelated.status_code != 429

    # Clean up
    reset_rate_limits()


def test_extract_client_ip_trusted_proxy_security():
    """Validates that extract_client_ip ignores client-forged X-Forwarded-For headers from untrusted hosts."""
    from app.core.rate_limit import extract_client_ip
    from unittest.mock import MagicMock

    # Case A: Untrusted direct external client attempting to spoof X-Forwarded-For
    untrusted_req = MagicMock()
    untrusted_req.client.host = "203.0.113.195"
    untrusted_req.headers = {"X-Forwarded-For": "10.0.0.1, 198.51.100.1"}
    # Must IGNORE forged header and return real socket IP
    assert extract_client_ip(untrusted_req) == "203.0.113.195"

    # Case B: Trusted reverse proxy (e.g. localhost / 127.0.0.1)
    trusted_req = MagicMock()
    trusted_req.client.host = "127.0.0.1"
    trusted_req.headers = {"X-Forwarded-For": "198.51.100.55, 10.0.0.1"}
    # Must parse client IP from trusted proxy header
    assert extract_client_ip(trusted_req) == "198.51.100.55"

