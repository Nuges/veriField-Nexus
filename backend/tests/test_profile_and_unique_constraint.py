import pytest
import uuid
import io
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.domains.organizations.models import Organization
from app.domains.authentication.models import User
from app.domains.projects.models import Project, CarbonCalculation
from app.domains.activities.models import Activity

@pytest.mark.asyncio
async def test_profile_update_and_avatar_upload(async_client: AsyncClient, admin_token_headers: dict):
    # 1. Update Profile via PUT /api/v1/auth/profile
    update_payload = {
        "full_name": "Audited Administrator",
        "phone": "+254700000000"
    }
    resp = await async_client.put(
        "/api/v1/auth/profile",
        json=update_payload,
        headers=admin_token_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["full_name"] == "Audited Administrator"
    assert data["phone"] == "+254700000000"

    # 2. Upload Avatar with invalid extension -> 400
    fake_exe = io.BytesIO(b"malicious executable payload")
    resp_bad = await async_client.post(
        "/api/v1/auth/upload-avatar",
        files={"file": ("malware.exe", fake_exe, "application/x-msdownload")},
        headers=admin_token_headers
    )
    assert resp_bad.status_code == 400
    assert "supported" in resp_bad.text

    # 3. Upload Valid PNG Avatar -> 200
    valid_png = io.BytesIO(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4")
    resp_good = await async_client.post(
        "/api/v1/auth/upload-avatar",
        files={"file": ("profile.png", valid_png, "image/png")},
        headers=admin_token_headers
    )
    assert resp_good.status_code == 200
    res_data = resp_good.json()
    assert "avatar_url" in res_data
    assert res_data["avatar_url"].startswith("/static/avatars/avatar_")

@pytest.mark.asyncio
async def test_carbon_calculation_db_unique_constraint(db_session: AsyncSession):
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    act_id = uuid.uuid4()

    org = Organization(id=org_id, name=f"Unique Calc Org {org_id.hex[:6]}", org_type="DEVELOPER", status="ACTIVE")
    user = User(
        id=user_id,
        email=f"unique_{uuid.uuid4().hex[:6]}@example.com",
        full_name="Unique User",
        role="ORG_ADMIN",
        organization_id=org_id,
        status="active",
        is_active=True,
    )
    proj = Project(id=proj_id, organization_id=org_id, name=f"Unique Calc Project {proj_id.hex[:6]}")
    from datetime import datetime, timezone
    now_utc = datetime.now(timezone.utc)
    act = Activity(id=act_id, organization_id=org_id, user_id=user_id, activity_type="MONITORING", captured_at=now_utc)

    db_session.add_all([org, user, proj, act])
    await db_session.commit()

    # 1. Add first calculation
    calc1 = CarbonCalculation(
        id=uuid.uuid4(),
        project_id=proj_id,
        activity_id=act_id,
        tco2e_generated=10.5
    )
    db_session.add(calc1)
    await db_session.commit()
    
    # 2. Add duplicate calculation for same (project_id, activity_id) -> Expect IntegrityError
    calc2 = CarbonCalculation(
        id=uuid.uuid4(),
        project_id=proj_id,
        activity_id=act_id,
        tco2e_generated=20.0
    )
    db_session.add(calc2)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()
