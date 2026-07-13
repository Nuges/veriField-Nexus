from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_marketplace_lifecycle(
    async_client: AsyncClient, admin_token_headers: dict
):
    org_id = str(uuid4())
    project_id = str(uuid4())

    payload = {
        "org_id": org_id,
        "project_id": project_id,
        "quantity": 1000.0,
        "price_per_unit": 25.50,
        "currency": "USD",
    }

    resp = await async_client.post(
        "/api/v1/marketplace/listings", json=payload, headers=admin_token_headers
    )
    assert resp.status_code == 201, resp.text

    get_resp = await async_client.get(
        "/api/v1/marketplace/listings", headers=admin_token_headers
    )
    assert get_resp.status_code == 200
    assert len(get_resp.json()) > 0
    assert get_resp.json()[0]["quantity"] == 1000.0
