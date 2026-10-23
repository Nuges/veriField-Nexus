"""
Phase 1 Security & Tenant Isolation Tests for /api/v1/audits/* and /api/v1/verification/*
==========================================================================================
Verifies:
1. Anonymous requests to /api/v1/audits and /api/v1/verification endpoints are rejected (401).
2. Authenticated Super Admin requests succeed with 200 OK.
3. Role-based access control enforces permissions: users without audit permissions are rejected (403).
4. Cross-tenant isolation: Tenant-scoped users only see tasks and data within their organization.
"""

from uuid import UUID, uuid4
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete

from app.core.security import get_current_user
from app.domains.authentication.models import User
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project
from app.domains.verification.models import VerificationTask
from app.main import app


@pytest.mark.asyncio
async def test_audit_endpoints_anonymous_rejection(async_client: AsyncClient):
    """Anonymous requests to /api/v1/audits/* and /api/v1/verification/* must be rejected with 401."""
    # 1. GET /api/v1/audits
    res = await async_client.get("/api/v1/audits")
    assert res.status_code == 401, f"Expected 401 for anonymous /api/v1/audits, got {res.status_code}"

    # 2. GET /api/v1/audits/
    res = await async_client.get("/api/v1/audits/")
    assert res.status_code == 401, f"Expected 401 for anonymous /api/v1/audits/, got {res.status_code}"

    # 3. GET /api/v1/audits/tasks
    res = await async_client.get("/api/v1/audits/tasks")
    assert res.status_code == 401, f"Expected 401 for anonymous /api/v1/audits/tasks, got {res.status_code}"

    # 4. GET /api/v1/audits/packages
    res = await async_client.get("/api/v1/audits/packages")
    assert res.status_code == 401, f"Expected 401 for anonymous /api/v1/audits/packages, got {res.status_code}"

    # 5. POST /api/v1/audits/packages/compile
    res = await async_client.post("/api/v1/audits/packages/compile", json={"project_id": str(uuid4())})
    assert res.status_code == 401, f"Expected 401 for anonymous /api/v1/audits/packages/compile, got {res.status_code}"

    # 6. Canonical /api/v1/verification/packages
    res = await async_client.get("/api/v1/verification/packages")
    assert res.status_code == 401, f"Expected 401 for anonymous /api/v1/verification/packages, got {res.status_code}"


@pytest.mark.asyncio
async def test_audit_endpoints_authorized_super_admin(
    async_client: AsyncClient, admin_token_headers: dict
):
    """Super Admin should have global access to /api/v1/audits and /api/v1/verification."""
    # 1. GET /api/v1/audits with admin headers
    res = await async_client.get("/api/v1/audits", headers=admin_token_headers)
    assert res.status_code == 200, f"Expected 200 for admin /api/v1/audits, got {res.status_code}: {res.text}"
    data = res.json()
    assert "tasks" in data or "audits" in data

    # 2. GET /api/v1/verification/packages with admin headers
    res = await async_client.get("/api/v1/verification/packages", headers=admin_token_headers)
    assert res.status_code == 200, f"Expected 200 for admin /api/v1/verification/packages, got {res.status_code}: {res.text}"
    assert isinstance(res.json(), list)


@pytest.mark.asyncio
async def test_audit_rbac_permission_enforcement(async_client: AsyncClient):
    """Users without required permission (e.g. VIEWER without audit:write) must receive 403 Forbidden on mutations."""
    viewer_user = User(
        id=UUID("00000000-0000-0000-0000-000000000099"),
        email="viewer@test.org",
        full_name="Viewer User",
        role="VIEWER",
        organization_id=UUID("00000000-0000-0000-0000-000000000010"),
        status="active",
        is_active=True,
    )

    async def override_viewer():
        return viewer_user

    app.dependency_overrides[get_current_user] = override_viewer
    try:
        # Viewer attempting mutation: POST /api/v1/verification/tasks
        payload = {"project_id": str(uuid4()), "status": "ASSIGNED"}
        res = await async_client.post(
            "/api/v1/verification/tasks",
            json=payload,
            headers={"Authorization": "Bearer VIEWER_TOKEN"},
        )
        assert res.status_code == 403, f"Expected 403 for unauthorized role, got {res.status_code}: {res.text}"

        # Viewer attempting mutation via duplicate /api/v1/audits
        res = await async_client.post(
            "/api/v1/audits/tasks",
            json=payload,
            headers={"Authorization": "Bearer VIEWER_TOKEN"},
        )
        assert res.status_code == 403, f"Expected 403 for unauthorized role via /audits, got {res.status_code}: {res.text}"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture
