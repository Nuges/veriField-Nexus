import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_user(async_client: AsyncClient, admin_token_headers: dict):
    response = await async_client.post(
        "/api/v1/auth/users",
        json={
            "full_name": "Test User",
            "email": f"testuser_{uuid.uuid4().hex}@example.com",
            "password": "StrongPassword123!",
            "role": "field_agent",
        },
        headers=admin_token_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["role"] == "field_agent"
    assert "version" in data
    assert "is_deleted" in data


@pytest.mark.asyncio
async def test_update_user_optimistic_concurrency(
    async_client: AsyncClient, admin_token_headers: dict
):
    # First create
    resp = await async_client.post(
        "/api/v1/auth/users",
        json={
            "full_name": "Concurrency User",
            "email": f"concur_{uuid.uuid4().hex}@example.com",
            "password": "StrongPassword123!",
        },
        headers=admin_token_headers,
    )
    assert resp.status_code == 201
    user_id = resp.json()["id"]

    # Update once
    resp1 = await async_client.put(
        f"/api/v1/auth/users/{user_id}",
        json={"full_name": "Updated 1"},
        headers=admin_token_headers,
    )
    assert resp1.status_code == 200
    assert resp1.json()["version"] == 2

    # In a real OCC scenario with the API, the client passes back the version it thinks it has,
    # but the current schema updates it directly on the backend. This test confirms the backend version increments.


@pytest.mark.asyncio
async def test_soft_delete(async_client: AsyncClient, admin_token_headers: dict):
    resp = await async_client.post(
        "/api/v1/auth/users",
        json={
            "full_name": "Delete Me",
            "email": f"delete_{uuid.uuid4().hex}@example.com",
            "password": "Pass123!",
        },
        headers=admin_token_headers,
    )
    assert resp.status_code == 201
    user_id = resp.json()["id"]

    del_resp = await async_client.delete(
        f"/api/v1/auth/users/{user_id}", headers=admin_token_headers
    )
    assert del_resp.status_code == 204

    # Verify it doesn't appear in list
    list_resp = await async_client.get(
        "/api/v1/auth/users", headers=admin_token_headers
    )
    users = list_resp.json()
    assert all(u["id"] != user_id for u in users)
