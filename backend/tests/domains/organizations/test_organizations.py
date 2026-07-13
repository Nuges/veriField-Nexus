import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_organization(
    async_client: AsyncClient, admin_token_headers: dict
):
    unique_name = f"Acme Climate Co {uuid.uuid4()}"
    payload = {
        "name": unique_name,
        "org_type": "Developer",
        "metadata_context": {"region": "Global"},
        "plan": "ENTERPRISE",
        "licensed_sectors": ["energy", "agriculture"],
    }

    response = await async_client.post(
        "/api/v1/organizations", json=payload, headers=admin_token_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == unique_name
    assert data["org_type"] == "Developer"
    assert data["plan"] == "ENTERPRISE"
    assert "id" in data


@pytest.mark.asyncio
async def test_update_organization(
    async_client: AsyncClient, admin_token_headers: dict
):
    unique_name = f"Org to Update {uuid.uuid4()}"
    payload = {
        "name": unique_name,
        "org_type": "VVB",
        "metadata_context": {},
        "plan": "FREE",
    }

    response = await async_client.post(
        "/api/v1/organizations", json=payload, headers=admin_token_headers
    )
    assert response.status_code == 200
    org_id = response.json()["id"]

    update_payload = {
        "name": f"Updated Org Name {uuid.uuid4()}",
        "plan": "PROFESSIONAL",
    }

    response = await async_client.put(
        f"/api/v1/organizations/{org_id}",
        json=update_payload,
        headers=admin_token_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == update_payload["name"]
    assert data["plan"] == "PROFESSIONAL"
    assert data["version"] == 2  # OCC incremented


@pytest.mark.asyncio
async def test_delete_organization(
    async_client: AsyncClient, admin_token_headers: dict
):
    unique_name = f"Org to Delete {uuid.uuid4()}"
    payload = {
        "name": unique_name,
        "org_type": "Registry",
        "metadata_context": {},
        "plan": "FREE",
    }

    response = await async_client.post(
        "/api/v1/organizations", json=payload, headers=admin_token_headers
    )
    assert response.status_code == 200
    org_id = response.json()["id"]

    # Delete the org (soft delete)
    response = await async_client.delete(
        f"/api/v1/organizations/{org_id}", headers=admin_token_headers
    )
    assert response.status_code == 204

    # Try fetching it
    response = await async_client.get(
        f"/api/v1/organizations/{org_id}", headers=admin_token_headers
    )
    assert response.status_code == 404
