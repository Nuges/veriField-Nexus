import pytest
import uuid
from httpx import AsyncClient
from app.core.rbac import (
    normalize_canonical_role,
    has_permission,
    validate_separation_of_duties,
    ROLE_SUPER_ADMIN,
    ROLE_ORG_ADMIN,
    ROLE_PROJECT_MANAGER,
    ROLE_FIELD_AGENT,
    ROLE_QA_OFFICER,
    ROLE_VERIFIER,
    ROLE_AUDITOR,
    ROLE_COMPLIANCE_ADMIN,
    ROLE_REGISTRY_ADMIN,
    ROLE_FINANCE,
    ROLE_VIEWER,
)
from app.domains.authentication.models import User
from fastapi import HTTPException


def test_role_normalization():
    """Verify that legacy, alias, and raw role strings map to canonical roles."""
    assert normalize_canonical_role("super_admin") == ROLE_SUPER_ADMIN
    assert normalize_canonical_role("admin") == ROLE_ORG_ADMIN
    assert normalize_canonical_role("org_owner") == ROLE_ORG_ADMIN
    assert normalize_canonical_role("project_developer") == ROLE_PROJECT_MANAGER
    assert normalize_canonical_role("field_agent") == ROLE_FIELD_AGENT
    assert normalize_canonical_role("vvb") == ROLE_VERIFIER
    assert normalize_canonical_role("third_party_auditor") == ROLE_AUDITOR
    assert normalize_canonical_role("compliance_officer") == ROLE_COMPLIANCE_ADMIN
    assert normalize_canonical_role("finance_officer") == ROLE_FINANCE
    assert normalize_canonical_role("unknown_custom_role") == ROLE_VIEWER


def test_permission_matrix_boundaries():
    """Verify least-privilege permissions across canonical roles."""
    # Super Admin has all permissions
    assert has_permission(ROLE_SUPER_ADMIN, "project:create") is True
    assert has_permission(ROLE_SUPER_ADMIN, "ledger:mint") is True
    assert has_permission(ROLE_SUPER_ADMIN, "audit:write") is True

    # Field Agent can only create/read activities and read assets
    assert has_permission(ROLE_FIELD_AGENT, "activity:create") is True
    assert has_permission(ROLE_FIELD_AGENT, "project:create") is False
    assert has_permission(ROLE_FIELD_AGENT, "ledger:mint") is False
    assert has_permission(ROLE_FIELD_AGENT, "audit:write") is False
    assert has_permission(ROLE_FIELD_AGENT, "team:manage") is False

    # Project Manager can manage projects, but CANNOT mint or audit
    assert has_permission(ROLE_PROJECT_MANAGER, "project:create") is True
    assert has_permission(ROLE_PROJECT_MANAGER, "project:update") is True
    assert has_permission(ROLE_PROJECT_MANAGER, "ledger:mint") is False
    assert has_permission(ROLE_PROJECT_MANAGER, "audit:write") is False
    assert has_permission(ROLE_PROJECT_MANAGER, "compliance:authorize") is False

    # VVB Auditor can write audit findings, but CANNOT mint, create projects, or manage teams
    assert has_permission(ROLE_AUDITOR, "audit:write") is True
    assert has_permission(ROLE_AUDITOR, "ledger:mint") is False
    assert has_permission(ROLE_AUDITOR, "project:create") is False
    assert has_permission(ROLE_AUDITOR, "team:manage") is False

    # Finance can mint ledger credits, but CANNOT verify or create projects
    assert has_permission(ROLE_FINANCE, "ledger:mint") is True
    assert has_permission(ROLE_FINANCE, "finance:manage") is True
    assert has_permission(ROLE_FINANCE, "audit:write") is False
    assert has_permission(ROLE_FINANCE, "project:create") is False

    # Compliance Admin can authorize ITMOs, but CANNOT mint or write audits
    assert has_permission(ROLE_COMPLIANCE_ADMIN, "compliance:authorize") is True
    assert has_permission(ROLE_COMPLIANCE_ADMIN, "ledger:mint") is False
    assert has_permission(ROLE_COMPLIANCE_ADMIN, "audit:write") is False


def test_separation_of_duties_developer_cannot_self_verify():
    """Verify SoD rule: Project Developer cannot verify or sign their own project."""
    developer_id = uuid.uuid4()
    other_user_id = uuid.uuid4()

    # Case 1: Developer tries to verify own project as a verifier
    actor_same = User(id=developer_id, role=ROLE_VERIFIER, full_name="Dev Verifier")
    with pytest.raises(HTTPException) as excinfo:
        validate_separation_of_duties(actor_same, developer_id, action="VERIFY")
    assert excinfo.value.status_code == 403
    assert "Separation of Duties Violation" in excinfo.value.detail

    # Case 2: Project manager without verifier role tries to verify
    actor_pm = User(id=other_user_id, role=ROLE_PROJECT_MANAGER, full_name="Project Manager")
    with pytest.raises(HTTPException) as excinfo:
        validate_separation_of_duties(actor_pm, developer_id, action="VERIFY")
    assert excinfo.value.status_code == 403
    assert "requires accredited VVB" in excinfo.value.detail

    # Case 3: Accredited third-party verifier verifies project (Allowed)
    actor_valid_vvb = User(id=other_user_id, role=ROLE_VERIFIER, full_name="Independent VVB")
    # Should not raise exception
    validate_separation_of_duties(actor_valid_vvb, developer_id, action="VERIFY")


