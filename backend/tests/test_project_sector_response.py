"""Field clients receive the persisted sector on both list and detail responses."""
from uuid import uuid4
import pytest
from sqlalchemy import select
from app.domains.methodologies.models.base_registry import MethodologyFamily
from app.domains.projects.models import Project
from app.domains.organizations.models import Organization

@pytest.mark.asyncio
async def test_five_sector_project_list_and_detail_contract(async_client, admin_token_headers, db_session):
    codes = ["COOKSTOVES", "HYBRID_ENERGY", "BIOCHAR", "EV_MOBILITY", "AGRICULTURE_LAND_USE"]
    org = Organization(id=uuid4(), name=f"Field contract {uuid4().hex[:6]}", licensed_sectors=codes, status="ACTIVE")
    db_session.add(org)
    expected = {}
    for code in codes:
        family = (await db_session.execute(select(MethodologyFamily).where(MethodologyFamily.code == code))).scalar_one_or_none()
        if family is None:
            family = MethodologyFamily(id=uuid4(), code=code, name=code, is_active=True)
            db_session.add(family)
            await db_session.flush()
        project = Project(id=uuid4(), name=f"{code} field project", organization_id=org.id, sector_id=family.id, baseline_parameters={})
        db_session.add(project)
        expected[str(project.id)] = (code, str(family.id))
    await db_session.commit()
    response = await async_client.get("/api/v1/projects", headers=admin_token_headers)
    assert response.status_code == 200, response.text
    items = {p["id"]: p for p in response.json()["items"]}
    for project_id, (sector_code, sector_id) in expected.items():
        assert items[project_id]["sector"] == sector_code
        assert items[project_id]["sector_id"] == sector_id
        assert items[project_id]["methodology_id"] is None
        detail = await async_client.get(f"/api/v1/projects/{project_id}", headers=admin_token_headers)
        assert detail.status_code == 200, detail.text
        assert detail.json()["sector"] == sector_code
        assert detail.json()["sector_id"] == sector_id
        assert detail.json()["methodology_id"] is None

@pytest.mark.asyncio
async def test_legacy_sector_is_read_from_linked_methodology_without_assigning_a_method(async_client, admin_token_headers, db_session):
    from app.domains.methodologies.models.base_registry import Methodology
    methodology = (await db_session.execute(select(Methodology).limit(1))).scalar_one()
    family = await db_session.get(MethodologyFamily, methodology.family_id)
    legacy = Project(id=uuid4(), name="Legacy linked project", methodology_id=methodology.id, sector_id=None, baseline_parameters={})
    unconfigured = Project(id=uuid4(), name="Farm name is not a sector assignment", methodology_id=None, sector_id=None, baseline_parameters={})
    db_session.add_all([legacy, unconfigured])
    await db_session.commit()
    linked = await async_client.get(f"/api/v1/projects/{legacy.id}", headers=admin_token_headers)
    assert linked.status_code == 200, linked.text
    assert linked.json()["sector"] == family.code
    assert linked.json()["methodology_code"] == methodology.code
    await db_session.refresh(legacy)
    assert legacy.sector_id is None  # Presentation did not mutate stored assignments.
    unknown = await async_client.get(f"/api/v1/projects/{unconfigured.id}", headers=admin_token_headers)
    assert unknown.status_code == 200, unknown.text
    assert unknown.json()["sector"] is None
    assert unknown.json()["methodology_id"] is None
