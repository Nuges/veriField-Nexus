from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_programme_lifecycle(
    async_client: AsyncClient, admin_token_headers: dict
):
    # 1. Create a Programme
    payload = {
        "name": "Sub-Saharan Solar Initiative",
        "org_id": str(uuid4()),
        "funding_sources": ["World Bank", "Green Climate Fund"],
        "budget": 50000000.0,
        "status": "ACTIVE",
    }

    resp = await async_client.post(
        "/api/v1/programmes/", json=payload, headers=admin_token_headers
    )
    assert resp.status_code == 201, resp.text
    prog = resp.json()
    prog_id = prog["id"]

    assert prog["name"] == "Sub-Saharan Solar Initiative"
    assert prog["budget"] == 50000000.0

    # 2. Get the Programme
    get_resp = await async_client.get(
        f"/api/v1/programmes/{prog_id}", headers=admin_token_headers
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == prog_id

    # 3. List Programmes
    list_resp = await async_client.get(
        "/api/v1/programmes/", headers=admin_token_headers
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()) > 0
