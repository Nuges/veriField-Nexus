import uuid
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from app.domains.organizations.routers.access_requests import approve_access_request


@pytest.mark.asyncio
@pytest.mark.parametrize("sector", ["AGRICULTURE_LAND_USE", "unknown-sector"])
async def test_approval_never_discards_an_explicit_unresolved_sector(sector):
    request = SimpleNamespace(
        status="PENDING", organization_name="Solar Company",
        use_case=json.dumps({"sector_id": sector, "project_name": "Requested Farm"}),
    )
    db = SimpleNamespace(execute=AsyncMock(), add=Mock(), commit=AsyncMock())

    async def execute(statement, params=None):
        query = str(statement)
        if "SELECT * FROM access_requests" in query:
            return SimpleNamespace(fetchone=lambda: request)
        if "FROM methodology_families" in query:
            assert not params or "alias" not in params, "Explicit sector must not be replaced by organization-name inference"
            return SimpleNamespace(fetchone=lambda: None)
        raise AssertionError("Unresolved sector must stop approval before provisioning")

    db.execute.side_effect = execute
    with pytest.raises(HTTPException) as caught:
        await approve_access_request(
            uuid.uuid4(), db=db, current_user=SimpleNamespace(role="SUPER_ADMIN"),
        )
    assert caught.value.status_code == 409
    assert "operating sector" in caught.value.detail.lower()
    db.add.assert_not_called()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_agriculture_approval_without_methodology_preserves_selection(db_session, monkeypatch):
    from sqlalchemy import select, text
    from app.core.event_bus import EventBus
    from app.domains.authentication.models import User
    from app.domains.authentication.repository import UserRepository
    from app.domains.authentication.schemas import UserResponse
    from app.domains.methodologies.models.base_registry import MethodologyFamily
    from app.domains.organizations.models import Organization
    from app.domains.organizations.routers.access_requests import AccessRequestCreate, create_access_request
    from app.domains.projects.models import Project

    monkeypatch.setattr(EventBus, "publish", AsyncMock())
    family = (await db_session.execute(select(MethodologyFamily).where(
        MethodologyFamily.code == "AGRICULTURE_LAND_USE"
    ))).scalars().first()
    if family is None:
        family = MethodologyFamily(code="AGRICULTURE_LAND_USE", name="Agriculture & Land Use", is_active=True)
        db_session.add(family)
        await db_session.commit()
    admin = (await db_session.execute(select(User).where(User.role == "SUPER_ADMIN"))).scalars().first()
    suffix = uuid.uuid4().hex[:10]
    email = f"partner-{suffix}@example.test"
    project_name = f"Requested Farm {suffix}"
    await create_access_request(AccessRequestCreate(
        full_name="New Partner", email=email, organization_name=f"Partner {suffix}",
        country="India", sector_id="AGRICULTURE_LAND_USE", project_name=project_name,
    ), db=db_session)
    request_id = (await db_session.execute(text("SELECT id FROM access_requests WHERE email=:email"), {"email": email})).scalar_one()
    result = await approve_access_request(uuid.UUID(str(request_id)), db=db_session, current_user=admin)
    organization = (await db_session.execute(select(Organization).where(Organization.id == uuid.UUID(result["organization_id"])))).scalar_one()
    assert organization.licensed_sectors == ["AGRICULTURE_LAND_USE"]
    assert organization.licensed_methodologies == []
    project = (await db_session.execute(select(Project).where(Project.organization_id == organization.id))).scalar_one()
    assert project.name == project_name
    assert project.sector_id == family.id
    assert project.methodology_id is None
    user = await UserRepository(db_session).get_by_email(email)
    assert UserResponse.model_validate(user).licensed_sectors == ["AGRICULTURE_LAND_USE"]
    assert (await db_session.execute(text("SELECT status FROM access_requests WHERE id=:id"), {"id": str(request_id)})).scalar_one() == "APPROVED"


