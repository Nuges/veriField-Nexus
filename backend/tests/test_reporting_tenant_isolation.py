"""
Security & Tenant Isolation Tests for Reporting Domain (P1-05)

Verifies:
1. Tenant A can list and create reports for Tenant A (org_id == Org A)
2. Tenant B attempts to list Tenant A reports -> 403 Forbidden
3. Tenant B attempts to create report for Tenant A -> 403 Forbidden
4. Super Admin can list and generate reports across tenants
"""
import uuid
from unittest.mock import patch, AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import get_current_user
from app.db.session import (
    get_db,
    _init_fallback_db,
    _get_fallback_session_factory,
)
from app.domains.authentication.models import User
from app.domains.organizations.models import Organization
from app.main import app


@pytest.mark.asyncio
async def test_reporting_tenant_isolation():
    await _init_fallback_db()
    factory = _get_fallback_session_factory()

    org_a_id = uuid.uuid4()
    org_b_id = uuid.uuid4()

    user_a = User(
        id=uuid.uuid4(),
        email=f"admin_a_{uuid.uuid4().hex[:6]}@tenant-a.com",
        full_name="Admin Tenant A",
        role="ORG_ADMIN",
        organization_id=org_a_id,
        status="active",
    )
    user_b = User(
        id=uuid.uuid4(),
        email=f"admin_b_{uuid.uuid4().hex[:6]}@tenant-b.com",
        full_name="Admin Tenant B",
        role="ORG_ADMIN",
        organization_id=org_b_id,
        status="active",
    )
    super_admin = User(
        id=uuid.uuid4(),
        email=f"superadmin_{uuid.uuid4().hex[:6]}@verifield.com",
        full_name="Super Admin",
        role="SUPER_ADMIN",
        organization_id=None,
        status="active",
    )

    org_a = Organization(id=org_a_id, name=f"Tenant A {uuid.uuid4().hex[:6]}", status="ACTIVE")
    org_b = Organization(id=org_b_id, name=f"Tenant B {uuid.uuid4().hex[:6]}", status="ACTIVE")

    async with factory() as session:
        session.add(org_a)
        session.add(org_b)
        session.add(user_a)
        session.add(user_b)
        session.add(super_admin)
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
        # 1. Tenant A creates report for Org A -> 201 Created
        # -----------------------------------------------------------------
        app.dependency_overrides[get_current_user] = lambda: user_a
        report_payload_a = {
            "org_id": str(org_a_id),
            "title": "Q3 Verification Report",
            "report_type": "VERIFICATION_SUMMARY",
            "parameters": {"scope": "all_projects"},
        }
        res_create_a = await client.post("/api/v1/reporting/", json=report_payload_a)
        assert res_create_a.status_code == 201, f"Tenant A report creation failed: {res_create_a.text}"

        # -----------------------------------------------------------------
        # 2. Tenant A lists own reports -> 200 OK
        # -----------------------------------------------------------------
        res_list_a = await client.get(f"/api/v1/reporting/?org_id={org_a_id}")
        assert res_list_a.status_code == 200
        assert len(res_list_a.json()) >= 1

        # -----------------------------------------------------------------
        # 3. Tenant B attempts to list Tenant A reports -> 403 Forbidden
        # -----------------------------------------------------------------
        app.dependency_overrides[get_current_user] = lambda: user_b
        res_list_b_on_a = await client.get(f"/api/v1/reporting/?org_id={org_a_id}")
        assert res_list_b_on_a.status_code == 403, f"Tenant B listing Tenant A reports should be 403, got {res_list_b_on_a.status_code}"

        # -----------------------------------------------------------------
        # 4. Tenant B attempts to create report under Tenant A org_id -> 403 Forbidden
        # -----------------------------------------------------------------
        report_payload_spoof = {
            "org_id": str(org_a_id),
            "title": "Malicious Exfiltration Report",
            "report_type": "EMISSIONS",
            "parameters": {},
        }
        res_spoof = await client.post("/api/v1/reporting/", json=report_payload_spoof)
        assert res_spoof.status_code == 403, f"Tenant B spoofing report org_id should be 403, got {res_spoof.status_code}"

        # -----------------------------------------------------------------
        # 5. Super Admin lists Tenant A reports -> 200 OK
        # -----------------------------------------------------------------
        app.dependency_overrides[get_current_user] = lambda: super_admin
        res_list_sa = await client.get(f"/api/v1/reporting/?org_id={org_a_id}")
        assert res_list_sa.status_code == 200

        # -----------------------------------------------------------------
        # 6. Super Admin creates report for Org A -> 201 Created
        # -----------------------------------------------------------------
        res_create_sa = await client.post("/api/v1/reporting/", json=report_payload_a)
        assert res_create_sa.status_code == 201

    app.dependency_overrides.clear()
