import pytest
import uuid
from httpx import AsyncClient
from app.core.rate_limit import reset_rate_limits

@pytest.mark.asyncio
async def test_auth_rate_limiting_login_and_signup(async_client: AsyncClient):
    # Reset in-memory rate limiter
    reset_rate_limits()

    # Test 1: Submitting requests under the limit (15 requests for login)
    for i in range(15):
        resp = await async_client.post(
            "/api/v1/auth/login",
            json={"email": f"nonexistent_{i}@example.com", "password": "WrongPassword123!"}
        )
        # Should be 401 Unauthorized or 400 Bad Request, NOT 429
        assert resp.status_code in (401, 400, 422), f"Request {i+1} got unexpected status {resp.status_code}"

    # Test 2: 16th request must exceed threshold and receive HTTP 429
    resp_limited = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "attacker@example.com", "password": "AnyPassword123!"}
    )
    assert resp_limited.status_code == 429
    assert resp_limited.json()["detail"] == "Too many requests. Please try again later."
    assert "Retry-After" in resp_limited.headers

    # Test 3: Unrelated endpoint (e.g. methodologies catalogue) is unaffected
    resp_unrelated = await async_client.get("/api/v1/methodologies")
    assert resp_unrelated.status_code in (200, 401, 403)
    assert resp_unrelated.status_code != 429

    # Clean up
    reset_rate_limits()
