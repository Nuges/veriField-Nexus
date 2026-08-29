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


@pytest.mark.asyncio
async def test_community_feed_and_audits_endpoints(
    async_client: AsyncClient, admin_token_headers: dict
):
    # 1. Test Community Feed (no 500 error, returns 200 OK with valid list)
    comm_resp = await async_client.get("/api/v1/community")
    assert comm_resp.status_code == 200
    comm_data = comm_resp.json()
    assert "posts" in comm_data
    assert isinstance(comm_data["posts"], list)

    # 2. Test Audits list endpoint for mobile app
    audits_resp = await async_client.get("/api/v1/audits", headers=admin_token_headers)
    assert audits_resp.status_code == 200
    audits_data = audits_resp.json()
    assert "audits" in audits_data
    assert isinstance(audits_data["audits"], list)
