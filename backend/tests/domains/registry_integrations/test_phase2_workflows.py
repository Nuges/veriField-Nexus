"""Isolated Phase 2 project, permission and evidence-boundary regressions."""
from uuid import uuid4
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import delete

from app.core.security import get_current_user
from app.core.rbac import CANONICAL_ROLES, has_permission
from app.domains.authentication.models import User
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project
from app.domains.assets.models import Asset
from app.domains.activities.models import Activity
from app.domains.registry_integrations.repository import project_activity_statement
from app.domains.registry_integrations.services.readiness_engine import RegistryReadinessEngine
from app.domains.reporting.services.lineage import DataLineageEngine
from app.main import app


@pytest_asyncio.fixture
async def registry_projects(db_session):
    org, foreign_org = uuid4(), uuid4()
    first, second, foreign, unowned = uuid4(), uuid4(), uuid4(), uuid4()
    user_id = uuid4()
    db_session.add_all([Organization(id=org, name=f"Registry {org}"), Organization(id=foreign_org, name=f"Registry {foreign_org}")])
    await db_session.flush()
    db_session.add_all([Project(id=first, name="Selected project", organization_id=org, country="India"),
                        Project(id=second, name="Other project", organization_id=org),
                        Project(id=foreign, name="Foreign project", organization_id=foreign_org),
                        Project(id=unowned, name="Unowned project")])
    db_session.add(User(id=user_id, email=f"registry-{user_id}@example.test", full_name="Test operator", role="ORG_ADMIN", organization_id=org, is_active=True, status="active"))
    await db_session.commit()
    try:
        yield {"org": org, "foreign_org": foreign_org, "first": first, "second": second, "foreign": foreign, "unowned": unowned, "user": user_id}
    finally:
        await db_session.rollback()
        await db_session.execute(delete(Activity).where(Activity.user_id == user_id))
        await db_session.execute(delete(Asset).where(Asset.project_id.in_([first, second, foreign, unowned])))
        await db_session.execute(delete(Project).where(Project.id.in_([first, second, foreign, unowned])))
        await db_session.execute(delete(User).where(User.id == user_id))
        await db_session.execute(delete(Organization).where(Organization.id.in_([org, foreign_org])))
        await db_session.commit()


def actor(scope, role="ORG_ADMIN", organization=True):
    return User(id=scope["user"], email="phase2@example.test", full_name="Operator", role=role,
                organization_id=scope["org"] if organization else None, status="active", is_active=True)


@pytest.mark.asyncio
@pytest.mark.parametrize("prefix", ["registry", "registry-integrations"])
@pytest.mark.parametrize("role", sorted(CANONICAL_ROLES))
async def test_existing_registry_read_permission_for_all_roles(async_client, registry_projects, role, prefix):
    async def current_actor(): return actor(registry_projects, role)
    app.dependency_overrides[get_current_user] = current_actor
    try:
        response = await async_client.get(f"/api/v1/{prefix}/document-matrix")
        assert response.status_code == (200 if has_permission(role, "registry:read") else 403), response.text
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
@pytest.mark.parametrize("prefix", ["registry", "registry-integrations"])
@pytest.mark.parametrize("resource", ["readiness/{project}", "dossier/VERRA/{project}", "package-download/VERRA/{project}", "documents/VERRA/{project}/VCS_PROJECT_DESCRIPTION?format=json"])
@pytest.mark.parametrize("target", ["foreign", "unowned"])
async def test_project_boundary_before_readers_and_downloads(async_client, registry_projects, prefix, resource, target):
    async def current_actor(): return actor(registry_projects)
    app.dependency_overrides[get_current_user] = current_actor
    try:
        response = await async_client.get(f"/api/v1/{prefix}/" + resource.format(project=registry_projects[target]))
        assert response.status_code == 403, response.text
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["document-matrix", "readiness/{project}", "package-download/VERRA/{project}", "dossier/VERRA/{project}", "documents/VERRA/{project}/DOC?format=json"])
async def test_anonymous_registry_workflow_is_rejected(async_client, registry_projects, path):
    response = await async_client.get("/api/v1/registry/" + path.format(project=registry_projects["first"]))
    assert response.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["document-matrix", "readiness/{project}", "package-download/VERRA/{project}", "dossier/VERRA/{project}", "documents/VERRA/{project}/DOC?format=json"])
async def test_viewer_cannot_operate_registry_read_routes(async_client, registry_projects, path):
    async def current_actor(): return actor(registry_projects, "VIEWER")
    app.dependency_overrides[get_current_user] = current_actor
    try:
        response = await async_client.get("/api/v1/registry/" + path.format(project=registry_projects["first"]))
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_empty_project_never_borrows_another_projects_activity(db_session, registry_projects):
    scope = registry_projects
    db_session.add(Activity(id=uuid4(), organization_id=scope["org"], user_id=scope["user"],
                            project_id=scope["second"], activity_type="SOIL_SENSOR_TELEMETRY",
                            activity_data={"temperature_c": 30}, trust_score=95, captured_at=datetime.now(timezone.utc)))
    await db_session.commit()
    readiness = await RegistryReadinessEngine(db_session).evaluate_readiness(scope["first"])
    lineage = await DataLineageEngine(db_session).get_project_data_lineage(scope["first"])
    assert "ZERO_ACTIVITY_DATA" in readiness["blocking_items"]
    assert "METHODOLOGY_UNLINKED" in readiness["blocking_items"]
    assert lineage["summary_metrics"]["total_activities_processed"] == 0
    assert lineage["summary_metrics"]["total_emission_reductions_tco2e"] == 0
    project = await db_session.get(Project, scope["first"])
    assert project.methodology_id is None


@pytest.mark.asyncio
async def test_explicit_project_and_legacy_asset_records_are_scoped(db_session, registry_projects):
    scope = registry_projects
    asset_id = uuid4()
    db_session.add(Asset(id=asset_id, project_id=scope["first"], organization_id=scope["org"], name="Selected asset"))
    await db_session.flush()
    ids = [uuid4() for _ in range(5)]
    for record_id, project_id, organization_id, linked_asset in [
        (ids[0], scope["first"], scope["org"], None),
        (ids[1], None, scope["org"], asset_id),
        (ids[2], scope["second"], scope["org"], asset_id),
        (ids[3], None, scope["org"], None),
        (ids[4], scope["first"], scope["foreign_org"], None),
    ]:
        db_session.add(Activity(id=record_id, organization_id=organization_id, user_id=scope["user"], project_id=project_id,
                                asset_id=linked_asset, activity_type="SOIL_SENSOR_TELEMETRY", activity_data={"temperature_c": 29}, captured_at=datetime.now(timezone.utc)))
    await db_session.commit()
    result = await db_session.execute(project_activity_statement(scope["first"], scope["org"], [asset_id]))
    assert {record.id for record in result.scalars()} == {ids[0], ids[1]}
    lineage = await DataLineageEngine(db_session).get_project_data_lineage(scope["first"])
    assert lineage["summary_metrics"]["total_activities_processed"] == 2
    assert lineage["summary_metrics"]["total_emission_reductions_tco2e"] == 0
