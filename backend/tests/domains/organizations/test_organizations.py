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


@pytest.mark.asyncio
async def test_access_request_sector_resolution(
    async_client: AsyncClient, admin_token_headers: dict
):
    unique_email = f"lead_{uuid.uuid4().hex[:8]}@example.com"
    req_payload = {
        "full_name": "Agric Lead",
        "email": unique_email,
        "organization_name": "Agric Test Org",
        "country": "Nigeria",
        "sector_id": "AGRICULTURE_LAND_USE",
        "project_name": "Agric Pilot",
    }
    post_res = await async_client.post("/api/v1/access-requests", json=req_payload)
    assert post_res.status_code == 200, post_res.text

    get_res = await async_client.get("/api/v1/access-requests", headers=admin_token_headers)
    assert get_res.status_code == 200, get_res.text
    items = get_res.json()
    match = next((item for item in items if item["email"] == unique_email), None)
    assert match is not None
    assert match["sector_name"] == "Agriculture & Land Use"
    assert match["sector_code"] == "AGRICULTURE_LAND_USE"
