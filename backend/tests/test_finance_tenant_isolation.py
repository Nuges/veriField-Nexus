"""
Security & Tenant Isolation Tests for Finance Domain (P0-03)

Verifies:
1. Tenant A can initiate transactions for Tenant A (from_org_id == Org A)
2. Tenant A can read own transactions
3. Recipient Tenant (to_org_id) can read the transaction as a participant
4. Unrelated Tenant B cannot read Tenant A transaction (404)
5. Tenant B cannot spoof from_org_id to initiate transaction from Org A (403 Forbidden)
6. Super Admin can read and process transactions across tenants
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
from app.domains.finance.models import Transaction
from app.domains.organizations.models import Organization
from app.main import app


@pytest.mark.asyncio
@patch("app.core.event_bus.EventBus.publish", new_callable=AsyncMock)
async def test_finance_tenant_isolation(mock_event_bus):
    await _init_fallback_db()
    factory = _get_fallback_session_factory()

    org_a_id = uuid.uuid4()
    org_b_id = uuid.uuid4()
    org_c_id = uuid.uuid4()

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
    user_c = User(
        id=uuid.uuid4(),
        email=f"admin_c_{uuid.uuid4().hex[:6]}@tenant-c.com",
        full_name="Admin Tenant C",
        role="ORG_ADMIN",
        organization_id=org_c_id,
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
    org_c = Organization(id=org_c_id, name=f"Tenant C {uuid.uuid4().hex[:6]}", status="ACTIVE")

    async with factory() as session:
        session.add(org_a)
        session.add(org_b)
        session.add(org_c)
        session.add(user_a)
        session.add(user_b)
        session.add(user_c)
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

        # -----------------------------------------------------------------
        # 1. Tenant A initiates valid transaction (Org A -> Org C) -> 201 Created
        # -----------------------------------------------------------------
        app.dependency_overrides[get_current_user] = lambda: user_a
        tx_payload_a = {
            "from_org_id": str(org_a_id),
            "to_org_id": str(org_c_id),
            "amount": 50000.0,
            "currency": "USD",
            "metadata_json": {"memo": "Carbon offset purchase"},
        }
        res_create_a = await client.post("/api/v1/finance/transactions", json=tx_payload_a)
        assert res_create_a.status_code == 201, f"Tenant A tx creation failed: {res_create_a.text}"
        tx_id = res_create_a.json()["id"]

        # -----------------------------------------------------------------
        # 2. Tenant A (from_org) reads transaction -> 200 OK
        # -----------------------------------------------------------------
        res_get_a = await client.get(f"/api/v1/finance/transactions/{tx_id}")
        assert res_get_a.status_code == 200
        assert res_get_a.json()["id"] == tx_id

        # -----------------------------------------------------------------
        # 3. Tenant C (to_org participant) reads transaction -> 200 OK
        # -----------------------------------------------------------------
        app.dependency_overrides[get_current_user] = lambda: user_c
        res_get_c = await client.get(f"/api/v1/finance/transactions/{tx_id}")
        assert res_get_c.status_code == 200
        assert res_get_c.json()["id"] == tx_id

        # -----------------------------------------------------------------
        # 4. Unrelated Tenant B attempts to read Tenant A transaction -> 404
        # -----------------------------------------------------------------
        app.dependency_overrides[get_current_user] = lambda: user_b
        res_get_b = await client.get(f"/api/v1/finance/transactions/{tx_id}")
        assert res_get_b.status_code == 404, f"Tenant B should receive 404 for unrelated tx, got {res_get_b.status_code}"

        # -----------------------------------------------------------------
        # 5. Tenant B attempts to initiate transaction using Org A as from_org_id -> 403 Forbidden
        # -----------------------------------------------------------------
        tx_spoof_payload = {
            "from_org_id": str(org_a_id),
            "to_org_id": str(org_b_id),
            "amount": 99999.0,
            "currency": "USD",
            "metadata_json": {"memo": "Illegitimate drain attempt"},
        }
        res_spoof = await client.post("/api/v1/finance/transactions", json=tx_spoof_payload)
        assert res_spoof.status_code == 403, f"Tenant B spoofing from_org_id should be 403, got {res_spoof.status_code}"

        # -----------------------------------------------------------------
        # 6. Super Admin can read and process transactions across tenants -> 200 OK
        # -----------------------------------------------------------------
        app.dependency_overrides[get_current_user] = lambda: super_admin
        res_get_sa = await client.get(f"/api/v1/finance/transactions/{tx_id}")
        assert res_get_sa.status_code == 200
        assert res_get_sa.json()["id"] == tx_id

    app.dependency_overrides.clear()
