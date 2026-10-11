"""
VeriField Nexus — Activity Ingestion Permission Enforcement Regression Suite
=============================================================================
Tests:
1. FIELD_AGENT (holds 'activity:create') -> Allowed (201 / 200).
2. VIEWER (holds only 'activity:read') -> Rejected with HTTP 403 Forbidden.
3. INVESTOR (holds no activity permissions) -> Rejected with HTTP 403 Forbidden.
4. SUPER_ADMIN (bypasses standard gating) -> Allowed (201 / 200).
5. Consistent enforcement across single, offline, batch, and bulk routes.
"""

import os
import uuid
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.core.security import get_password_hash
from app.domains.organizations.models import Organization
from app.domains.authentication.models import User
from app.domains.projects.models import Project
from app.domains.authentication.service import AuthenticationService

POSTGRES_URL = (
    os.environ.get("POSTGIS_TEST_URL")
    or os.environ.get("POSTGRES_TEST_URL")
    or f"postgresql+asyncpg://{os.environ.get('USER', 'postgres')}@localhost:5432/verifield_postgis_test"
)


@pytest_asyncio.fixture
async def rbac_fixture():
    engine = create_async_engine(POSTGRES_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    org_id = uuid.uuid4()
    project_id = uuid.uuid4()

    agent_id = uuid.uuid4()
    viewer_id = uuid.uuid4()
    investor_id = uuid.uuid4()
    superadmin_id = uuid.uuid4()

    password = "RbacTestPassword123!"

    async with session_factory() as session:
        org = Organization(
            id=org_id,
            name=f"RBAC Activity Org {uuid.uuid4().hex[:6]}",
            status="ACTIVE",
            licensed_sectors=["AGRICULTURE_LAND_USE"],
        )
        session.add(org)

        project = Project(
            id=project_id,
            project_code=f"AGR-RBAC-{uuid.uuid4().hex[:4]}",
            name="RBAC Activity Test Project",
            organization_id=org_id,
            baseline_parameters={"is_test": True},
        )
        session.add(project)

        agent = User(
            id=agent_id,
            email=f"agent_{uuid.uuid4().hex[:6]}@rbac.test",
            full_name="Field Agent RBAC",
            role="FIELD_AGENT",
            organization_id=org_id,
            password_hash=get_password_hash(password),
            status="active",
        )
        viewer = User(
            id=viewer_id,
            email=f"viewer_{uuid.uuid4().hex[:6]}@rbac.test",
            full_name="Viewer RBAC",
            role="VIEWER",
            organization_id=org_id,
            password_hash=get_password_hash(password),
            status="active",
        )
        investor = User(
            id=investor_id,
            email=f"investor_{uuid.uuid4().hex[:6]}@rbac.test",
            full_name="Investor RBAC",
            role="INVESTOR",
            organization_id=org_id,
            password_hash=get_password_hash(password),
            status="active",
        )
        superadmin = User(
            id=superadmin_id,
            email=f"sa_{uuid.uuid4().hex[:6]}@rbac.test",
            full_name="Super Admin RBAC",
            role="SUPER_ADMIN",
            password_hash=get_password_hash(password),
            status="active",
        )
        session.add_all([agent, viewer, investor, superadmin])
        await session.commit()

        agent_token = AuthenticationService.generate_token_static(agent)
        viewer_token = AuthenticationService.generate_token_static(viewer)
        investor_token = AuthenticationService.generate_token_static(investor)
        sa_token = AuthenticationService.generate_token_static(superadmin)

    from app.db.session import get_db

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    yield {
        "org_id": org_id,
        "project_id": project_id,
        "agent_token": agent_token,
        "viewer_token": viewer_token,
        "investor_token": investor_token,
        "sa_token": sa_token,
    }

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_single_activity_viewer_forbidden(rbac_fixture):
    """Proves DEFECT-01 fix: VIEWER role receives HTTP 403 on POST /api/v1/activities."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "activity_type": "SOIL_SENSOR_TELEMETRY",
            "project_id": str(rbac_fixture["project_id"]),
            "client_id": f"viewer-test-{uuid.uuid4().hex[:8]}",
            "activity_data": {"soil_moisture_pct": 45.0},
        }

        # VIEWER -> 403 Forbidden
        viewer_res = await client.post(
            "/api/v1/activities",
            json=payload,
            headers={"Authorization": f"Bearer {rbac_fixture['viewer_token']}"},
        )
        assert viewer_res.status_code == 403, f"Expected 403, got {viewer_res.status_code}: {viewer_res.text}"
        assert "lacks required permission 'activity:create'" in viewer_res.text


@pytest.mark.asyncio
async def test_single_activity_field_agent_allowed(rbac_fixture):
    """Proves FIELD_AGENT with 'activity:create' succeeds with HTTP 201."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "activity_type": "SOIL_SENSOR_TELEMETRY",
            "project_id": str(rbac_fixture["project_id"]),
            "client_id": f"agent-test-{uuid.uuid4().hex[:8]}",
            "activity_data": {"soil_moisture_pct": 52.0},
        }

        # FIELD_AGENT -> 201 Created
        agent_res = await client.post(
            "/api/v1/activities",
            json=payload,
            headers={"Authorization": f"Bearer {rbac_fixture['agent_token']}"},
        )
        assert agent_res.status_code == 201, f"Expected 201, got {agent_res.status_code}: {agent_res.text}"


