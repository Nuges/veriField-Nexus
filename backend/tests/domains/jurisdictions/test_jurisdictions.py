import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_jurisdiction(
    async_client: AsyncClient, admin_token_headers: dict
):
    payload = {
        "code": f"US-CA-{uuid.uuid4().hex[:8]}",
        "name": "California",
        "level": "STATE",
        "metadata_context": {"tax": "10%"},
        "spatial_boundary": {},
        "status": "ACTIVE",
        "health_score": 100.0,
    }

    response = await async_client.post(
        "/api/v1/jurisdictions", json=payload, headers=admin_token_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "California"


@pytest.mark.asyncio
async def test_update_jurisdiction(
    async_client: AsyncClient, admin_token_headers: dict
):
    code = f"TEST-UPD-{uuid.uuid4().hex[:8]}"
    payload = {
        "code": code,
        "name": "Test Update",
        "level": "CUSTOM",
        "metadata_context": {},
        "spatial_boundary": {},
        "status": "ACTIVE",
        "health_score": 100.0,
    }

    response = await async_client.post(
        "/api/v1/jurisdictions", json=payload, headers=admin_token_headers
    )
    assert response.status_code == 201
    j_id = response.json()["id"]

    update_payload = {
        "name": "Updated Test",
        "code": code,
        "level": "CUSTOM",
        "status": "ACTIVE",
        "metadata_context": {},
        "spatial_boundary": {},
        "health_score": 100.0,
    }

    response = await async_client.put(
        f"/api/v1/jurisdictions/{j_id}",
        json=update_payload,
        headers=admin_token_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Test"


@pytest.mark.asyncio
async def test_delete_jurisdiction(
    async_client: AsyncClient, admin_token_headers: dict
):
    payload = {
        "code": f"TEST-DEL-{uuid.uuid4().hex[:8]}",
        "name": "Test Delete",
        "level": "CUSTOM",
        "metadata_context": {},
        "spatial_boundary": {},
        "status": "ACTIVE",
        "health_score": 100.0,
    }

    response = await async_client.post(
        "/api/v1/jurisdictions", json=payload, headers=admin_token_headers
    )
    assert response.status_code == 201
    j_id = response.json()["id"]

    response = await async_client.delete(
        f"/api/v1/jurisdictions/{j_id}", headers=admin_token_headers
    )
    assert response.status_code == 204

    response = await async_client.get(
        f"/api/v1/jurisdictions/{j_id}", headers=admin_token_headers
    )
    assert response.status_code == 404