@pytest.mark.asyncio
async def test_update_user_role_hierarchy_protection():
    """Verify that tenant admins cannot escalate users to SUPER_ADMIN."""
    from app.domains.authentication.service import AuthenticationService
    from unittest.mock import AsyncMock

    mock_repo = AsyncMock()
    target_user = User(
        id=uuid.uuid4(),
        email="test_user@example.com",
        role="FIELD_AGENT",
        organization_id=uuid.uuid4()
    )
    mock_repo.get_by_id.return_value = target_user
    mock_repo.update.side_effect = lambda u: u

    service = AuthenticationService(mock_repo)

    # Tenant Org Admin trying to promote user to SUPER_ADMIN
    org_admin_actor = User(
        id=uuid.uuid4(),
        email="org_admin@example.com",
        role=ROLE_ORG_ADMIN,
        organization_id=target_user.organization_id
    )

    with pytest.raises(HTTPException) as excinfo:
        await service.update_user_role(target_user.id, "SUPER_ADMIN", actor_user=org_admin_actor)
    assert excinfo.value.status_code == 403
    assert "Only Super Admin can assign the Super Admin role" in excinfo.value.detail

    # Tenant Org Admin trying to update a user in another organization
    other_org_admin = User(
        id=uuid.uuid4(),
        email="other_admin@example.com",
        role=ROLE_ORG_ADMIN,
        organization_id=uuid.uuid4()  # Different organization
    )
    with pytest.raises(HTTPException) as excinfo:
        await service.update_user_role(target_user.id, "PROJECT_MANAGER", actor_user=other_org_admin)
    assert excinfo.value.status_code == 403
    assert "outside your organization" in excinfo.value.detail


@pytest.mark.asyncio
async def test_provision_user_account_with_qa_officer_and_canonical_roles(db_session):
    """Verify that provision_user_account accepts QA_OFFICER and all canonical roles."""
    from app.domains.organizations.routers.governance import provision_user_account
    from app.domains.organizations.models import Organization

    org_id = uuid.uuid4()
    org = Organization(
        id=org_id,
        name=f"Test Org {uuid.uuid4().hex[:6]}",
        org_type="DEVELOPER",
        status="ACTIVE",
    )
    db_session.add(org)
    await db_session.commit()

    admin_actor = User(
        id=uuid.uuid4(),
        email="admin@testorg.com",
        role="ORG_ADMIN",
        organization_id=org_id,
        is_active=True,
    )

    # 1. Provision QA_OFFICER
    res_qa = await provision_user_account(
        db=db_session,
        actor_user=admin_actor,
        full_name="Seyi Ol",
        email=f"seyi_{uuid.uuid4().hex[:6]}@testorg.com",
        role="QA_OFFICER",
        organization_id=org_id,
        custom_password="ValidPassword123!",
    )
    assert res_qa["user"].role == "QA_OFFICER"
    assert res_qa["user"].full_name == "Seyi Ol"

    # 2. Provision VERIFIER
    res_verifier = await provision_user_account(
        db=db_session,
        actor_user=admin_actor,
        full_name="Verifier Jane",
        email=f"jane_{uuid.uuid4().hex[:6]}@testorg.com",
        role="VERIFIER",
        organization_id=org_id,
        custom_password="ValidPassword123!",
    )
    assert res_verifier["user"].role == "VERIFIER"

    # 3. Provision PROJECT_MANAGER
    res_pm = await provision_user_account(
        db=db_session,
        actor_user=admin_actor,
        full_name="PM John",
        email=f"john_{uuid.uuid4().hex[:6]}@testorg.com",
        role="PROJECT_MANAGER",
        organization_id=org_id,
        custom_password="ValidPassword123!",
    )
    assert res_pm["user"].role == "PROJECT_MANAGER"


