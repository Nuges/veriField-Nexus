"""
Security & Code Correctness Tests for Digital Twins Domain (P1-08)

Verifies:
1. Intelligence engine uses state_vector instead of attributes (no AttributeError)
2. Intelligence engine queries DigitalTwinState using digital_twin_id correctly
3. Tenant A can run simulations and playback on Tenant A digital twins
4. Tenant B cannot access Tenant A digital twins (rejected with 404)
5. Super Admin can access digital twins across tenants
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
from app.domains.assets.models import Asset
from app.domains.authentication.models import User
from app.domains.digital_twins.models.twin import DigitalTwin, DigitalTwinState
from app.domains.digital_twins.services.intelligence import TwinIntelligenceEngine
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project
from app.main import app


@pytest.mark.asyncio
async def test_digital_twins_security_and_engine():
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
    super_admin = User(
        id=uuid.uuid4(),
        email=f"superadmin_{uuid.uuid4().hex[:6]}@verifield.com",
        full_name="Super Admin",
        role="SUPER_ADMIN",
        organization_id=None,
        status="active",
    )

    org_a = Organization(id=org_a_id, name=f"Tenant A {uuid.uuid4().hex[:6]}", status="ACTIVE")
    org_b = Organization(id=org_b_id, name=f"Tenant B {uuid.uuid4().hex[:6]}", status="ACTIVE")

    project_a = Project(
        id=uuid.uuid4(),
        project_code=f"PRJ-A-{uuid.uuid4().hex[:4]}",
        name="Project A",
        country="Kenya",
        organization_id=org_a_id,
    )
    asset_a = Asset(
        id=uuid.uuid4(),
        project_id=project_a.id,
        organization_id=org_a_id,
        name="Cookstove Unit A",
        status="active",
    )
    twin_a = DigitalTwin(
        id=uuid.uuid4(),
        asset_id=asset_a.id,
        twin_status="online",
        state_vector={"health_score": 95.0, "degradation_rate_per_hour": 0.1},
    )
    twin_state_a = DigitalTwinState(
        id=uuid.uuid4(),
        digital_twin_id=twin_a.id,
        timestamp=datetime.now(timezone.utc),
        state_data={"temperature": 45.0, "pressure": 1.2},
    )

    async with factory() as session:
        session.add(org_a)
        session.add(org_b)
        session.add(user_a)
        session.add(user_b)
        session.add(super_admin)
        session.add(project_a)
        session.add(asset_a)
        session.add(twin_a)
        session.add(twin_state_a)
        await session.commit()

    # -----------------------------------------------------------------
    # Direct Engine Test: verify state_vector and digital_twin_id fixes
    # -----------------------------------------------------------------
    async with factory() as session:
        engine = TwinIntelligenceEngine(session)
        # 1. run_simulation (tests twin.state_vector fix)
        sim_res = await engine.run_simulation(str(twin_a.id), forward_steps=3, step_size_minutes=60)
        assert len(sim_res) == 3
        assert "predicted_health" in sim_res[0]

        # 2. playback_history (tests digital_twin_id fix)
        history = await engine.playback_history(
            str(twin_a.id),
            start_time=datetime(2020, 1, 1, tzinfo=timezone.utc),
            end_time=datetime(2030, 1, 1, tzinfo=timezone.utc),
        )
        assert len(history) >= 1

        # 3. evaluate_failure_prediction (tests digital_twin_id fix)
        fail_res = await engine.evaluate_failure_prediction(str(twin_a.id))
        assert "status" in fail_res

    # -----------------------------------------------------------------
    # API Tenant Isolation Tests
    # -----------------------------------------------------------------
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

        # 1. Tenant A simulates own twin -> 200 OK
        app.dependency_overrides[get_current_user] = lambda: user_a
        res_sim_a = await client.post(f"/api/v1/digital-twins/{twin_a.id}/simulate?forward_steps=5")
        assert res_sim_a.status_code == 200

        # 2. Tenant B attempts to simulate Tenant A twin -> 404
        app.dependency_overrides[get_current_user] = lambda: user_b
        res_sim_b = await client.post(f"/api/v1/digital-twins/{twin_a.id}/simulate?forward_steps=5")
        assert res_sim_b.status_code == 404

        # 3. Super Admin simulates Tenant A twin -> 200 OK
        app.dependency_overrides[get_current_user] = lambda: super_admin
        res_sim_sa = await client.post(f"/api/v1/digital-twins/{twin_a.id}/simulate?forward_steps=5")
        assert res_sim_sa.status_code == 200

    app.dependency_overrides.clear()
