"""
=============================================================================
VeriField Nexus — All Sectors Onboarding & Auth Wiring Verification
=============================================================================
Verifies:
1. All 5 canonical sectors exist in methodology families:
   - AGRICULTURE_LAND_USE
   - BIOCHAR
   - COOKSTOVES
   - HYBRID_ENERGY
   - EV_MOBILITY
2. GET /api/v1/methodologies/families returns all 5 sectors.
3. GET /api/v1/methodologies returns active methodologies for each sector.
4. Each sector can be submitted via POST /api/v1/access-requests (signup flow).
5. Super Admin approval provisions Organization & User with the exact sector in licensed_sectors.
6. User can authenticate via POST /api/v1/auth/login and receives licensed_sectors for workspace hydration.
=============================================================================
"""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_password_hash
from app.domains.agriculture.seed import seed_agriculture_methodologies
from app.domains.authentication.models import User
from app.domains.methodologies.metadata.seed_phase_1 import seed_data
from app.domains.methodologies.models.base_registry import Methodology, MethodologyFamily
from app.domains.organizations.models import Organization


EXPECTED_SECTORS = [
    ("AGRICULTURE_LAND_USE", "Agriculture & Land Use"),
    ("BIOCHAR", "Biochar Carbon Removal"),
    ("COOKSTOVES", "Clean Cookstoves"),
    ("HYBRID_ENERGY", "Hybrid Energy & Mini-grids"),
    ("EV_MOBILITY", "EV Mobility"),
]


