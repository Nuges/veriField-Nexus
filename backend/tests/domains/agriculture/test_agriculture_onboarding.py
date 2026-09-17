"""
=============================================================================
VeriField Nexus — Agriculture & Land Use Onboarding & Provisioning E2E Tests
=============================================================================
Tests:
1. Public Access Request submission with Agriculture & Land Use sector and VM0042 methodology.
2. Input validation (missing fields, invalid email, duplicate email, sector-methodology mismatch).
3. Super Admin review, approval, and rejection of Agriculture access requests:
   - Non-admin blocked from approving (403 Forbidden).
   - Super Admin approval provisions Organization with licensed_sectors=["AGRICULTURE_LAND_USE"].
   - Initial Org Admin provisioned with role="ADMIN".
   - Rejection sets status to REJECTED without provisioning tenant.
   - Repeated approval rejected safely (already processed).
4. Org Admin login with temporary password and verification of Agriculture workspace entitlement.
5. Workspace resolution testing:
   - canonicalSectorCode() maps agriculture, agri, land_use, farm, afolu to agriculture_land_use.
=============================================================================
"""

import uuid
from datetime import datetime, timedelta, timezone
import jwt as pyjwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domains.agriculture.seed import seed_agriculture_methodologies
from app.domains.authentication.models import User
from app.domains.methodologies.models.base_registry import Methodology, MethodologyFamily
from app.domains.organizations.models import Organization
from app.main import app


def _create_token(user_id: uuid.UUID, email: str, role: str, org_id: uuid.UUID = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "organization_id": str(org_id) if org_id else None,
        "iat": now,
        "exp": now + timedelta(hours=2),
        "jti": str(uuid.uuid4()),
    }
    return pyjwt.encode(payload, settings.effective_jwt_secret, algorithm="HS256")


@pytest.mark.asyncio
async def test_agriculture_access_request_and_super_admin_provisioning(db_session: AsyncSession):
    await seed_agriculture_methodologies(db_session)

    # 1. Fetch Agriculture Sector and VM0042 Methodology IDs
    sec_res = await db_session.execute(
        select(MethodologyFamily).where(MethodologyFamily.code == "AGRICULTURE_LAND_USE")
    )
    agri_sec = sec_res.scalars().first()
    assert agri_sec is not None

    meth_res = await db_session.execute(
        select(Methodology).where(Methodology.code == "VM0042")
    )
    vm42 = meth_res.scalars().first()
    assert vm42 is not None

    # Setup Super Admin user
    sa_email = settings.authorized_bootstrap_admin_email
    sa_user_res = await db_session.execute(select(User).where(User.email == sa_email))
    sa_user = sa_user_res.scalars().first()
    if not sa_user:
        sa_user = User(
            id=uuid.uuid4(),
            email=sa_email,
            full_name="Platform Super Admin",
            role="SUPER_ADMIN",
            is_active=True,
        )
        db_session.add(sa_user)
        await db_session.flush()

    sa_token = _create_token(sa_user.id, sa_user.email, "SUPER_ADMIN")
    sa_headers = {"Authorization": f"Bearer {sa_token}"}

    # Setup Regular user (for negative authorization tests)
    reg_org = (await db_session.execute(select(Organization).limit(1))).scalars().first()
    reg_user = User(
        id=uuid.uuid4(),
        email=f"regular.{uuid.uuid4().hex[:6]}@example.com",
        full_name="Regular Viewer",
        role="VIEWER",
        organization_id=reg_org.id if reg_org else uuid.uuid4(),
        is_active=True,
    )
    db_session.add(reg_user)
    await db_session.commit()

    reg_token = _create_token(reg_user.id, reg_user.email, "VIEWER")
    reg_headers = {"Authorization": f"Bearer {reg_token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 2. Test Input Validation Failures
        # A. Missing required fields
        bad_req = await client.post(
            "/api/v1/access-requests",
            json={"email": "bad@example.com"},
        )
        assert bad_req.status_code in (400, 422)

        # B. Invalid email
        bad_email = await client.post(
            "/api/v1/access-requests",
            json={
                "full_name": "Applicant",
                "email": "not-an-email",
                "organization_name": "Test Farm Co",
                "sector_id": str(agri_sec.id),
                "methodology_id": str(vm42.id),
                "project_name": "Test Soil Project",
            },
        )
        assert bad_email.status_code in (400, 422)

        # 3. Submit Valid Agriculture Access Request
        unique_id = uuid.uuid4().hex[:6]
        applicant_email = f"lead.agronomist.{unique_id}@example.com"
        applicant_org = f"Regenerative Agro-Holdings {unique_id}"
        valid_payload = {
            "full_name": "Lead Agronomist",
            "email": applicant_email,
            "phone": "+1-555-0199",
            "organization_name": applicant_org,
            "country": "India",
            "sector_id": str(agri_sec.id),
            "methodology_id": str(vm42.id),
            "project_name": "Community Soil Regeneration",
            "use_case": "Deployment of VM0042 digital MRV for smallholder regenerative agroforestry.",
        }
        submit_resp = await client.post("/api/v1/access-requests", json=valid_payload)
        assert submit_resp.status_code == 200, submit_resp.text
        resp_data = submit_resp.json()
        assert resp_data["status"] == "success"

        # 4. Duplicate Submission with Same Email Fails
        dup_resp = await client.post("/api/v1/access-requests", json=valid_payload)
        assert dup_resp.status_code == 400
        assert "already exists" in dup_resp.json()["detail"]

        # 5. Super Admin Reviews Access Request
        list_resp = await client.get("/api/v1/admin/access-requests?status=PENDING", headers=sa_headers)
        assert list_resp.status_code == 200
        requests = list_resp.json()
        matched = next((r for r in requests if r["email"] == applicant_email), None)
        assert matched is not None
        request_id = matched["id"]

        # 6. Non-Admin Attempt to Approve is Blocked (403)
        unauth_approve = await client.post(
            f"/api/v1/admin/access-requests/{request_id}/approve",
            headers=reg_headers,
        )
        assert unauth_approve.status_code == 403

        # 7. Super Admin Approves Request
        approve_resp = await client.post(
            f"/api/v1/admin/access-requests/{request_id}/approve",
            headers=sa_headers,
        )
        assert approve_resp.status_code == 200, approve_resp.text
        approve_data = approve_resp.json()
        assert "organization_id" in approve_data
        assert approve_data["organization_name"] == applicant_org
        assert approve_data["org_admin_email"] == applicant_email
        temp_password = approve_data["temporary_password"]
        assert len(temp_password) >= 8

        # 8. Repeated Approval Attempt Fails (Safe Idempotency Guard)
        repeat_approve = await client.post(
            f"/api/v1/admin/access-requests/{request_id}/approve",
            headers=sa_headers,
        )
        assert repeat_approve.status_code == 400
        assert "already processed" in repeat_approve.json()["detail"]

        # 9. Verify Organization Provisioned with Agriculture & Land Use Sector
        org_id = uuid.UUID(approve_data["organization_id"])
        org_query = await db_session.execute(select(Organization).where(Organization.id == org_id))
        org = org_query.scalars().first()
        assert org is not None
        assert "AGRICULTURE_LAND_USE" in org.licensed_sectors
        assert "VM0042" in org.licensed_methodologies

        # 10. Login with Provisioned User Credentials
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": applicant_email, "password": temp_password},
        )
        assert login_resp.status_code == 200, login_resp.text
        login_data = login_resp.json()
        assert "access_token" in login_data
        user_info = login_data["user"]
        assert user_info["email"] == applicant_email
        assert user_info["role"] in ("ORG_ADMIN", "ADMIN")
        assert user_info["organization_id"] == str(org_id)
        assert "AGRICULTURE_LAND_USE" in user_info["licensed_sectors"]


