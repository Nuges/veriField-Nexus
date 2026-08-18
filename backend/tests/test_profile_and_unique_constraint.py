import pytest
import uuid
import io
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.domains.projects.models import CarbonCalculation

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
    proj_id = uuid.uuid4()
    act_id = uuid.uuid4()
    
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