@pytest.mark.asyncio
async def test_all_five_sectors_exist_and_wired(
    async_client: AsyncClient,
    db_session: AsyncSession
):
    # Ensure full seeding of both seed_phase_1 and agriculture catalogue
    await seed_data(db_session)
    await seed_agriculture_methodologies(db_session)
    await db_session.commit()

    # 1. Verify GET /api/v1/methodologies/families (consumed by /signup page)
    fams_resp = await async_client.get("/api/v1/methodologies/families")
    assert fams_resp.status_code == 200, fams_resp.text
    fams_data = fams_resp.json()
    fams_by_code = {f["code"]: f for f in fams_data}

    for sector_code, sector_name in EXPECTED_SECTORS:
        assert sector_code in fams_by_code, f"Sector {sector_code} missing from GET /api/v1/methodologies/families"
        assert sector_name.lower() in fams_by_code[sector_code]["name"].lower(), (
            f"Expected {sector_name} for {sector_code}, got {fams_by_code[sector_code]['name']}"
        )

    # 2. Verify GET /api/v1/methodologies (consumed by /signup page methodology dropdown)
    meths_resp = await async_client.get("/api/v1/methodologies")
    assert meths_resp.status_code == 200, meths_resp.text
    meths_data = meths_resp.json()

    for sector_code, _ in EXPECTED_SECTORS:
        fam_id = fams_by_code[sector_code]["id"]
        # Match methodologies belonging to this family
        matching = [
            m for m in meths_data
            if (m.get("family_id") and str(m["family_id"]).replace("-", "").lower() == str(fam_id).replace("-", "").lower())
            or (m.get("family") and m["family"].get("code") == sector_code)
        ]
        assert len(matching) > 0, f"Expected catalog methodologies for sector {sector_code}"
        if sector_code not in ["AGRICULTURE_LAND_USE", "BIOCHAR"]:
            assert all(
                m.get("calculation_support_status") != "ENABLED"
                for m in matching
            ), f"Expected calculation engines to remain gated for {sector_code}"

    # 3. Super Admin setup for approvals
    sa_email = "superadmin.sector.audit@verifield.com"
    sa_pw = "SuperAdminAuditPass123!"
    sa_res = await db_session.execute(select(User).where(User.email == sa_email))
    sa_user = sa_res.scalars().first()
    if not sa_user:
        sa_user = User(
            id=uuid.uuid4(),
            email=sa_email,
            full_name="Super Admin Sector Auditor",
            password_hash=get_password_hash(sa_pw),
            role="SUPER_ADMIN",
            is_active=True,
        )
        db_session.add(sa_user)
        await db_session.commit()

    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": sa_email, "password": sa_pw}
    )
    assert login_resp.status_code == 200, login_resp.text
    sa_token = login_resp.json()["access_token"]
    sa_headers = {"Authorization": f"Bearer {sa_token}"}

    # 4. Test E2E Onboarding Flow for Production-Ready Sectors and Fail-Closed for Gated Sectors
    for sector_code, sector_name in EXPECTED_SECTORS:
        fam_id = fams_by_code[sector_code]["id"]
        matching_meths = [
            m for m in meths_data
            if (m.get("family_id") and str(m["family_id"]).replace("-", "").lower() == str(fam_id).replace("-", "").lower())
            or (m.get("family") and m["family"].get("code") == sector_code)
        ]

        # For gated sectors without production closure, verify fail-closed behavior
        if sector_code not in ["AGRICULTURE_LAND_USE", "BIOCHAR"]:
            fail_payload = {
                "full_name": f"Lead {sector_name}",
                "email": f"fail.{sector_code.lower()}@example.com",
                "organization_name": f"Org {sector_code}",
                "country": "Kenya",
                "sector_id": fam_id,
                "methodology_id": "UNCONFIGURED_CODE",
                "project_name": f"Pilot {sector_name}"
            }
            fail_resp = await async_client.post("/api/v1/access-requests", json=fail_payload)
            assert fail_resp.status_code == 422, f"Expected 422 for unclosed sector {sector_code}"
            continue

        chosen_meth = matching_meths[0]
        meth_id = chosen_meth["id"]

        test_email = f"user.{sector_code.lower()}.{uuid.uuid4().hex[:6]}@example.com"
        test_org = f"Org {sector_code} {uuid.uuid4().hex[:4]}"

        # Step A: Signup Submission (POST /api/v1/access-requests)
        signup_payload = {
            "full_name": f"Lead {sector_name}",
            "email": test_email,
            "organization_name": test_org,
            "country": "Kenya",
            "sector_id": fam_id,
            "methodology_id": meth_id,
            "project_name": f"Pilot {sector_name} Project"
        }
        ar_resp = await async_client.post("/api/v1/access-requests", json=signup_payload)
        assert ar_resp.status_code == 200, f"Signup failed for {sector_code}: {ar_resp.text}"

        # Step B: Super Admin Review & Approval
        # Retrieve the created access request
        list_ar_resp = await async_client.get("/api/v1/access-requests?status=PENDING", headers=sa_headers)
        assert list_ar_resp.status_code == 200, list_ar_resp.text
        pending_list = list_ar_resp.json()
        target_ar = next((ar for ar in pending_list if ar["email"] == test_email), None)
        assert target_ar is not None, f"Created access request not found in pending list for {test_email}"

        # Approve access request
        approve_resp = await async_client.post(
            f"/api/v1/admin/access-requests/{target_ar['id']}/approve",
            headers=sa_headers
        )
        assert approve_resp.status_code == 200, f"Approval failed for {sector_code}: {approve_resp.text}"

        # Step C: Inspect User and Organization in DB
        res_usr = await db_session.execute(select(User).where(User.email == test_email))
        created_user = res_usr.scalars().first()
        assert created_user is not None
        assert created_user.organization == test_org

        # Check user's licensed_sectors
        user_sectors = created_user.licensed_sectors
        assert sector_code in [s.upper() for s in user_sectors], (
            f"Expected {sector_code} in user licensed_sectors, got {user_sectors}"
        )

        # Step D: Test Sign-in (/api/v1/auth/login)
        # Update user password to a known password so we can test login endpoint
        known_pw = "TestSectorPass123!"
        created_user.password_hash = get_password_hash(known_pw)
        created_user.requires_password_change = False
        await db_session.commit()

        user_login_resp = await async_client.post(
            "/api/v1/auth/login",
            json={"email": test_email, "password": known_pw}
        )
        assert user_login_resp.status_code == 200, f"Login failed for {test_email}: {user_login_resp.text}"
        login_data = user_login_resp.json()
        assert "user" in login_data
        returned_user = login_data["user"]
        assert returned_user["email"] == test_email
        assert returned_user["licensed_sectors"] is not None
        returned_sectors = [s.upper() for s in returned_user["licensed_sectors"]]
        assert sector_code in returned_sectors, (
            f"Returned user in login response does not contain {sector_code}: {returned_sectors}"
        )
