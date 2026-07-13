from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_finance_lifecycle(async_client: AsyncClient, admin_token_headers: dict):
    from_org_id = str(uuid4())
    to_org_id = str(uuid4())
    project_id = str(uuid4())

    payload = {
        "from_org_id": from_org_id,
        "to_org_id": to_org_id,
        "amount": 50000.0,
        "currency": "USD",
        "project_id": project_id,
        "status": "COMPLETED",
    }

    resp = await async_client.post(
        "/api/v1/finance/transactions", json=payload, headers=admin_token_headers
    )
    assert resp.status_code == 201, resp.text
    tx = resp.json()
    tx_id = tx["id"]

    get_resp = await async_client.get(
        f"/api/v1/finance/transactions/{tx_id}", headers=admin_token_headers
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["amount"] == 50000.0
