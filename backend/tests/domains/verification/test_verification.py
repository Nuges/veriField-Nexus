from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_verification_lifecycle(
    async_client: AsyncClient, admin_token_headers: dict
):
    # We use raw UUIDs for foreign keys in this test
    project_id = str(uuid4())
    org_id = str(uuid4())

    # 1. Create Verification Task
    payload = {"project_id": project_id, "status": "ASSIGNED"}

    resp = await async_client.post(
        "/api/v1/verification/tasks", json=payload, headers=admin_token_headers
    )
    assert resp.status_code == 201, resp.text
    task = resp.json()
    task_id = task["id"]

    assert task["status"] == "ASSIGNED"

    # 2. Get Verification Task
    get_resp = await async_client.get(
        f"/api/v1/verification/tasks/{task_id}", headers=admin_token_headers
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == task_id

    # 3. Submit Audit Report
    audit_payload = {
        "project_id": project_id,
        "vvb_org_id": org_id,
        "report_uri": "s3://nexus-bucket/audits/report-123.pdf",
        "report_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "is_positive_opinion": True,
    }

    audit_resp = await async_client.post(
        "/api/v1/verification/audits", json=audit_payload, headers=admin_token_headers
    )
    assert audit_resp.status_code == 201, audit_resp.text
    assert audit_resp.json()["is_positive_opinion"]