async def scoped_tasks(db_session):
    """Seed both permitted and forbidden records so an empty response cannot pass."""
    org_a, org_b = uuid4(), uuid4()
    project_a, project_b = uuid4(), uuid4()
    user_id = uuid4()
    own_id, foreign_id, assigned_id = uuid4(), uuid4(), uuid4()
    db_session.add_all([
        Organization(id=org_a, name=f"Audit scope A {org_a}"),
        Organization(id=org_b, name=f"Audit scope B {org_b}"),
    ])
    await db_session.flush()
    db_session.add_all([
        Project(id=project_a, name="Own audit project", organization_id=org_a),
        Project(id=project_b, name="Foreign audit project", organization_id=org_b),
    ])
    await db_session.flush()
    db_session.add_all([
        VerificationTask(id=own_id, project_id=project_a, status="ASSIGNED", findings=[]),
        VerificationTask(id=foreign_id, project_id=project_b, status="ASSIGNED", findings=[]),
        VerificationTask(id=assigned_id, project_id=project_b, verifier_id=user_id, status="ASSIGNED", findings=[]),
    ])
    await db_session.commit()
    try:
        yield {"org_id": org_a, "user_id": user_id, "own_id": own_id,
               "foreign_id": foreign_id, "assigned_id": assigned_id}
    finally:
        await db_session.execute(delete(VerificationTask).where(VerificationTask.id.in_([own_id, foreign_id, assigned_id])))
        await db_session.execute(delete(Project).where(Project.id.in_([project_a, project_b])))
        await db_session.execute(delete(Organization).where(Organization.id.in_([org_a, org_b])))
        await db_session.commit()


@pytest.mark.asyncio
@pytest.mark.parametrize("prefix", ["/api/v1/audits", "/api/v1/verification"])
@pytest.mark.parametrize("suffix", ["", "/", "/tasks", "/audits"])
async def test_audit_tenant_scoping_filtering(async_client: AsyncClient, scoped_tasks, prefix, suffix):
    """Both route families include own/assigned tasks and exclude foreign tasks."""
    tenant_user = User(
        id=scoped_tasks["user_id"],
        email="admin@tenant1.org",
        full_name="Tenant 1 Admin",
        role="ORG_ADMIN",
        organization_id=scoped_tasks["org_id"],
        status="active",
        is_active=True,
    )

    async def override_tenant_user():
        return tenant_user

    app.dependency_overrides[get_current_user] = override_tenant_user
    try:
        res = await async_client.get(
            f"{prefix}{suffix}",
            headers={"Authorization": "Bearer TENANT_TOKEN"},
        )
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        data = res.json()
        visible_ids = {item["id"] for item in data["tasks"]}
        assert visible_ids == {str(scoped_tasks["own_id"]), str(scoped_tasks["assigned_id"])}
        assert str(scoped_tasks["foreign_id"]) not in visible_ids
        assert data["total"] == 2
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
@pytest.mark.parametrize("prefix", ["/api/v1/audits", "/api/v1/verification"])
async def test_audit_user_without_org_sees_only_assigned_tasks(async_client, scoped_tasks, prefix):
    user = User(id=scoped_tasks["user_id"], email="verifier@test.org", full_name="Verifier",
                role="VERIFIER", organization_id=None, status="active", is_active=True)

    async def override_user():
        return user

    app.dependency_overrides[get_current_user] = override_user
    try:
        response = await async_client.get(f"{prefix}/tasks", headers={"Authorization": "Bearer TEST_TOKEN"})
        assert response.status_code == 200, response.text
        assert {item["id"] for item in response.json()["tasks"]} == {str(scoped_tasks["assigned_id"])}
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_audit_super_admin_sees_both_tenants(async_client, scoped_tasks, admin_token_headers):
    response = await async_client.get("/api/v1/audits/tasks", headers=admin_token_headers)
    assert response.status_code == 200, response.text
    visible_ids = {item["id"] for item in response.json()["tasks"]}
    assert {str(scoped_tasks[key]) for key in ("own_id", "foreign_id", "assigned_id")} <= visible_ids
