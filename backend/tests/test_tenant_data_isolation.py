"""
=============================================================================
VeriField Nexus — Multi-Tenant Data Isolation & Verification Suite
=============================================================================
Formally verifies:
1. Fresh Tenant Empty State:
   - Newly created ORG_ADMIN with 0 projects, 0 activities, 0 tasks.
   - GET /api/v1/verification/tasks returns 200 with empty [] (No 500 / AttributeError).
   - GET /api/v1/verification/audits returns 200 with empty [].
   - GET /api/v1/activities returns 200 with empty [].
   - GET /api/v1/projects returns 200 with empty [].
   - GET /api/v1/reporting/metrics/anomalies returns 200 with empty [].
   - Dashboard Resolver returns 0 projects, 0 activities, QA findings = "—" (NO_DATA, never 23).

2. Tenant Isolation (Tenant A vs Tenant B):
   - Tenant B possesses projects, activities, anomalies, and verification tasks.
   - Tenant A queries never leak Tenant B data across any endpoint.
   - Tenant B receives only its own data.

3. Adversarial BOLA / IDOR Protection:
   - Tenant A attempting direct access to Tenant B project -> 404 or 403.
   - Tenant A attempting direct access to Tenant B verification task -> 403 Forbidden.
   - Tenant A attempting to resolve Tenant B anomaly -> 403 Forbidden.

4. Platform Super Admin Visibility:
   - SUPER_ADMIN retains platform-wide operational authority.
=============================================================================
"""

import uuid
from datetime import datetime, timezone
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
from app.domains.projects.models import Project
from app.domains.activities.models import Activity
from app.domains.verification.models import VerificationTask
from app.domains.workspaces.services.dashboard_resolver import DashboardResolverService
from app.main import app


