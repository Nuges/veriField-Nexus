import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.registry_integrations.models import RegistryConfig


@pytest.mark.asyncio
async def test_registry_integration_sync(async_client: AsyncClient, admin_token_headers: dict, db_session: AsyncSession):
    registry_id = uuid.uuid4()
    project_id = uuid.uuid4()

    # 1. Create a registry config record
    reg_config = RegistryConfig(
        id=registry_id,
        name=f"Verra Registry {uuid.uuid4().hex[:6]}",
        adapter_type="verra",
        base_url="https://api.registry.example.org",
        credentials={"api_key": "test-key-mock"},
        is_active=True,
    )
    db_session.add(reg_config)
    await db_session.commit()

    # 2. Trigger Sync via /api/v1/registry/{registry_id}/sync
    payload = {
        "project_id": str(project_id),
        "action": "registerProject",
        "payload": {"project_name": "Test Forest Project"},
    }

    resp = await async_client.post(
        f"/api/v1/registry/{registry_id}/sync", json=payload, headers=admin_token_headers
    )
    assert resp.status_code == 200, f"Sync failed: {resp.text}"
    sync_log = resp.json()
    assert sync_log["status"] in ["success", "pending", "failed", "Queued", "Success"]

    # 3. Trigger Bundle Sync for local provider
    bundle_id = str(uuid.uuid4())
    resp_bundle = await async_client.post(
        f"/api/v1/registry/sync/{bundle_id}?provider_name=local",
        headers=admin_token_headers,
    )
    assert resp_bundle.status_code == 200
    assert resp_bundle.json()["success"] is True

    # 4. Trigger Bundle Sync for external unconfigured provider -> returns structured 501
    resp_ext = await async_client.post(
        f"/api/v1/registry/sync/{bundle_id}?provider_name=verra",
        headers=admin_token_headers,
    )
    assert resp_ext.status_code == 501
    assert "pending live credentials" in resp_ext.json()["detail"] or "staging" in resp_ext.json()["detail"]

