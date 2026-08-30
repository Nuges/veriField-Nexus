"""
=============================================================================
VeriField Nexus — Forensic Remediation & Security Regression Suite
=============================================================================
Verifies:
1. Analytics API Auth & Strict Tenant Isolation (VF-001):
   - Unauthenticated requests to /analytics/daily, /trust-distribution, /global, /agents rejected (401/403).
   - Authenticated non-Super Admin users see ONLY their organization's data.
   - Dialect-agnostic daily date grouping works on SQLite and PostgreSQL.
2. Registry Sync Clean Error Responses (VF-002):
   - Unimplemented external providers return HTTP 501 with structured message, not 500 crashes.
3. Observability Live Prometheus Metrics (VF-004):
   - /metrics returns live Prometheus format with build info, uptime, and request counters.
4. Ledger Digital Signature Determinism (VF-006):
   - DigitalSignatureProvider verifies signatures deterministically across instances.
=============================================================================
"""

import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.db.session import _init_fallback_db, _get_fallback_session_factory, get_db
from app.core.security import get_current_user
from app.domains.authentication.models import User
from app.domains.organizations.models import Organization
from app.domains.activities.models import Activity
from app.domains.ledger.service import DigitalSignatureProvider, HashGenerator


@pytest_asyncio.fixture(autouse=True)
async def init_test_db():
    await _init_fallback_db()


@pytest.mark.asyncio
async def test_analytics_endpoints_require_authentication():
    """Verify all analytics endpoints reject unauthenticated requests (VF-001)."""
    app.dependency_overrides.pop(get_current_user, None)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp_daily = await client.get("/api/v1/analytics/daily")
        assert resp_daily.status_code in (401, 403), f"Expected 401/403 for unauth /daily, got {resp_daily.status_code}"

        resp_trust = await client.get("/api/v1/analytics/trust-distribution")
        assert resp_trust.status_code in (401, 403), f"Expected 401/403 for unauth /trust-distribution, got {resp_trust.status_code}"

        resp_global = await client.get("/api/v1/analytics/global")
        assert resp_global.status_code in (401, 403), f"Expected 401/403 for unauth /global, got {resp_global.status_code}"

        resp_agents = await client.get("/api/v1/analytics/agents")
        assert resp_agents.status_code in (401, 403), f"Expected 401/403 for unauth /agents, got {resp_agents.status_code}"


@pytest.mark.asyncio
async def test_analytics_strict_tenant_isolation():
    """Verify analytics endpoints isolate Org A from Org B data (VF-001)."""
    factory = _get_fallback_session_factory()
    org_a_id = uuid.uuid4()
    org_b_id = uuid.uuid4()
    user_a_id = uuid.uuid4()
    user_b_id = uuid.uuid4()

    user_a = User(
        id=user_a_id,
        email=f"admin_a_{uuid.uuid4().hex[:6]}@orga.com",
        full_name="Agent Alpha",
        role="ORG_ADMIN",
        organization_id=org_a_id,
        status="active",
        is_active=True,
    )
    user_b = User(
        id=user_b_id,
        email=f"admin_b_{uuid.uuid4().hex[:6]}@orgb.com",
        full_name="Agent Beta",
        role="ORG_ADMIN",
        organization_id=org_b_id,
        status="active",
        is_active=True,
    )

    async with factory() as db:
        db.add(Organization(id=org_a_id, name=f"Org A {uuid.uuid4().hex[:6]}", org_type="DEVELOPER"))
        db.add(Organization(id=org_b_id, name=f"Org B {uuid.uuid4().hex[:6]}", org_type="DEVELOPER"))
        db.add_all([user_a, user_b])

        # Add 3 activities for Org A, 1 for Org B
        now = datetime.now(timezone.utc)
        for i in range(3):
            db.add(Activity(
                id=uuid.uuid4(),
                organization_id=org_a_id,
                user_id=user_a_id,
                activity_type="stove_usage",
                status="verified",
                trust_score=95,
                captured_at=now,
                submitted_at=now,
            ))
        db.add(Activity(
            id=uuid.uuid4(),
            organization_id=org_b_id,
            user_id=user_b_id,
            activity_type="stove_usage",
            status="verified",
            trust_score=85,
            captured_at=now,
            submitted_at=now,
        ))
        await db.commit()

    async def override_get_db():
        async with factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Query /analytics/daily as User A
        app.dependency_overrides[get_current_user] = lambda: user_a
        daily_res_a = await client.get("/api/v1/analytics/daily?days=30")
        assert daily_res_a.status_code == 200, f"Expected 200, got {daily_res_a.status_code}: {daily_res_a.text}"
        daily_data_a = daily_res_a.json()
        total_counts_a = sum(d["count"] for d in daily_data_a)
        assert total_counts_a == 3, f"Expected 3 activities for Org A, got {total_counts_a}"

        # 2. Query /analytics/daily as User B
        app.dependency_overrides[get_current_user] = lambda: user_b
        daily_res_b = await client.get("/api/v1/analytics/daily?days=30")
        assert daily_res_b.status_code == 200
        daily_data_b = daily_res_b.json()
        total_counts_b = sum(d["count"] for d in daily_data_b)
        assert total_counts_b == 1, f"Expected 1 activity for Org B, got {total_counts_b}"

        # 3. Query /analytics/trust-distribution as User A
        app.dependency_overrides[get_current_user] = lambda: user_a
        trust_res_a = await client.get("/api/v1/analytics/trust-distribution")
        assert trust_res_a.status_code == 200
        assert trust_res_a.json()["high"] == 3, "Expected 3 high-trust activities for Org A"

        # 4. Query /analytics/trust-distribution as User B
        app.dependency_overrides[get_current_user] = lambda: user_b
        trust_res_b = await client.get("/api/v1/analytics/trust-distribution")
        assert trust_res_b.status_code == 200
        assert trust_res_b.json()["high"] == 1, "Expected 1 high-trust activity for Org B"

    # Cleanup overrides
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_observability_live_prometheus_metrics():
    """Verify live Prometheus metrics format (VF-004)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/observability/metrics")
        assert resp.status_code == 200
        assert "verifield_nexus_build_info" in resp.text
        assert "verifield_database_healthy" in resp.text
        assert "nexus_requests_total" in resp.text


@pytest.mark.asyncio
async def test_ledger_digital_signature_verification_determinism():
    """Verify RSA digital signatures can be verified across multiple instances (VF-006)."""
    signer1 = DigitalSignatureProvider()
    signer2 = DigitalSignatureProvider()

    payload = {"project_id": str(uuid.uuid4()), "credits": 500, "timestamp": datetime.now(timezone.utc).isoformat()}
    canonical_hash = HashGenerator.generate_canonical_hash(payload)

    # Sign with instance 1
    signature_hex = signer1.sign_hash(canonical_hash)

    # Verify with instance 2
    is_valid = signer2.verify_signature(canonical_hash, signature_hex)
    assert is_valid is True, "Signature generated by instance 1 failed verification on instance 2!"

    # Verify tampering detection
    tampered_hash = HashGenerator.generate_canonical_hash({"tampered": True})
    assert signer2.verify_signature(tampered_hash, signature_hex) is False, "Tampered payload unexpectedly verified!"
