from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_verification_lifecycle(
    async_client: AsyncClient, admin_token_headers: dict
):
    # We use raw UUIDs for foreign keys in this test
    project_id = str(uuid4())
    org_id = str(uuid4())

    # 1. Create Verification Task
    payload = {"project_id": project_id, "status": "ASSIGNED"}

    resp = await async_client.post(
        "/api/v1/verification/tasks", json=payload, headers=admin_token_headers
    )
    assert resp.status_code == 201, resp.text
    task = resp.json()
    task_id = task["id"]

    assert task["status"] == "ASSIGNED"

    # 2. Get Verification Task
    get_resp = await async_client.get(
        f"/api/v1/verification/tasks/{task_id}", headers=admin_token_headers
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == task_id

    # 3. Submit Audit Report
    audit_payload = {
        "project_id": project_id,
        "vvb_org_id": org_id,
        "report_uri": "s3://nexus-bucket/audits/report-123.pdf",
        "report_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "is_positive_opinion": True,
    }

    audit_resp = await async_client.post(
        "/api/v1/verification/audits", json=audit_payload, headers=admin_token_headers
    )
    assert audit_resp.status_code == 201, audit_resp.text
    assert audit_resp.json()["is_positive_opinion"]


@pytest.mark.asyncio
async def test_community_feed_and_audits_endpoints(
    async_client: AsyncClient, admin_token_headers: dict
):
    # 1. Test Community Feed (no 500 error, returns 200 OK with valid list)
    comm_resp = await async_client.get("/api/v1/community")
    assert comm_resp.status_code == 200
    comm_data = comm_resp.json()
    assert "posts" in comm_data
    assert isinstance(comm_data["posts"], list)

    # 2. Test Audits list endpoint for mobile app
    audits_resp = await async_client.get("/api/v1/audits", headers=admin_token_headers)
    assert audits_resp.status_code == 200
    audits_data = audits_resp.json()
    assert "audits" in audits_data
    assert isinstance(audits_data["audits"], list)


@pytest.mark.asyncio
async def test_verification_packages_no_route_collision_and_canonical_contract(
    async_client: AsyncClient, admin_token_headers: dict
):
    """
    Formally verifies:
    1. GET /api/v1/verification/packages returns HTTP 200 (NOT HTTP 422).
       Eliminates route collision where /packages was captured by /{task_id}.
    2. GET /api/v1/verification/tasks returns canonical envelope:
       {"tasks": [...], "audits": [...], "total": int, "page": 1, "per_page": 50}.
    3. GET /api/v1/verification/tasks/{task_id} and legacy GET /api/v1/verification/{task_id}
       both resolve successfully without collision.
    """
    # 1. Verification Packages endpoint must return 200 list (not 422 UUID parsing error)
    resp_pkgs = await async_client.get(
        "/api/v1/verification/packages", headers=admin_token_headers
    )
    assert resp_pkgs.status_code == 200, f"Expected 200, got {resp_pkgs.status_code}: {resp_pkgs.text}"
    pkgs_data = resp_pkgs.json()
    assert isinstance(pkgs_data, list), f"Expected list of packages, got {type(pkgs_data)}"

    # 2. Canonical tasks contract
    resp_tasks = await async_client.get(
        "/api/v1/verification/tasks", headers=admin_token_headers
    )
    assert resp_tasks.status_code == 200, resp_tasks.text
    tasks_envelope = resp_tasks.json()
    assert "tasks" in tasks_envelope, "Response must include canonical 'tasks' field"
    assert "audits" in tasks_envelope, "Response must include backward-compatible 'audits' alias"
    assert "total" in tasks_envelope, "Response must include 'total' count"
    assert isinstance(tasks_envelope["tasks"], list)
    assert isinstance(tasks_envelope["audits"], list)
    assert isinstance(tasks_envelope["total"], int)

    # 3. Create a task and verify both canonical /tasks/{id} and fallback /{id} resolve
    new_task_payload = {"project_id": str(uuid4()), "status": "IN_PROGRESS"}
    create_resp = await async_client.post(
        "/api/v1/verification/tasks", json=new_task_payload, headers=admin_token_headers
    )
    assert create_resp.status_code == 201, create_resp.text
    created_id = create_resp.json()["id"]

    # Explicit namespaced route
    get_namespaced = await async_client.get(
        f"/api/v1/verification/tasks/{created_id}", headers=admin_token_headers
    )
    assert get_namespaced.status_code == 200
    assert get_namespaced.json()["id"] == created_id

    # Legacy dynamic route fallback
    get_legacy = await async_client.get(
        f"/api/v1/verification/{created_id}", headers=admin_token_headers
    )
    assert get_legacy.status_code == 200
    assert get_legacy.json()["id"] == created_id


@pytest.mark.asyncio
async def test_verification_packages_strict_tenant_isolation():
    """
    Formally verifies:
    An ORG_ADMIN cannot access verification packages belonging to another organization.
    Cross-tenant queries fail closed.
    """
    from datetime import date
    from app.core.security import get_current_user
    from app.db.session import _get_fallback_session_factory, _init_fallback_db, get_db
    from app.domains.authentication.models import User
    from app.domains.organizations.models import Organization
    from app.domains.projects.models import Project
    from app.domains.verification.models import VerificationPackage
    from app.main import app
    from httpx import ASGITransport

    await _init_fallback_db()
    factory = _get_fallback_session_factory()

    org_a_id = uuid4()
    org_b_id = uuid4()

    user_a = User(
        id=uuid4(),
        email=f"org_a_admin_{uuid4().hex[:6]}@domain.org",
        full_name="Org A Admin",
        role="ORG_ADMIN",
        organization_id=org_a_id,
        status="active",
    )
    user_b = User(
        id=uuid4(),
        email=f"org_b_admin_{uuid4().hex[:6]}@domain.org",
        full_name="Org B Admin",
        role="ORG_ADMIN",
        organization_id=org_b_id,
        status="active",
    )

    org_a = Organization(id=org_a_id, name=f"Org A {uuid4().hex[:6]}", status="ACTIVE")
    org_b = Organization(id=org_b_id, name=f"Org B {uuid4().hex[:6]}", status="ACTIVE")

    proj_b = Project(
        id=uuid4(),
        organization_id=org_b_id,
        name=f"Project B {uuid4().hex[:6]}",
    )

    pkg_b = VerificationPackage(
        id=uuid4(),
        project_id=proj_b.id,
        organization_id=org_b_id,
        monitoring_period_start=date(2026, 1, 1),
        monitoring_period_end=date(2026, 6, 30),
        package_name="Tenant B Biochar Verification Dossier",
        package_version=1,
        package_status="READY_FOR_AUDIT",
        registry_target="PURO_STANDARD",
        audit_type="OUTPUT_AUDIT",
        manifest_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        manifest_json={},
    )

    async with factory() as session:
        session.add_all([org_a, org_b, user_a, user_b, proj_b, pkg_b])
        await session.commit()

    async def override_get_db():
        async with factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: user_a

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # Org A queries packages -> must be empty (cannot see Org B's package)
            res = await client.get("/api/v1/verification/packages")
            assert res.status_code == 200
            pkgs = res.json()
            assert isinstance(pkgs, list)
            assert len(pkgs) == 0, f"Expected 0 packages for Org A, got {len(pkgs)}"

            # Org A attempts to filter by Org B's project_id -> must fail closed (return 0 packages)
            res_cross = await client.get(f"/api/v1/verification/packages?project_id={proj_b.id}")
            assert res_cross.status_code == 200
            cross_pkgs = res_cross.json()
            assert len(cross_pkgs) == 0, "Cross-tenant query must return 0 packages"
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)