@pytest.mark.asyncio
async def test_list_methodologies_scoped_to_agriculture(async_client: AsyncClient):
    """Verifies GET /api/v1/methodologies?sector=AGRICULTURE_LAND_USE returns ONLY VM0042."""
    response = await async_client.get("/api/v1/methodologies?sector=AGRICULTURE_LAND_USE")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1

    codes = [m["code"] for m in data]
    assert "VM0042" in codes
    assert "VM0051" in codes
    assert "VM0047" in codes
    assert "VM0032" in codes
    # Enforce zero cross-sector leakage
    assert "VM0044" not in codes
    assert "BIOCHAR_C_SINK" not in codes
    assert "AMS_I_F" not in codes
    assert "AMS_II_G" not in codes
    assert "EV_DISPLACEMENT" not in codes
    # Enforce supporting tools are not primary methodologies
    assert "VT0014" not in codes
    assert "VMD0053" not in codes
    assert "BM_T_001" not in codes
    assert "GS_AGRI_ACT_REQ" not in codes


@pytest.mark.asyncio
async def test_list_methodologies_scoped_to_biochar(async_client: AsyncClient):
    """Verifies GET /api/v1/methodologies?sector=BIOCHAR returns only proven Biochar methodologies."""
    response = await async_client.get("/api/v1/methodologies?sector=BIOCHAR")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1

    codes = [m["code"] for m in data]
    assert "VM0042" not in codes
    assert "VM0044" in codes
    assert "PURO_BIOCHAR_2025" in codes
    assert "BIOCHAR_C_SINK" in codes
    # Obsolete / non-canonical codes must be absent
    assert "EBC_BIOCHAR" not in codes
    assert "GS_BIOCHAR" not in codes


@pytest.mark.asyncio
async def test_list_methodologies_scoped_to_other_sectors(async_client: AsyncClient):
    """Verifies that each canonical sector returns its strictly scoped primary methodologies."""
    # Clean Cookstoves (GS_MECD, VM0050, AMS_II_G)
    cs_resp = await async_client.get("/api/v1/methodologies?sector=COOKSTOVES")
    assert cs_resp.status_code == 200
    cs_codes = {m["code"] for m in cs_resp.json()}
    assert "GS_MECD" in cs_codes
    assert "VM0050" in cs_codes
    assert "AMS_II_G" in cs_codes
    assert "VM0042" not in cs_codes
    assert "VM0044" not in cs_codes

    # Hybrid Energy (AMS_I_F, AMS_I_L, ACM0002)
    he_resp = await async_client.get("/api/v1/methodologies?sector=HYBRID_ENERGY")
    assert he_resp.status_code == 200
    he_codes = {m["code"] for m in he_resp.json()}
    assert "AMS_I_F" in he_codes
    assert "AMS_I_L" in he_codes
    assert "ACM0002" in he_codes
    assert "VM0042" not in he_codes
    assert "VM0044" not in he_codes

    # EV Mobility (VM0038, AMS_III_C)
    ev_resp = await async_client.get("/api/v1/methodologies?sector=EV_MOBILITY")
    assert ev_resp.status_code == 200
    ev_codes = {m["code"] for m in ev_resp.json()}
    assert "VM0038" in ev_codes
    assert "AMS_III_C" in ev_codes
    assert "VMD0049" not in ev_codes  # Supporting tool must NOT appear
    assert "VM0042" not in ev_codes
    assert "VM0044" not in ev_codes


@pytest.mark.asyncio
async def test_list_methodologies_unknown_sector_fails_closed(async_client: AsyncClient):
    """Verifies GET /api/v1/methodologies with unknown sector fails closed (returns [])."""
    response = await async_client.get("/api/v1/methodologies?sector=NON_EXISTENT_SECTOR_XYZ")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.asyncio