@pytest.mark.asyncio
async def test_role_escalation_negative_controls():
    """Verify negative authorization controls across roles and tenant boundaries."""
    from app.domains.authentication.service import AuthenticationService
    from app.core.config import settings
    from unittest.mock import AsyncMock

    mock_repo = AsyncMock()
    org_a = uuid.uuid4()
    org_b = uuid.uuid4()

    user_field_agent = User(
        id=uuid.uuid4(),
        email="agent@testorg.com",
        role="FIELD_AGENT",
        organization_id=org_a,
    )
    user_target = User(
        id=uuid.uuid4(),
        email="target@testorg.com",
        role="VIEWER",
        organization_id=org_a,
    )
    user_other_tenant = User(
        id=uuid.uuid4(),
        email="other@tenantb.com",
        role="VIEWER",
        organization_id=org_b,
    )

    mock_repo.get_by_id.side_effect = lambda uid: (
        user_target if uid == user_target.id else (user_other_tenant if uid == user_other_tenant.id else None)
    )
    mock_repo.update.side_effect = lambda u: u
    service = AuthenticationService(mock_repo)

    # 1. FIELD_AGENT cannot modify any user's role
    with pytest.raises(HTTPException) as excinfo:
        await service.update_user_role(user_target.id, "PROJECT_MANAGER", actor_user=user_field_agent)
    assert excinfo.value.status_code == 403

    # 2. ORG_ADMIN cannot escalate to SUPER_ADMIN
    org_admin = User(
        id=uuid.uuid4(),
        email="admin@testorg.com",
        role="ORG_ADMIN",
        organization_id=org_a,
    )
    with pytest.raises(HTTPException) as excinfo:
        await service.update_user_role(user_target.id, "SUPER_ADMIN", actor_user=org_admin)
    assert excinfo.value.status_code == 403
    assert "Only Super Admin can assign the Super Admin role" in excinfo.value.detail

    # 3. SUPER_ADMIN cannot promote an unauthorized email to SUPER_ADMIN
    super_admin_actor = User(
        id=uuid.uuid4(),
        email=settings.authorized_bootstrap_admin_email,
        role="SUPER_ADMIN",
    )
    with pytest.raises(HTTPException) as excinfo:
        await service.update_user_role(user_target.id, "SUPER_ADMIN", actor_user=super_admin_actor)
    assert excinfo.value.status_code == 403
    assert "restricted to designated administrator email" in excinfo.value.detail

    # 4. Cross-tenant role modification denied for ORG_ADMIN
    with pytest.raises(HTTPException) as excinfo:
        await service.update_user_role(user_other_tenant.id, "PROJECT_MANAGER", actor_user=org_admin)
    assert excinfo.value.status_code == 403
    assert "outside your organization" in excinfo.value.detail


@pytest.mark.asyncio
async def test_inactive_suspended_deleted_user_token_rejections(db_session):
    """Verify that get_current_user rejects inactive, suspended, or deleted users."""
    from app.core.security import get_current_user
    import jwt as pyjwt
    from app.core.config import settings

    uid_suffix = uuid.uuid4().hex[:8]
    test_org_id = uuid.uuid4()
    # 1. User with is_active = False
    inactive_user = User(
        id=uuid.uuid4(),
        email=f"inactive_{uid_suffix}@example.com",
        full_name="Inactive User",
        role="FIELD_AGENT",
        status="active",
        is_active=False,
        organization_id=test_org_id,
    )
    db_session.add(inactive_user)

    # 2. User with status = "suspended"
    suspended_user = User(
        id=uuid.uuid4(),
        email=f"suspended_{uid_suffix}@example.com",
        full_name="Suspended User",
        role="FIELD_AGENT",
        status="suspended",
        is_active=True,
        organization_id=test_org_id,
    )
    db_session.add(suspended_user)

    # 3. User with is_deleted = True
    deleted_user = User(
        id=uuid.uuid4(),
        email=f"deleted_{uid_suffix}@example.com",
        full_name="Deleted User",
        role="SUPER_ADMIN",
        status="active",
        is_active=False,
        is_deleted=True,
        organization_id=test_org_id,
    )
    db_session.add(deleted_user)
    await db_session.commit()

    def make_token(uid: uuid.UUID, email: str, role: str):
        payload = {
            "sub": str(uid),
            "email": email,
            "role": role,
            "exp": 9999999999,
        }
        return pyjwt.encode(payload, settings.effective_jwt_secret, algorithm="HS256")

    try:
        # Inactive user token must raise 403
        token_inactive = make_token(inactive_user.id, inactive_user.email, inactive_user.role)
        with pytest.raises(HTTPException) as exc1:
            await get_current_user(token=token_inactive, db=db_session)
        assert exc1.value.status_code == 403
        assert "inactive" in exc1.value.detail

        # Suspended user token must raise 403
        token_suspended = make_token(suspended_user.id, suspended_user.email, suspended_user.role)
        with pytest.raises(HTTPException) as exc2:
            await get_current_user(token=token_suspended, db=db_session)
        assert exc2.value.status_code == 403
        assert "suspended" in exc2.value.detail

        # Deleted user token must raise 403 even if claimed role is SUPER_ADMIN
        token_deleted = make_token(deleted_user.id, deleted_user.email, deleted_user.role)
        with pytest.raises(HTTPException) as exc3:
            await get_current_user(token=token_deleted, db=db_session)
        assert exc3.value.status_code == 403
        assert "deleted" in exc3.value.detail
    finally:
        await db_session.delete(inactive_user)
        await db_session.delete(suspended_user)
        await db_session.delete(deleted_user)
        await db_session.commit()

