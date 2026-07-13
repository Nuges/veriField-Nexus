from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_evidence_lifecycle(async_client: AsyncClient, admin_token_headers: dict):
    # We use a random UUID for activity_id. In a real test, this would need to exist in the DB,
    # but for testing the endpoint with raw endpoints, it might fail foreign key constraints
    # if the DB checks it. Since we are testing endpoints directly, let's see if it works.
    # Actually, we need to ensure the DB allows it or we create an activity first.

    # We removed the ForeignKey constraint from DB, so we can use a random UUID
    act_id = str(uuid4())

    # 1. Upload Evidence
    payload = {
        "activity_id": act_id,
        "file_uri": "s3://nexus-bucket/evidence/123.jpg",
        "file_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "evidence_type": "PHOTO",
        "metadata_json": {"gps": "0.0,0.0"},
    }

    resp = await async_client.post(
        "/api/v1/evidence/", json=payload, headers=admin_token_headers
    )
    assert resp.status_code == 201, resp.text
    ev = resp.json()
    ev_id = ev["id"]

    assert ev["status"] == "PENDING"
    assert (
        ev["file_hash"]
        == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )

    # 2. Verify Evidence
    verify_payload = {"status": "VERIFIED"}
    verify_resp = await async_client.put(
        f"/api/v1/evidence/{ev_id}/verify",
        json=verify_payload,
        headers=admin_token_headers,
    )
    assert verify_resp.status_code == 200
    assert verify_resp.json()["status"] == "VERIFIED"
    assert verify_resp.json()["verified_by"] is not None
