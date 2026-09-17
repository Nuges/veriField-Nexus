"""
=============================================================================
VeriField Nexus — Privileged Access, RBAC & SoD Enforcement Test Suite
=============================================================================
Verifies:
1. Bootstrap Admin Production Safety (no unconfigured fallback).
2. Persisted Role Authoritative over Bootstrap Email (no privilege from email alone).
3. Immediate Loss of Privilege upon Role Downgrade in Database.
4. Email Domain and Case-Insensitivity Normalization.
5. Strict Role Validation: Rejection of invalid roles (ROOT, SUPERUSER, SYSTEM_ADMIN).
6. Canonical Role Aliasing (technician -> FIELD_AGENT, admin -> ORG_ADMIN, vvb -> VERIFIER).
7. One-Time Bootstrap Semantics (does not resurrect soft-deleted accounts).
8. Comprehensive Security Audit Logging for Role Updates & Rejected Escalations.
9. Org Admin Separation of Duties (cannot promote to SUPER_ADMIN, cannot cross tenant boundaries).
=============================================================================
"""

import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text, select

from app.main import app
from app.core.config import settings, Settings
from app.core.rbac import (
    ALL_ROLES,
    ROLE_SUPER_ADMIN,
    ROLE_ORG_ADMIN,
    ROLE_FIELD_AGENT,
    ROLE_VERIFIER,
    ROLE_AUDITOR,
    ROLE_COMPLIANCE_ADMIN,
    ROLE_VIEWER,
    validate_assignable_role,
    normalize_canonical_role,
    is_canonical_or_alias,
)
from app.core.security import get_current_user, get_password_hash
from app.db.session import _init_fallback_db, _get_fallback_session_factory, get_db
from app.domains.authentication.models import User, SecurityAuditLog
from app.domains.organizations.models import Organization
from app.domains.authentication.service import AuthenticationService
from app.domains.authentication.repository import UserRepository
from fastapi import HTTPException


@pytest_asyncio.fixture(autouse=True)
async def init_test_db():
    await _init_fallback_db()


@pytest.mark.asyncio
async def test_bootstrap_admin_production_disabled_without_env():
    """In production environment, bootstrap admin email is disabled ("") if not set."""
    test_settings = Settings(
        app_env="production",
        verifield_bootstrap_admin_email="",
        super_admin_email="",
    )
    assert test_settings.is_production is True
    assert test_settings.authorized_bootstrap_admin_email == ""


@pytest.mark.asyncio
async def test_case_insensitive_bootstrap_email_normalization(monkeypatch):
    """Bootstrap email matching is normalized and case-insensitive."""
    monkeypatch.setattr(settings, "verifield_bootstrap_admin_email", "SuperAdmin@VeriField.com")
    assert settings.authorized_bootstrap_admin_email == "superadmin@verifield.com"


@pytest.mark.asyncio
async def test_invalid_role_strings_rejected():
    """Invalid roles like ROOT, SUPERUSER, SYSTEM_ADMIN are strictly rejected."""
    invalid_roles = ["ROOT", "SUPERUSER", "SYSTEM_ADMIN", "INVALID_ROLE", "OWNER", "GOD_MODE"]
    for role in invalid_roles:
        with pytest.raises(HTTPException) as excinfo:
            validate_assignable_role(role)
        assert excinfo.value.status_code == 400
        assert "Invalid role" in excinfo.value.detail


@pytest.mark.asyncio
async def test_legacy_role_alias_resolution():
    """Legacy aliases resolve deterministically to canonical 13 roles."""
    assert validate_assignable_role("technician") == ROLE_FIELD_AGENT
    assert validate_assignable_role("TECHNICIAN") == ROLE_FIELD_AGENT
    assert validate_assignable_role("operator") == ROLE_FIELD_AGENT
    assert validate_assignable_role("admin") == ROLE_ORG_ADMIN
    assert validate_assignable_role("vvb") == ROLE_VERIFIER
    assert validate_assignable_role("vvb_auditor") == ROLE_AUDITOR
    assert validate_assignable_role("regulator") == ROLE_COMPLIANCE_ADMIN
    assert validate_assignable_role("observer") == ROLE_VIEWER


