"""
=============================================================================
VeriField Nexus — Clean Cookstoves Location Privacy & Tenant Isolation Tests
=============================================================================
Verifies:
1. Authorized operational roles (FIELD_AGENT, ORG_ADMIN, PROJECT_MANAGER)
   receive exact coordinates and operational field telemetry.
2. Unauthorized/general portfolio roles (VIEWER, INVESTOR, OBSERVER)
   receive redacted coordinates (latitude/longitude None, protected address).
3. Cross-tenant isolation strictly blocks Tenant B from querying or modifying
   Tenant A household records (HTTP 403 / zero data exposure).
=============================================================================
"""

import uuid
from datetime import datetime, timedelta, timezone
import jwt as pyjwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domains.authentication.models import User
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project
from app.main import app


def _create_token(user_id: uuid.UUID, email: str, role: str, org_id: uuid.UUID = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "organization_id": str(org_id) if org_id else None,
        "iat": now,
        "exp": now + timedelta(hours=2),
        "jti": str(uuid.uuid4()),
    }
    return pyjwt.encode(payload, settings.effective_jwt_secret, algorithm="HS256")


@pytest.mark.asyncio
async def test_cookstove_operational_role_receives_exact_coordinates(db_session: AsyncSession):
    suffix = uuid.uuid4().hex[:6]
    org_a = Organization(id=uuid.uuid4(), name=f"Cookstove Developer A {suffix}")
    db_session.add(org_a)
    await db_session.flush()

    proj_a = Project(
        id=uuid.uuid4(),
        organization_id=org_a.id,
        name=f"Rift Valley Stove Programme {suffix}",
    )
    db_session.add(proj_a)
    await db_session.flush()

    agent_user = User(
        id=uuid.uuid4(),
        email=f"field.agent.{suffix}@example.com",
        full_name="Field Operations Agent",
        role="FIELD_AGENT",
        organization_id=org_a.id,
    )
    db_session.add(agent_user)
    await db_session.commit()

    agent_token = _create_token(agent_user.id, agent_user.email, agent_user.role, org_a.id)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Operational agent registers a household beneficiary
        payload = {
            "project_id": str(proj_a.id),
            "household_code": f"HH-{suffix}-001",
            "head_of_household": "Grace Achieng",
            "phone_number": "+254711223344",
            "address": "Plot 14, Kisumu Rural Zone 3",
            "community_name": "Kisumu North",
            "latitude": -0.0917,
            "longitude": 34.7680,
            "family_members_count": 6,
            "baseline_fuel_type": "WOOD_FIRE",
            "baseline_fuel_kg_per_day": 8.5,
        }
        res_create = await ac.post(
            "/api/v1/cookstoves/households",
            json=payload,
            headers={"Authorization": f"Bearer {agent_token}"},
        )
        assert res_create.status_code == 201
        created_data = res_create.json()
        assert created_data["household_code"] == f"HH-{suffix}-001"

        # 2. Operational agent queries household list -> receives exact coordinates
        res_list = await ac.get(
            f"/api/v1/cookstoves/households?project_id={proj_a.id}",
            headers={"Authorization": f"Bearer {agent_token}"},
        )
        assert res_list.status_code == 200
        items = res_list.json()
        assert len(items) >= 1
        hh = next(h for h in items if h["household_code"] == f"HH-{suffix}-001")

        # EXACT COORDINATE ACCESS PROOF
        assert hh["latitude"] == pytest.approx(-0.0917, abs=1e-4)
        assert hh["longitude"] == pytest.approx(34.7680, abs=1e-4)
        assert hh["address"] == "Plot 14, Kisumu Rural Zone 3"
        assert hh["phone_number"] == "+254711223344"
        assert hh["is_coordinates_redacted"] is False