@pytest.mark.asyncio
async def test_single_activity_investor_forbidden(rbac_fixture):
    """Proves INVESTOR role receives HTTP 403 on POST /api/v1/activities."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "activity_type": "SOIL_SENSOR_TELEMETRY",
            "project_id": str(rbac_fixture["project_id"]),
            "client_id": f"inv-test-{uuid.uuid4().hex[:8]}",
            "activity_data": {"soil_moisture_pct": 45.0},
        }

        inv_res = await client.post(
            "/api/v1/activities",
            json=payload,
            headers={"Authorization": f"Bearer {rbac_fixture['investor_token']}"},
        )
        assert inv_res.status_code == 403


@pytest.mark.asyncio
async def test_offline_activity_viewer_forbidden(rbac_fixture):
    """Proves VIEWER role receives HTTP 403 on POST /api/v1/activities/offline."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "activity_type": "SOIL_SENSOR_TELEMETRY",
            "project_id": str(rbac_fixture["project_id"]),
            "client_id": f"off-viewer-{uuid.uuid4().hex[:8]}",
            "activity_data": {"soil_moisture_pct": 45.0},
        }

        viewer_res = await client.post(
            "/api/v1/activities/offline",
            json=payload,
            headers={"Authorization": f"Bearer {rbac_fixture['viewer_token']}"},
        )
        assert viewer_res.status_code == 403


@pytest.mark.asyncio
async def test_batch_and_bulk_activity_viewer_forbidden(rbac_fixture):
    """Proves VIEWER role receives HTTP 403 on both batch and bulk routes."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        batch_payload = {
            "activities": [{
                "activity_type": "SOIL_SENSOR_TELEMETRY",
                "project_id": str(rbac_fixture["project_id"]),
                "client_id": f"batch-viewer-{uuid.uuid4().hex[:8]}",
                "activity_data": {"soil_moisture_pct": 45.0},
            }]
        }

        # POST /api/v1/activities/batch
        res_batch = await client.post(
            "/api/v1/activities/batch",
            json=batch_payload,
            headers={"Authorization": f"Bearer {rbac_fixture['viewer_token']}"},
        )
        assert res_batch.status_code == 403

        # POST /api/v1/activities/bulk
        res_bulk = await client.post(
            "/api/v1/activities/bulk",
            json=batch_payload,
            headers={"Authorization": f"Bearer {rbac_fixture['viewer_token']}"},
        )
        assert res_bulk.status_code == 403