@pytest.mark.asyncio
async def test_persisted_role_authoritative_over_bootstrap_email(monkeypatch):
    """
    A user whose email matches the bootstrap admin email, but whose database role
    is FIELD_AGENT, must NOT be permitted to access SUPER_ADMIN governance endpoints.
    """
    unique_email = f"bootstrap_agent_{uuid.uuid4().hex[:8]}@verifield.test"
    monkeypatch.setattr(settings, "verifield_bootstrap_admin_email", unique_email)
    session_factory = _get_fallback_session_factory()
    user_id = uuid.uuid4()
    async with session_factory() as session:
        field_agent_user = User(
            id=user_id,
            email=unique_email,
            full_name="Designated Agent",
            role=ROLE_FIELD_AGENT,
            status="active",
            is_active=True,
            password_hash=get_password_hash("TestPassword123!"),
        )
        session.add(field_agent_user)
        await session.commit()

    async def override_user():
        async with session_factory() as sess:
            return await sess.get(User, user_id)

    app.dependency_overrides[get_current_user] = override_user
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/admin/users")
        # Field agent must be forbidden (403), even though email matches bootstrap email
        assert resp.status_code == 403
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_downgraded_super_admin_immediately_loses_privilege():
    """
    A user whose database role is downgraded from SUPER_ADMIN to ORG_ADMIN
    immediately loses SUPER_ADMIN authority on the next request.
    """
    session_factory = _get_fallback_session_factory()
    user_id = uuid.uuid4()
    unique_email = f"downgrade_admin_{uuid.uuid4().hex[:8]}@verifield.test"
    async with session_factory() as session:
        test_admin = User(
            id=user_id,
            email=unique_email,
            full_name="Platform Admin",
            role=ROLE_SUPER_ADMIN,
            status="active",
            is_active=True,
            password_hash=get_password_hash("TestPassword123!"),
        )
        session.add(test_admin)
        await session.commit()

    async def override_current():
        async with session_factory() as sess:
            return await sess.get(User, user_id)

    app.dependency_overrides[get_current_user] = override_current
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp1 = await client.get("/api/v1/admin/users")
        assert resp1.status_code == 200

        # Downgrade role in database
        async with session_factory() as session:
            db_user = await session.get(User, user_id)
            db_user.role = ROLE_ORG_ADMIN
            await session.commit()

        # Next request must be rejected (403)
        resp2 = await client.get("/api/v1/admin/users")
        assert resp2.status_code == 403

    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_email_domain_mismatch_rejected(monkeypatch):
    """
    Promotion to SUPER_ADMIN fails if email domain or full email does not match
    authorized_bootstrap_admin_email.
    """
    admin_email = f"admin_{uuid.uuid4().hex[:8]}@verifield.com"
    monkeypatch.setattr(settings, "verifield_bootstrap_admin_email", admin_email)
    session_factory = _get_fallback_session_factory()
    async with session_factory() as session:
        repo = UserRepository(session)
        service = AuthenticationService(repo)

        super_actor = User(
            id=uuid.uuid4(),
            email=admin_email,
            full_name="Super Actor",
            role=ROLE_SUPER_ADMIN,
            is_active=True,
        )
        target = User(
            id=uuid.uuid4(),
            email=f"admin_{uuid.uuid4().hex[:8]}@attacker.com",  # Same local-part prefix, wrong domain!
            full_name="Attacker Admin",
            role=ROLE_FIELD_AGENT,
            is_active=True,
        )
        session.add(super_actor)
        session.add(target)
        await session.commit()

        with pytest.raises(HTTPException) as excinfo:
            await service.update_user_role(
                user_id=target.id,
                new_role=ROLE_SUPER_ADMIN,
                actor_user=super_actor,
            )
        assert excinfo.value.status_code == 403
        assert "restricted to designated administrator email" in excinfo.value.detail


@pytest.mark.asyncio
async def test_org_admin_cannot_promote_to_super_admin():
    """ORG_ADMIN attempting to assign SUPER_ADMIN is rejected with 403."""
    session_factory = _get_fallback_session_factory()
    org_id = uuid.uuid4()
    async with session_factory() as session:
        repo = UserRepository(session)
        service = AuthenticationService(repo)

        org_admin = User(
            id=uuid.uuid4(),
            email=f"orgadmin_{uuid.uuid4().hex[:8]}@org.com",
            full_name="Org Admin",
            role=ROLE_ORG_ADMIN,
            organization_id=org_id,
            is_active=True,
        )
        target = User(
            id=uuid.uuid4(),
            email=f"agent_{uuid.uuid4().hex[:8]}@org.com",
            full_name="Org Agent",
            role=ROLE_FIELD_AGENT,
            organization_id=org_id,
            is_active=True,
        )
        session.add(org_admin)
        session.add(target)
        await session.commit()

        with pytest.raises(HTTPException) as excinfo:
            await service.update_user_role(
                user_id=target.id,
                new_role=ROLE_SUPER_ADMIN,
                actor_user=org_admin,
            )
        assert excinfo.value.status_code == 403
        assert "Only Super Admin can assign the Super Admin role" in excinfo.value.detail


@pytest.mark.asyncio
async def test_org_admin_cross_tenant_role_modification_denied():
    """ORG_ADMIN attempting to modify role of a user in another organization is rejected."""
    session_factory = _get_fallback_session_factory()
    org1_id = uuid.uuid4()
    org2_id = uuid.uuid4()
    async with session_factory() as session:
        repo = UserRepository(session)
        service = AuthenticationService(repo)

        org_admin = User(
            id=uuid.uuid4(),
            email=f"admin_{uuid.uuid4().hex[:8]}@org1.com",
            full_name="Org1 Admin",
            role=ROLE_ORG_ADMIN,
            organization_id=org1_id,
            is_active=True,
        )
        target = User(
            id=uuid.uuid4(),
            email=f"agent_{uuid.uuid4().hex[:8]}@org2.com",
            full_name="Org2 Agent",
            role=ROLE_FIELD_AGENT,
            organization_id=org2_id,
            is_active=True,
        )
        session.add(org_admin)
        session.add(target)
        await session.commit()

        with pytest.raises(HTTPException) as excinfo:
            await service.update_user_role(
                user_id=target.id,
                new_role=ROLE_VERIFIER,
                actor_user=org_admin,
            )
        assert excinfo.value.status_code == 403
        assert "outside your organization" in excinfo.value.detail


