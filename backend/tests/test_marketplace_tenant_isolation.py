"""
Security & Tenant Isolation Tests for Marketplace Domain (P0-04)

Verifies:
1. Tenant A (ORG_ADMIN) can create listings for Tenant A (org_id == Org A)
2. Tenant B attempts to spoof org_id to create listing for Tenant A -> 403 Forbidden
3. Super Admin can create listing for specified organization
4. Non-admin roles (e.g. FIELD_AGENT) cannot create listings -> 403 Forbidden
5. Active marketplace listings are viewable
"""
import uuid
from unittest.mock import patch, AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import get_current_user
from app.db.session import (
    get_db,
    _init_fallback_db,
    _get_fallback_session_factory,
)
from app.domains.authentication.models import User
from app.domains.marketplace.models import Listing
from app.domains.organizations.models import Organization
from app.main import app


@pytest.mark.asyncio
@patch("app.core.event_bus.EventBus.publish", new_callable=AsyncMock)
async def test_marketplace_tenant_isolation(mock_event_bus):
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
    user_field_agent = User(
        id=uuid.uuid4(),
        email=f"agent_{uuid.uuid4().hex[:6]}@tenant-a.com",
        full_name="Field Agent",
        role="FIELD_AGENT",
        organization_id=org_a_id,
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

    async with factory() as session:
        session.add(org_a)
        session.add(org_b)
        session.add(user_a)
        session.add(user_b)
        session.add(user_field_agent)
        session.add(super_admin)
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

        project_id = uuid.uuid4()

        # -----------------------------------------------------------------
        # 1. Tenant A creates listing for Org A -> 201 Created
        # -----------------------------------------------------------------
        app.dependency_overrides[get_current_user] = lambda: user_a
        listing_payload_a = {
            "org_id": str(org_a_id),
            "project_id": str(project_id),
            "quantity": 1000.0,
            "price_per_unit": 25.5,
            "currency": "USD",
            "status": "ACTIVE",
        }
        res_create_a = await client.post("/api/v1/marketplace/listings", json=listing_payload_a)
        assert res_create_a.status_code == 201, f"Tenant A listing creation failed: {res_create_a.text}"
        listing_id = res_create_a.json()["id"]

        # -----------------------------------------------------------------
        # 2. Tenant B attempts to create listing for Org A (spoofing org_id) -> 403 Forbidden
        # -----------------------------------------------------------------
        app.dependency_overrides[get_current_user] = lambda: user_b
        listing_payload_spoof = {
            "org_id": str(org_a_id),
            "project_id": str(project_id),
            "quantity": 500.0,
            "price_per_unit": 10.0,
            "currency": "USD",
            "status": "ACTIVE",
        }
        res_spoof = await client.post("/api/v1/marketplace/listings", json=listing_payload_spoof)
        assert res_spoof.status_code == 403, f"Tenant B spoofing org_id should be 403, got {res_spoof.status_code}"

        # -----------------------------------------------------------------
        # 3. Super Admin creates listing explicitly for Org A -> 201 Created
        # -----------------------------------------------------------------
        app.dependency_overrides[get_current_user] = lambda: super_admin
        res_sa = await client.post("/api/v1/marketplace/listings", json=listing_payload_a)
        assert res_sa.status_code == 201, f"Super Admin listing creation failed: {res_sa.text}"

        # -----------------------------------------------------------------
        # 4. Field Agent cannot create listing -> 403 Forbidden
        # -----------------------------------------------------------------
        app.dependency_overrides[get_current_user] = lambda: user_field_agent
        res_fa = await client.post("/api/v1/marketplace/listings", json=listing_payload_a)
        assert res_fa.status_code == 403

        # -----------------------------------------------------------------
        # 5. Public read of listing -> 200 OK
        # -----------------------------------------------------------------
        res_get = await client.get(f"/api/v1/marketplace/listings/{listing_id}")
        assert res_get.status_code == 200
        assert res_get.json()["id"] == listing_id

    app.dependency_overrides.clear()
