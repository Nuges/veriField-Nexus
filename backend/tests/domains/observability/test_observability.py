import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_observability(async_client: AsyncClient):
    resp = await async_client.get("/api/v1/observability/health")
    assert resp.status_code == 200
    assert resp.json()["status"] in ["ok", "degraded"]

    metrics_resp = await async_client.get("/api/v1/observability/metrics")
    assert metrics_resp.status_code == 200
    assert "nexus_requests_total" in metrics_resp.text