@pytest.mark.asyncio
async def test_fresh_tenant_empty_state_and_verification_tasks_200():
    """Verify fresh tenant has 0 data and verification endpoints return 200 with empty lists."""
    await _init_fallback_db()
    factory = _get_fallback_session_factory()

    org_fresh_id = uuid.uuid4()
    user_fresh = User(
        id=uuid.uuid4(),
        email=f"fresh_admin_{uuid.uuid4().hex[:6]}@agri-farm.org",
        full_name="Fresh Agriculture Admin",
        role="ORG_ADMIN",
        organization_id=org_fresh_id,
        status="active",
    )
    org_fresh = Organization(
        id=org_fresh_id,
        name=f"Fresh Agriculture Org {uuid.uuid4().hex[:6]}",
        status="ACTIVE",
    )

    async with factory() as session:
        session.add(org_fresh)
        session.add(user_fresh)
        await session.commit()

    async def override_get_db():
        async with factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: user_fresh

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. GET /api/v1/verification/tasks -> Must return 200, empty audits/tasks
        res_tasks = await client.get("/api/v1/verification/tasks")
        assert res_tasks.status_code == 200, f"Expected 200, got {res_tasks.status_code}: {res_tasks.text}"
        data_tasks = res_tasks.json()
        assert data_tasks.get("tasks") == []
        assert data_tasks.get("audits") == []
        assert data_tasks.get("total") == 0

        # 2. GET /api/v1/verification/audits -> Must return 200, empty audits/tasks
        res_audits = await client.get("/api/v1/verification/audits")
        assert res_audits.status_code == 200
        data_audits = res_audits.json()
        assert data_audits.get("audits") == []
        assert data_audits.get("tasks") == []
        assert data_audits.get("total") == 0

        # 3. GET /api/v1/activities -> Must return 200, 0 activities
        res_acts = await client.get("/api/v1/activities")
        assert res_acts.status_code == 200
        data_acts = res_acts.json()
        assert data_acts.get("activities") == []
        assert data_acts.get("total") == 0

        # 4. GET /api/v1/projects -> Must return 200, 0 projects
        res_projs = await client.get("/api/v1/projects")
        assert res_projs.status_code == 200
        data_projs = res_projs.json()
        assert data_projs.get("items") == []
        assert data_projs.get("total") == 0

        # 5. GET /api/v1/reporting/metrics/anomalies -> Must return 200, 0 anomalies
        res_anom = await client.get("/api/v1/reporting/metrics/anomalies")
        assert res_anom.status_code == 200
        data_anom = res_anom.json()
        assert data_anom.get("anomalies") == []
        assert data_anom.get("total") == 0

    # 6. Verify Dashboard Resolver directly for fresh tenant
    async with factory() as session:
        resolver = DashboardResolverService(session)
        dash_payload = await resolver.resolve_dashboard(
            organization_id=org_fresh_id,
            workspace_id="agriculture",
            methodology_id="VM0042",
        )
        assert dash_payload["activity_total"] == 0
        assert dash_payload["activities"] == []
        assert dash_payload["project"]["id"] is None

        # Find QA Findings KPI
        kpi_map = {k["code"]: k for k in dash_payload.get("kpis", [])}
        assert "qa_findings" in kpi_map
        qa_kpi = kpi_map["qa_findings"]
        # Empty tenant without evaluations must show neutral NO_DATA ("—"), NEVER 23!
        assert qa_kpi["value"] == "—"
        assert qa_kpi["state"] == "NO_DATA"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_multi_tenant_data_isolation_between_tenants():
    """Verify Tenant A never sees any data belonging to Tenant B."""
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
    org_a = Organization(id=org_a_id, name=f"Tenant A {uuid.uuid4().hex[:6]}", status="ACTIVE")
    org_b = Organization(id=org_b_id, name=f"Tenant B {uuid.uuid4().hex[:6]}", status="ACTIVE")

    # Seed Tenant B with: 1 Project, 2 Activities (1 flagged anomaly, 1 verified), 1 VerificationTask
    proj_b_id = uuid.uuid4()
    proj_b = Project(
        id=proj_b_id,
        organization_id=org_b_id,
        name="Tenant B Solar & Biochar Project",
    )

    act_b_verified = Activity(
        id=uuid.uuid4(),
        organization_id=org_b_id,
        user_id=user_b.id,
        property_id=proj_b_id,
        activity_type="solar_meter_telemetry",
        activity_data={"power_kw": 45.0},
        status="verified",
        trust_score=98.0,
        captured_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )

    act_b_flagged = Activity(
        id=uuid.uuid4(),
        organization_id=org_b_id,
        user_id=user_b.id,
        property_id=proj_b_id,
        activity_type="biochar_pyrolysis_batch",
        activity_data={"kiln_temp": 1200},
        status="flagged",
        trust_flags={"fraud_flag": "Suspicious thermal surge"},
        trust_score=35.0,
        captured_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )

    task_b_id = uuid.uuid4()
    task_b = VerificationTask(
        id=task_b_id,
        project_id=proj_b_id,
        verifier_id=None,
        status="ASSIGNED",
        findings={"note": "Tenant B external audit needed"},
        created_at=datetime.now(timezone.utc),
    )

    async with factory() as session:
        session.add(org_a)
        session.add(org_b)
        session.add(user_a)
        session.add(user_b)
        session.add(proj_b)
        session.add(act_b_verified)
        session.add(act_b_flagged)
        session.add(task_b)
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
        # -------------------------------------------------------------
        # TENANT A ACCESS (EMPTY TENANT) - NO DATA LEAKS
        # -------------------------------------------------------------
        app.dependency_overrides[get_current_user] = lambda: user_a

        # 1. Activities: Must NOT include Tenant B's activities
        res_a_acts = await client.get("/api/v1/activities")
        assert res_a_acts.status_code == 200
        a_act_ids = [a["id"] for a in res_a_acts.json().get("activities", [])]
        assert str(act_b_verified.id) not in a_act_ids
        assert str(act_b_flagged.id) not in a_act_ids

        # 2. Anomalies: Must NOT include Tenant B's flagged activity
        res_a_anom = await client.get("/api/v1/reporting/metrics/anomalies")
        assert res_a_anom.status_code == 200
        a_anom_ids = [a["id"] for a in res_a_anom.json().get("anomalies", [])]
        assert str(act_b_flagged.id) not in a_anom_ids

        # 3. Verification Tasks: Must NOT include Tenant B's verification task
        res_a_tasks = await client.get("/api/v1/verification/tasks")
        assert res_a_tasks.status_code == 200
        a_task_ids = [t["id"] for t in res_a_tasks.json().get("tasks", [])]
        assert str(task_b_id) not in a_task_ids

        # 4. Projects: Must NOT include Tenant B's project
        res_a_projs = await client.get("/api/v1/projects")
        assert res_a_projs.status_code == 200
        a_proj_ids = [p["id"] for p in res_a_projs.json().get("items", [])]
        assert str(proj_b_id) not in a_proj_ids

        # -------------------------------------------------------------
        # TENANT B ACCESS - GETS OWN DATA
        # -------------------------------------------------------------
        app.dependency_overrides[get_current_user] = lambda: user_b

        # 1. Tenant B activities include Tenant B's activities
        res_b_acts = await client.get("/api/v1/activities")
        assert res_b_acts.status_code == 200
        b_act_ids = [a["id"] for a in res_b_acts.json().get("activities", [])]
        assert str(act_b_verified.id) in b_act_ids
        assert str(act_b_flagged.id) in b_act_ids

        # 2. Tenant B anomalies include Tenant B's flagged activity
        res_b_anom = await client.get("/api/v1/reporting/metrics/anomalies")
        assert res_b_anom.status_code == 200
        b_anom_ids = [a["id"] for a in res_b_anom.json().get("anomalies", [])]
        assert str(act_b_flagged.id) in b_anom_ids

        # 3. Tenant B verification tasks include Tenant B's task
        res_b_tasks = await client.get("/api/v1/verification/tasks")
        assert res_b_tasks.status_code == 200
        b_task_ids = [t["id"] for t in res_b_tasks.json().get("tasks", [])]
        assert str(task_b_id) in b_task_ids

        # 4. Tenant B projects include Tenant B's project
        res_b_projs = await client.get("/api/v1/projects")
        assert res_b_projs.status_code == 200
        b_proj_ids = [p["id"] for p in res_b_projs.json().get("items", [])]
        assert str(proj_b_id) in b_proj_ids

    # 5. Check Dashboard Resolver for Tenant A
    async with factory() as session:
        resolver = DashboardResolverService(session)
        dash_a = await resolver.resolve_dashboard(
            organization_id=org_a_id,
            workspace_id="agriculture",
            methodology_id="VM0042",
        )
        assert len(dash_a["activities"]) == 0
        assert dash_a["project"]["id"] is None
        kpi_map = {k["code"]: k for k in dash_a.get("kpis", [])}
        assert kpi_map["qa_findings"]["value"] == "—"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_adversarial_cross_tenant_bola_idor_denied():
    """Verify Tenant A cannot directly access or mutate Tenant B records (BOLA / IDOR protection)."""
    await _init_fallback_db()
    factory = _get_fallback_session_factory()

    org_a_id = uuid.uuid4()
    org_b_id = uuid.uuid4()

    user_a = User(
        id=uuid.uuid4(),
        email=f"attacker_a_{uuid.uuid4().hex[:6]}@tenant-a.com",
        full_name="Attacker Tenant A",
        role="ORG_ADMIN",
        organization_id=org_a_id,
        status="active",
    )
    user_b = User(
        id=uuid.uuid4(),
        email=f"victim_b_{uuid.uuid4().hex[:6]}@tenant-b.com",
        full_name="Victim Tenant B",
        role="ORG_ADMIN",
        organization_id=org_b_id,
        status="active",
    )
    org_a = Organization(id=org_a_id, name=f"Org A {uuid.uuid4().hex[:6]}", status="ACTIVE")
    org_b = Organization(id=org_b_id, name=f"Org B {uuid.uuid4().hex[:6]}", status="ACTIVE")

    proj_b = Project(
        id=uuid.uuid4(),
        organization_id=org_b_id,
        name="Sensitive Tenant B Carbon Project",
    )
    act_b = Activity(
        id=uuid.uuid4(),
        organization_id=org_b_id,
        user_id=user_b.id,
        property_id=proj_b.id,
        activity_type="cookstove_usage",
        status="flagged",
        trust_flags={"fraud_flag": "Potential double count"},
        captured_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )
    task_b = VerificationTask(
        id=uuid.uuid4(),
        project_id=proj_b.id,
        verifier_id=None,
        status="ASSIGNED",
        findings={"secret": "Auditor proprietary analysis"},
        created_at=datetime.now(timezone.utc),
    )

    async with factory() as session:
        session.add(org_a)
        session.add(org_b)
        session.add(user_a)
        session.add(user_b)
        session.add(proj_b)
        session.add(act_b)
        session.add(task_b)
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

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Tenant A attempts to fetch Tenant B's project by ID -> 404 Not Found (or 403 Forbidden)
        res_proj = await client.get(f"/api/v1/projects/{proj_b.id}")
        assert res_proj.status_code in (403, 404), f"Expected 403 or 404, got {res_proj.status_code}"

        # 2. Tenant A attempts to fetch Tenant B's verification task by ID -> 403 Forbidden
        res_task = await client.get(f"/api/v1/verification/tasks/{task_b.id}")
        assert res_task.status_code == 403, f"Expected 403 Forbidden, got {res_task.status_code}"

        # 3. Tenant A attempts to resolve Tenant B's anomaly -> 403 Forbidden
        res_resolve = await client.post(
            f"/api/v1/reporting/metrics/anomalies/{act_b.id}/resolve?action=verify"
        )
        assert res_resolve.status_code == 403, f"Expected 403 Forbidden, got {res_resolve.status_code}"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_super_admin_cross_tenant_visibility():
    """Verify SUPER_ADMIN retains platform-wide operational authority."""
    await _init_fallback_db()
    factory = _get_fallback_session_factory()

    org_id = uuid.uuid4()
    super_admin = User(
        id=uuid.uuid4(),
        email=f"super_admin_{uuid.uuid4().hex[:6]}@verifield.com",
        full_name="Global Super Admin",
        role="SUPER_ADMIN",
        organization_id=None,
        status="active",
    )
    org = Organization(id=org_id, name=f"Org {uuid.uuid4().hex[:6]}", status="ACTIVE")
    proj = Project(
        id=uuid.uuid4(),
        organization_id=org_id,
        name="Global Admin Visible Project",
    )
    act_flagged = Activity(
        id=uuid.uuid4(),
        organization_id=org_id,
        user_id=super_admin.id,
        property_id=proj.id,
        activity_type="cookstove_usage",
        status="flagged",
        trust_flags={"fraud_flag": "Super Admin Reviewable"},
        captured_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )
    task = VerificationTask(
        id=uuid.uuid4(),
        project_id=proj.id,
        status="ASSIGNED",
        findings={"note": "Super Admin Review Task"},
        created_at=datetime.now(timezone.utc),
    )

    async with factory() as session:
        session.add(org)
        session.add(super_admin)
        session.add(proj)
        session.add(act_flagged)
        session.add(task)
        await session.commit()

    async def override_get_db():
        async with factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: super_admin

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Super Admin can view projects across tenants
        res_direct = await client.get(f"/api/v1/projects/{proj.id}")
        assert res_direct.status_code == 200
        assert res_direct.json()["id"] == str(proj.id)

        res_projs = await client.get("/api/v1/projects")
        assert res_projs.status_code == 200
        assert res_projs.json().get("total", 0) > 0

        # 2. Super Admin sees verification tasks
        res_tasks = await client.get("/api/v1/verification/tasks")
        assert res_tasks.status_code == 200
        task_ids = [t["id"] for t in res_tasks.json().get("tasks", [])]
        assert str(task.id) in task_ids

        # 3. Super Admin sees anomalies
        res_anom = await client.get("/api/v1/reporting/metrics/anomalies")
        assert res_anom.status_code == 200
        anom_ids = [a["id"] for a in res_anom.json().get("anomalies", [])]
        assert str(act_flagged.id) in anom_ids

    app.dependency_overrides.clear()