async def test_access_request_valid_agriculture_and_vm0042(async_client: AsyncClient):
    """Verifies valid access request with Agriculture & Land Use and VM0042 succeeds."""
    unique_email = f"agri_test_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "full_name": "Agri User",
        "email": unique_email,
        "organization_name": "Agri Innovations Ltd",
        "country": "Nigeria",
        "sector_id": "AGRICULTURE_LAND_USE",
        "methodology_id": "VM0042",
        "project_name": "Soil Organic Carbon Project",
    }
    response = await async_client.post("/api/v1/access-requests", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"


@pytest.mark.asyncio
async def test_access_request_valid_agriculture_and_vm0042_uuid(async_client: AsyncClient):
    """Verifies access request with VM0042 canonical UUID succeeds."""
    unique_email = f"agri_uuid_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "full_name": "Agri UUID User",
        "email": unique_email,
        "organization_name": "Agri UUID Co",
        "country": "Kenya",
        "sector_id": "AGRICULTURE_LAND_USE",
        "methodology_id": "ec739cc0-517a-4fa0-9ff3-ed4cc6d17667",
        "project_name": "Kenya Grassland SOC",
    }
    response = await async_client.post("/api/v1/access-requests", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"


@pytest.mark.asyncio
async def test_access_request_cross_sector_mismatch_agri_with_biochar_fails(async_client: AsyncClient):
    """Verifies access request with Agriculture sector but Biochar methodology VM0044 fails with 422."""
    unique_email = f"mismatch_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "full_name": "Mismatch User",
        "email": unique_email,
        "organization_name": "Mismatch Co",
        "country": "Global",
        "sector_id": "AGRICULTURE_LAND_USE",
        "methodology_id": "VM0044",
        "project_name": "Mismatch Project",
    }
    response = await async_client.post("/api/v1/access-requests", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "belongs to sector 'Biochar Carbon Removal'" in data["detail"]


@pytest.mark.asyncio
async def test_access_request_cross_sector_mismatch_biochar_with_agri_fails(async_client: AsyncClient):
    """Verifies access request with Biochar sector but Agriculture methodology VM0042 fails with 422."""
    unique_email = f"mismatch2_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "full_name": "Mismatch User 2",
        "email": unique_email,
        "organization_name": "Mismatch Co 2",
        "country": "Global",
        "sector_id": "BIOCHAR",
        "methodology_id": "VM0042",
        "project_name": "Mismatch Project 2",
    }
    response = await async_client.post("/api/v1/access-requests", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "belongs to sector 'Agriculture & Land Use'" in data["detail"]


@pytest.mark.asyncio
async def test_access_request_disallowed_supporting_modules_fail(async_client: AsyncClient):
    """Verifies that non-primary supporting tools/modules (VT0014, VMD0053) are rejected with 422."""
    unique_email_1 = f"tool1_{uuid.uuid4().hex[:8]}@example.com"
    payload_vt = {
        "full_name": "Tool User",
        "email": unique_email_1,
        "organization_name": "Tool Co",
        "country": "Global",
        "sector_id": "AGRICULTURE_LAND_USE",
        "methodology_id": "VT0014",
        "project_name": "Tool Project",
    }
    response_vt = await async_client.post("/api/v1/access-requests", json=payload_vt)
    assert response_vt.status_code == 422
    assert "supporting module/tool" in response_vt.json()["detail"]

    unique_email_2 = f"tool2_{uuid.uuid4().hex[:8]}@example.com"
    payload_vmd = {
        "full_name": "Tool User 2",
        "email": unique_email_2,
        "organization_name": "Tool Co 2",
        "country": "Global",
        "sector_id": "AGRICULTURE_LAND_USE",
        "methodology_id": "VMD0053",
        "project_name": "Tool Project 2",
    }
    response_vmd = await async_client.post("/api/v1/access-requests", json=payload_vmd)
    assert response_vmd.status_code == 422
    assert "supporting module/tool" in response_vmd.json()["detail"]


@pytest.mark.asyncio
async def test_access_request_unconfigured_methodology_fails(async_client: AsyncClient):
    """Verifies that unconfigured methodology codes are rejected with 422."""
    unique_email = f"unconf_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "full_name": "Unconfigured User",
        "email": unique_email,
        "organization_name": "Unconfigured Co",
        "country": "Global",
        "sector_id": "AGRICULTURE_LAND_USE",
        "methodology_id": "UNCONFIGURED_CODE_XYZ",
        "project_name": "Unconfigured Project",
    }
    response = await async_client.post("/api/v1/access-requests", json=payload)
    assert response.status_code == 422
    assert "not applicable to sector" in response.json()["detail"]
