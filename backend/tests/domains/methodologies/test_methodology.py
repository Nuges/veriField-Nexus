from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.methodologies.models.base_registry import (
    MethodologyFamily, MethodologyRegistry)


@pytest.mark.asyncio
async def test_create_methodology_and_version(
    async_client: AsyncClient, admin_token_headers: dict, db_session: AsyncSession
):
    # Setup test registry and family
    reg = MethodologyRegistry(code=f"REG-{uuid4().hex[:6]}", name="Test Registry")
    fam = MethodologyFamily(code=f"FAM-{uuid4().hex[:6]}", name="Test Family")
    db_session.add(reg)
    db_session.add(fam)
    await db_session.commit()
    await db_session.refresh(reg)
    await db_session.refresh(fam)

    # 1. Create Methodology
    code = f"METH-{uuid4().hex[:6]}"
    payload = {
        "code": code,
        "name": "Test Methodology",
        "description": "Test Desc",
        "registry_id": str(reg.id),
        "family_id": str(fam.id),
    }

    resp = await async_client.post(
        "/api/v1/methodologies/", json=payload, headers=admin_token_headers
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["code"] == code
    meth_id = data["id"]

    # 2. Create Version
    version_payload = {
        "version": "1.0.0",
        "release_date": "2026-01-01",
        "migration_notes": "Initial release",
    }

    resp2 = await async_client.post(
        f"/api/v1/methodologies/{meth_id}/versions",
        json=version_payload,
        headers=admin_token_headers,
    )
    assert resp2.status_code == 200, resp2.text
    vdata = resp2.json()
    assert vdata["version"] == "1.0.0"
    version_id = vdata["id"]

    # 3. Update Status to active
    status_payload = {"status": "active"}
    resp3 = await async_client.put(
        f"/api/v1/methodologies/{meth_id}/versions/{version_id}/status",
        json=status_payload,
        headers=admin_token_headers,
    )
    assert resp3.status_code == 200, resp3.text
    assert resp3.json()["status"] == "active"