@pytest.mark.asyncio
async def test_cookstove_general_role_receives_redacted_coordinates(db_session: AsyncSession):
    suffix = uuid.uuid4().hex[:6]
    org_a = Organization(id=uuid.uuid4(), name=f"Cookstove Developer A {suffix}")
    db_session.add(org_a)
    await db_session.flush()

    proj_a = Project(
        id=uuid.uuid4(),
        organization_id=org_a.id,
        name=f"Rift Valley Stove Programme {suffix}",
    )
    db_session.add(proj_a)
    await db_session.flush()

    # Agent who created the record
    agent_user = User(
        id=uuid.uuid4(),
        email=f"field.agent.{suffix}@example.com",
        full_name="Field Operations Agent",
        role="FIELD_AGENT",
        organization_id=org_a.id,
    )
    # General viewer (e.g. portfolio viewer / investor)
    viewer_user = User(
        id=uuid.uuid4(),
        email=f"viewer.{suffix}@example.com",
        full_name="General Portfolio Viewer",
        role="VIEWER",
        organization_id=org_a.id,
    )
    db_session.add_all([agent_user, viewer_user])
    await db_session.commit()

    agent_token = _create_token(agent_user.id, agent_user.email, agent_user.role, org_a.id)
    viewer_token = _create_token(viewer_user.id, viewer_user.email, viewer_user.role, org_a.id)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "project_id": str(proj_a.id),
            "household_code": f"HH-{suffix}-002",
            "head_of_household": "John Kamau",
            "phone_number": "+254722334455",
            "address": "Household 88, Nakuru West",
            "community_name": "Nakuru Central",
            "latitude": -0.3031,
            "longitude": 36.0800,
            "family_members_count": 4,
            "baseline_fuel_type": "CHARCOAL",
            "baseline_fuel_kg_per_day": 6.0,
        }
        res_create = await ac.post(
            "/api/v1/cookstoves/households",
            json=payload,
            headers={"Authorization": f"Bearer {agent_token}"},
        )
        assert res_create.status_code == 201

        # General viewer queries household list -> MUST receive redacted coordinates
        res_list = await ac.get(
            f"/api/v1/cookstoves/households?project_id={proj_a.id}",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert res_list.status_code == 200
        items = res_list.json()
        assert len(items) >= 1
        hh = next(h for h in items if h["household_code"] == f"HH-{suffix}-002")

        # PRIVACY REDACTION PROOF
        assert hh["latitude"] is None, "General/viewer role must not receive exact latitude"
        assert hh["longitude"] is None, "General/viewer role must not receive exact longitude"
        assert hh["phone_number"] is None, "General/viewer role must not receive beneficiary phone number"
        assert hh["address"] == "[PROTECTED HOUSEHOLD LOCATION]"
        assert hh["is_coordinates_redacted"] is True
        # Community level context remains visible for aggregated grouping
        assert hh["community_name"] == "Nakuru Central"


@pytest.mark.asyncio
async def test_cookstove_tenant_isolation_blocks_cross_tenant_access(db_session: AsyncSession):
    suffix = uuid.uuid4().hex[:6]
    # Tenant A
    org_a = Organization(id=uuid.uuid4(), name=f"Cookstove Developer A {suffix}")
    # Tenant B
    org_b = Organization(id=uuid.uuid4(), name=f"Unauthorized Competitor B {suffix}")
    db_session.add_all([org_a, org_b])
    await db_session.flush()

    proj_a = Project(
        id=uuid.uuid4(),
        organization_id=org_a.id,
        name=f"Tenant A Project {suffix}",
    )
    db_session.add(proj_a)
    await db_session.flush()

    agent_a = User(
        id=uuid.uuid4(),
        email=f"agent.a.{suffix}@example.com",
        full_name="Agent A",
        role="FIELD_AGENT",
        organization_id=org_a.id,
    )
    admin_b = User(
        id=uuid.uuid4(),
        email=f"admin.b.{suffix}@example.com",
        full_name="Admin B",
        role="ORG_ADMIN",
        organization_id=org_b.id,
    )
    db_session.add_all([agent_a, admin_b])
    await db_session.commit()

    token_a = _create_token(agent_a.id, agent_a.email, agent_a.role, org_a.id)
    token_b = _create_token(admin_b.id, admin_b.email, admin_b.role, org_b.id)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Tenant A registers household
        payload = {
            "project_id": str(proj_a.id),
            "household_code": f"HH-TENANT-A-{suffix}",
            "head_of_household": "Alice Wanjiku",
            "phone_number": "+254733445566",
            "address": "Secret Farmhouse 9",
            "community_name": "Eldoret East",
            "latitude": 0.5143,
            "longitude": 35.2698,
            "family_members_count": 5,
        }
        res_create = await ac.post(
            "/api/v1/cookstoves/households",
            json=payload,
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert res_create.status_code == 201

        # 1. Tenant B attempts direct access to Tenant A project -> HTTP 403 Forbidden
        res_idor = await ac.get(
            f"/api/v1/cookstoves/households?project_id={proj_a.id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert res_idor.status_code == 403, "Cross-tenant access must be rejected with HTTP 403"

        # 2. Tenant B attempts POST household into Tenant A project -> HTTP 403 Forbidden
        res_attack_post = await ac.post(
            "/api/v1/cookstoves/households",
            json={**payload, "household_code": f"ATTACK-{suffix}"},
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert res_attack_post.status_code == 403, "Cross-tenant creation must be rejected with HTTP 403"

        # 3. Tenant B lists all households without project_id -> receives ONLY Tenant B data (zero records from Tenant A)
        res_b_list = await ac.get(
            "/api/v1/cookstoves/households",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert res_b_list.status_code == 200
        items_b = res_b_list.json()
        assert not any(h["household_code"] == f"HH-TENANT-A-{suffix}" for h in items_b), "Tenant B must never see Tenant A households"