@pytest.mark.asyncio
async def test_audit_logging_on_role_updates_and_rejected_escalations(monkeypatch):
    """Role updates and rejected escalations create audit entries in SecurityAuditLog."""
    admin_email = f"audit_admin_{uuid.uuid4().hex[:8]}@verifield.com"
    monkeypatch.setattr(settings, "verifield_bootstrap_admin_email", admin_email)
    session_factory = _get_fallback_session_factory()
    org_id = uuid.uuid4()
    async with session_factory() as session:
        repo = UserRepository(session)
        service = AuthenticationService(repo)

        super_user = User(
            id=uuid.uuid4(),
            email=admin_email,
            full_name="Audit Super Admin",
            role=ROLE_SUPER_ADMIN,
            organization_id=org_id,
            is_active=True,
        )
        agent = User(
            id=uuid.uuid4(),
            email=f"agent_{uuid.uuid4().hex[:8]}@verifield.com",
            full_name="Audit Field Agent",
            role=ROLE_FIELD_AGENT,
            organization_id=org_id,
            is_active=True,
        )
        session.add(super_user)
        session.add(agent)
        await session.commit()

        # 1. Rejected escalation
        try:
            await service.update_user_role(
                user_id=agent.id,
                new_role=ROLE_SUPER_ADMIN,
                actor_user=agent,  # Agent tries self-escalation
            )
        except HTTPException:
            pass

        # Check audit log for this agent
        res = await session.execute(
            select(SecurityAuditLog).where(
                SecurityAuditLog.action == "UNAUTHORIZED_ROLE_ESCALATION_ATTEMPT",
                SecurityAuditLog.target_user_id == agent.id,
            )
        )
        log_entry = res.scalars().first()
        assert log_entry is not None
        assert log_entry.result == "FORBIDDEN"

        # 2. Legitimate role update
        await service.update_user_role(
            user_id=agent.id,
            new_role=ROLE_VERIFIER,
            actor_user=super_user,
        )

        res_update = await session.execute(
            select(SecurityAuditLog).where(
                SecurityAuditLog.action == "ROLE_UPDATED",
                SecurityAuditLog.target_user_id == agent.id,
            )
        )
        log_update = res_update.scalars().first()
        assert log_update is not None
        assert log_update.result == "SUCCESS"
        assert log_update.metadata_json["new_role"] == ROLE_VERIFIER


@pytest.mark.asyncio
async def test_one_time_bootstrap_does_not_resurrect_deleted_admin():
    """
    One-time bootstrap semantics: if designated bootstrap account is downgraded or
    soft-deleted, re-running database initialization must NOT overwrite or resurrect it.
    """
    session_factory = _get_fallback_session_factory()
    test_email = f"bootstrap_downgraded_{uuid.uuid4().hex[:6]}@verifield.test"
    async with session_factory() as session:
        # Explicitly insert or update the bootstrap admin account into a soft-deleted, downgraded VIEWER state
        await session.execute(text("""
            INSERT INTO users (id, email, full_name, role, status, is_active, password_hash, requires_password_change, version, is_deleted, created_at, updated_at)
            VALUES ('00000000-0000-0000-0000-000000000001', :email, 'Bootstrap Test', 'VIEWER', 'inactive', 0, 'hash', 0, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET role = 'VIEWER', is_deleted = 1
        """), {"email": test_email})
        await session.commit()

    # Re-run _init_fallback_db()
    # Note: _fallback_initialized might be True, so temporarily set it to False to simulate app restart
    import app.db.session as session_module
    session_module._fallback_initialized = False
    await session_module._init_fallback_db()

    # Verify the user was NOT resurrected to is_deleted=0 and was NOT re-elevated to SUPER_ADMIN
    async with session_factory() as session:
        res = await session.execute(
            text("SELECT role, is_deleted FROM users WHERE id = '00000000-0000-0000-0000-000000000001'")
        )
        row = res.first()
        assert row is not None
        assert row[0] == "VIEWER"
        assert row[1] == 1

    # Restore bootstrap super admin to prevent side-effects on subsequent test suites
    async with session_factory() as session:
        from app.core.security import get_password_hash
        pw_hash = get_password_hash("Lovelyday1")
        await session.execute(text("""
            INSERT OR REPLACE INTO users (id, email, full_name, role, status, is_active, password_hash, requires_password_change, version, is_deleted, created_at, updated_at)
            VALUES (
                '00000000-0000-0000-0000-000000000001',
                :admin_email,
                'Platform Super Admin',
                'SUPER_ADMIN',
                'active',
                1,
                :pw_hash,
                0,
                1,
                0,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
        """), {"admin_email": settings.authorized_bootstrap_admin_email, "pw_hash": pw_hash})
        await session.commit()