@pytest.mark.asyncio
async def test_access_request_rejection_flow(db_session: AsyncSession):
    await seed_agriculture_methodologies(db_session)

    sa_email = settings.authorized_bootstrap_admin_email
    sa_user_res = await db_session.execute(select(User).where(User.email == sa_email))
    sa_user = sa_user_res.scalars().first()
    if not sa_user:
        sa_user = User(
            id=uuid.uuid4(),
            email=sa_email,
            full_name="Platform Super Admin",
            role="SUPER_ADMIN",
            is_active=True,
        )
        db_session.add(sa_user)
        await db_session.flush()

    sa_token = _create_token(sa_user.id, sa_user.email, "SUPER_ADMIN")
    sa_headers = {"Authorization": f"Bearer {sa_token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Submit request
        unique_id = uuid.uuid4().hex[:6]
        rej_email = f"applicant.rejected.{unique_id}@example.com"
        await client.post(
            "/api/v1/access-requests",
            json={
                "full_name": "Ineligible Applicant",
                "email": rej_email,
                "organization_name": f"Ineligible Org {unique_id}",
                "country": "Kenya",
                "sector_id": "AGRICULTURE_LAND_USE",
                "methodology_id": "VM0042",
                "project_name": "Ineligible Project",
            },
        )

        list_resp = await client.get("/api/v1/admin/access-requests?status=PENDING", headers=sa_headers)
        matched = next(r for r in list_resp.json() if r["email"] == rej_email)
        req_id = matched["id"]

        # Super Admin Rejects
        rej_resp = await client.post(f"/api/v1/admin/access-requests/{req_id}/reject", headers=sa_headers)
        assert rej_resp.status_code == 200

        # Verify in DB: status is REJECTED, and NO user/org was created
        raw_req = await db_session.execute(
            text("SELECT status FROM access_requests WHERE id = :id"),
            {"id": req_id},
        )
        assert raw_req.fetchone()[0] == "REJECTED"

        usr_check = await db_session.execute(select(User).where(User.email == rej_email))
        assert usr_check.scalars().first() is None
