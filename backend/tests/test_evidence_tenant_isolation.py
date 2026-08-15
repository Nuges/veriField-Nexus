"""
Security & Tenant Isolation Tests for Evidence Domain (P0-02)

Verifies:
1. Tenant A can upload evidence for Tenant A activity
2. Tenant A can read own evidence
3. Tenant B cannot read Tenant A evidence (rejected with 403/404)
4. Tenant B cannot upload evidence for Tenant A activity (rejected with 403)
5. Tenant B cannot verify Tenant A evidence (rejected with 403)
6. Super Admin can read and verify evidence across tenants
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import get_current_user
from app.db.session import (
    get_db,
    _init_fallback_db,
    _get_fallback_session_factory,
)
from app.domains.activities.models import Activity
from app.domains.authentication.models import User
from app.domains.evidence.models import Evidence
from app.domains.organizations.models import Organization
from app.main import app


@pytest.mark.asyncio
@patch("app.core.event_bus.EventBus.publish", new_callable=AsyncMock)
async def test_evidence_tenant_isolation(mock_event_bus):
    await _init_fallback_db()
    factory = _get_fallback_session_factory()

    org_a_id = uuid.uuid4()
    org_b_id = uuid.uuid4()

    user_a_id = uuid.uuid4()
    user_b_id = uuid.uuid4()
    super_admin_id = uuid.uuid4()

    user_a = User(
        id=user_a_id,
        email=f"admin_a_{uuid.uuid4().hex[:6]}@tenant-a.com",
        full_name="Admin Tenant A",
        role="ORG_ADMIN",
        organization_id=org_a_id,
        status="active",
    )
    user_b = User(
        id=user_b_id,
        email=f"admin_b_{uuid.uuid4().hex[:6]}@tenant-b.com",
        full_name="Admin Tenant B",
        role="ORG_ADMIN",
        organization_id=org_b_id,
        status="active",
    )
    super_admin = User(
        id=super_admin_id,
        email=f"superadmin_{uuid.uuid4().hex[:6]}@verifield.com",
        full_name="Super Admin",
        role="SUPER_ADMIN",
        organization_id=None,
        status="active",
    )

    org_a = Organization(
        id=org_a_id,
        name=f"Tenant A Corp {uuid.uuid4().hex[:6]}",
        status="ACTIVE",
    )
    org_b = Organization(
        id=org_b_id,
        name=f"Tenant B Corp {uuid.uuid4().hex[:6]}",
        status="ACTIVE",
    )

    activity_a_id = uuid.uuid4()
    activity_a = Activity(
        id=activity_a_id,
        organization_id=org_a_id,
        user_id=user_a_id,
        activity_type="cookstove_distribution",
        status="SUBMITTED",
        activity_data={"units": 5},
        captured_at=datetime.now(timezone.utc),
    )

    async with factory() as session:
        session.add(org_a)
        session.add(org_b)
        session.add(user_a)
        session.add(user_b)
        session.add(super_admin)
        session.add(activity_a)
        await session.commit()

    async def override_get_db():
        async with factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:

        # -----------------------------------------------------------------
        # 1. Tenant A uploads evidence for Activity A -> 201 Created
        # -----------------------------------------------------------------
        app.dependency_overrides[get_current_user] = lambda: user_a
        upload_payload = {
            "activity_id": str(activity_a_id),
            "file_uri": "s3://nexus-bucket/evidence/tenant_a_001.jpg",
            "file_hash": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
            "evidence_type": "PHOTO",
            "metadata_json": {"camera": "field_unit_1"},
        }
        res_upload_a = await client.post("/api/v1/evidence", json=upload_payload)
        assert res_upload_a.status_code == 201, f"Tenant A upload failed: {res_upload_a.text}"
        evidence_a_id = res_upload_a.json()["id"]

        # -----------------------------------------------------------------
        # 2. Tenant A reads own evidence -> 200 OK
        # -----------------------------------------------------------------
        res_get_a = await client.get(f"/api/v1/evidence/{evidence_a_id}")
        assert res_get_a.status_code == 200
        assert res_get_a.json()["id"] == evidence_a_id

        # -----------------------------------------------------------------
        # 3. Tenant B attempts to read Tenant A evidence -> 403/404 Forbidden
        # -----------------------------------------------------------------
        app.dependency_overrides[get_current_user] = lambda: user_b
        res_get_b = await client.get(f"/api/v1/evidence/{evidence_a_id}")
        assert res_get_b.status_code in (403, 404), f"Tenant B read should be rejected, got {res_get_b.status_code}"

        # -----------------------------------------------------------------
        # 4. Tenant B attempts to upload evidence to Tenant A activity -> 403 Forbidden
        # -----------------------------------------------------------------
        upload_payload_b = {
            "activity_id": str(activity_a_id),
            "file_uri": "s3://nexus-bucket/evidence/tenant_b_attack.jpg",
            "file_hash": "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
            "evidence_type": "PHOTO",
            "metadata_json": {},
        }
        res_upload_b = await client.post("/api/v1/evidence", json=upload_payload_b)
        assert res_upload_b.status_code == 403, f"Tenant B upload to Tenant A activity should be 403, got {res_upload_b.status_code}"

        # -----------------------------------------------------------------
        # 5. Tenant B attempts to verify Tenant A evidence -> 403 Forbidden
        # -----------------------------------------------------------------
        res_verify_b = await client.put(f"/api/v1/evidence/{evidence_a_id}/verify", json={"status": "VERIFIED"})
        assert res_verify_b.status_code == 403, f"Tenant B verify Tenant A evidence should be 403, got {res_verify_b.status_code}"

        # -----------------------------------------------------------------
        # 6. Super Admin reads and verifies Tenant A evidence -> 200 OK
        # -----------------------------------------------------------------
        app.dependency_overrides[get_current_user] = lambda: super_admin
        res_get_sa = await client.get(f"/api/v1/evidence/{evidence_a_id}")
        assert res_get_sa.status_code == 200, f"Super Admin read failed: {res_get_sa.text}"

        res_verify_sa = await client.put(f"/api/v1/evidence/{evidence_a_id}/verify", json={"status": "VERIFIED"})
        assert res_verify_sa.status_code == 200, f"Super Admin verify failed: {res_verify_sa.text}"
        assert res_verify_sa.json()["status"] == "VERIFIED"

    app.dependency_overrides.clear()
