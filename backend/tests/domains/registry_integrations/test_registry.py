from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_registry_federation_flow(
    async_client: AsyncClient, admin_token_headers: dict
):
    # 1. Create a Registry Config
    config_payload = {
        "name": f"Verra Test Registry {uuid4()}",
        "adapter_type": "verra",
        "base_url": "https://verra.org/api",
        "credentials": {"api_key": "test_key"},
    }
    resp = await async_client.post(
        "/api/v1/registry-integrations/configs",
        json=config_payload,
        headers=admin_token_headers,
    )
    assert resp.status_code == 200, resp.text
    config = resp.json()
    config_id = config["id"]

    # 2. Trigger Sync Action
    project_id = str(uuid4())
    sync_payload = {
        "project_id": project_id,
        "action": "issueCredits",
        "payload": {"tco2e": 1000},
    }
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status": "success",
            "response_payload": {"serial_numbers": ["123"]},
        }
        mock_post.return_value = mock_resp

        sync_resp = await async_client.post(
            f"/api/v1/registry-integrations/{config_id}/sync",
            json=sync_payload,
            headers=admin_token_headers,
        )
    assert sync_resp.status_code == 200, sync_resp.text
    log = sync_resp.json()

    assert log["status"] == "success"
    assert "serial_numbers" in log["response_payload"]
