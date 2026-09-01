"""
=============================================================================
VeriField Nexus — Role-Based Access Control (RBAC) & Separation of Duties
=============================================================================
Defines standard platform permissions, maps them to canonical enterprise roles,
normalizes role aliases, enforces Separation of Duties (SoD), and provides
FastAPI dependency injection for route-level authorization.
=============================================================================
"""

from typing import Dict, Set, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.domains.authentication.models import User

# ─── Canonical Enterprise Roles ──────────────────────────────────────────────
ROLE_SUPER_ADMIN = "SUPER_ADMIN"
ROLE_ORG_ADMIN = "ORG_ADMIN"
ROLE_PROJECT_MANAGER = "PROJECT_MANAGER"
ROLE_FIELD_SUPERVISOR = "FIELD_SUPERVISOR"
ROLE_FIELD_AGENT = "FIELD_AGENT"
ROLE_QA_OFFICER = "QA_OFFICER"
ROLE_VERIFIER = "VERIFIER"
ROLE_AUDITOR = "AUDITOR"
ROLE_COMPLIANCE_ADMIN = "COMPLIANCE_ADMIN"
ROLE_REGISTRY_ADMIN = "REGISTRY_ADMIN"
ROLE_FINANCE = "FINANCE"
ROLE_INVESTOR = "INVESTOR"
ROLE_VIEWER = "VIEWER"

CANONICAL_ROLES: Set[str] = {
    ROLE_SUPER_ADMIN,
    ROLE_ORG_ADMIN,
    ROLE_PROJECT_MANAGER,
    ROLE_FIELD_SUPERVISOR,
    ROLE_FIELD_AGENT,
    ROLE_QA_OFFICER,
    ROLE_VERIFIER,
    ROLE_AUDITOR,
    ROLE_COMPLIANCE_ADMIN,
    ROLE_REGISTRY_ADMIN,
    ROLE_FINANCE,
    ROLE_INVESTOR,
    ROLE_VIEWER,
}

# Legacy backward-compatibility constants
ROLE_PLATFORM_SUPER_ADMIN = ROLE_SUPER_ADMIN
ROLE_ORG_OWNER = ROLE_ORG_ADMIN
ROLE_JURISDICTION_ADMIN = ROLE_COMPLIANCE_ADMIN
ROLE_PLATFORM_SUPPORT = ROLE_VIEWER
ROLE_OBSERVER = ROLE_VIEWER

# ─── Canonical Role Aliases Mapping ──────────────────────────────────────────
ROLE_ALIASES: Dict[str, str] = {
    # Super Admin
    "super_admin": ROLE_SUPER_ADMIN,
    "superadmin": ROLE_SUPER_ADMIN,
    "platform_super_admin": ROLE_SUPER_ADMIN,

    # Org Admin
    "admin": ROLE_ORG_ADMIN,
    "org_owner": ROLE_ORG_ADMIN,
    "tenant_admin": ROLE_ORG_ADMIN,
    "organization_admin": ROLE_ORG_ADMIN,

    # Project Manager
    "project_developer": ROLE_PROJECT_MANAGER,
    "developer": ROLE_PROJECT_MANAGER,
    "portfolio_manager": ROLE_PROJECT_MANAGER,
    "programme_manager": ROLE_PROJECT_MANAGER,

    # Field Operations
    "field_agent": ROLE_FIELD_AGENT,
    "operator": ROLE_FIELD_AGENT,
    "technician": ROLE_FIELD_AGENT,
    "surveyor": ROLE_FIELD_AGENT,

    # QA / MRV Officer
    "mrv_officer": ROLE_QA_OFFICER,
    "mrv_manager": ROLE_QA_OFFICER,
    "iot_engineer": ROLE_QA_OFFICER,
    "operations_engineer": ROLE_QA_OFFICER,

    # Verifier & Auditor
    "vvb": ROLE_VERIFIER,
    "vvb_verifier": ROLE_VERIFIER,
    "vvb_auditor": ROLE_AUDITOR,
    "third_party_auditor": ROLE_AUDITOR,

    # Compliance & Regulatory
    "compliance_officer": ROLE_COMPLIANCE_ADMIN,
    "regulator": ROLE_COMPLIANCE_ADMIN,
    "jurisdiction_admin": ROLE_COMPLIANCE_ADMIN,

    # Registry
    "registry_manager": ROLE_REGISTRY_ADMIN,
    "registry_officer": ROLE_REGISTRY_ADMIN,

    # Finance
    "finance_officer": ROLE_FINANCE,
    "treasury": ROLE_FINANCE,
    "billing_admin": ROLE_FINANCE,

    # Read-Only / Observers
    "observer": ROLE_VIEWER,
    "client": ROLE_VIEWER,
    "platform_support": ROLE_VIEWER,
}


def normalize_canonical_role(role_str: Optional[str]) -> str:
    """Normalizes any incoming role string into a canonical system role."""
    if not role_str:
        return ROLE_VIEWER
    cleaned = role_str.strip().upper().replace(" ", "_")
    cleaned_lower = role_str.strip().lower().replace(" ", "_")

    if cleaned_lower in ROLE_ALIASES:
        return ROLE_ALIASES[cleaned_lower]
    if cleaned in ROLE_ALIASES:
        return ROLE_ALIASES[cleaned]
    if cleaned in {
        ROLE_SUPER_ADMIN,
        ROLE_ORG_ADMIN,
        ROLE_PROJECT_MANAGER,
        ROLE_FIELD_SUPERVISOR,
        ROLE_FIELD_AGENT,
        ROLE_QA_OFFICER,
        ROLE_VERIFIER,
        ROLE_AUDITOR,
        ROLE_COMPLIANCE_ADMIN,
        ROLE_REGISTRY_ADMIN,
        ROLE_FINANCE,
        ROLE_INVESTOR,
        ROLE_VIEWER,
    }:
        return cleaned

    # Default unknown roles to least-privilege VIEWER
    return ROLE_VIEWER

ALL_ROLES: Set[str] = set(CANONICAL_ROLES) | {k.upper() for k in ROLE_ALIASES.keys()}
normalize_role = normalize_canonical_role


# ─── Role to Permissions Mapping ──────────────────────────────────────────────
ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    ROLE_SUPER_ADMIN: {
        "admin:all",
        "support:all",
        "org:manage",
        "org:read",
        "org:update",
        "project:all",
        "project:read",
        "project:create",
        "project:update",
        "asset:all",
        "asset:read",
        "activity:all",
        "activity:create",
        "activity:read",
        "activity:update",
        "activity:verify",
        "team:manage",
        "billing:manage",
        "report:all",
        "report:read",
        "ledger:all",
        "ledger:read",
        "ledger:mint",
        "ledger:manage",
        "audit:all",
        "audit:read",
        "audit:write",
        "verification:sign",
        "jurisdiction:all",
        "accreditation:all",
        "compliance:all",
        "compliance:read",
        "compliance:authorize",
        "registry:all",
        "registry:read",
        "registry:prepare",
        "registry:submit",
        "registry:authorize",
        "finance:all",
        "finance:read",
        "finance:manage",
    },
    ROLE_ORG_ADMIN: {
        "org:read",
        "org:update",
        "team:manage",
        "billing:manage",
        "project:read",
        "project:create",
        "project:update",
        "asset:all",
        "asset:read",
        "activity:all",
        "activity:read",
        "report:all",
        "report:read",
        "ledger:read",
        "audit:read",
        "compliance:read",
        "registry:read",
        "finance:read",
    },
    ROLE_PROJECT_MANAGER: {
        "org:read",
        "project:read",
        "project:create",
        "project:update",
        "asset:all",
        "asset:read",
        "activity:create",
        "activity:read",
        "activity:update",
        "report:all",
        "report:read",
        "ledger:read",
        "audit:read",
        "compliance:read",
        "registry:read",
        "registry:prepare",
    },
    ROLE_FIELD_SUPERVISOR: {
        "org:read",
        "project:read",
        "asset:read",
        "activity:create",
        "activity:read",
        "activity:update",
        "activity:verify",
        "team:manage",
        "report:read",
    },
    ROLE_FIELD_AGENT: {
        "org:read",
        "activity:create",
        "activity:read",
        "asset:read",
    },
    ROLE_QA_OFFICER: {
        "org:read",
        "project:read",
        "asset:read",
        "activity:read",
        "activity:verify",
        "report:all",
        "report:read",
        "ledger:read",
    },
    ROLE_VERIFIER: {
        "org:read",
        "project:read",
        "asset:read",
        "activity:read",
        "activity:verify",
        "report:read",
        "ledger:read",
        "audit:read",
        "audit:write",
        "verification:sign",
    },
    ROLE_AUDITOR: {
        "org:read",
        "project:read",
        "asset:read",
        "activity:read",
        "report:read",
        "ledger:read",
        "audit:read",
        "audit:write",
    },
    ROLE_COMPLIANCE_ADMIN: {
        "org:read",
        "compliance:all",
        "compliance:read",
        "compliance:authorize",
        "accreditation:all",
        "project:read",
        "asset:read",
        "activity:read",
        "report:read",
        "registry:read",
        "registry:authorize",
    },
    ROLE_REGISTRY_ADMIN: {
        "org:read",
        "registry:all",
        "registry:prepare",
        "registry:submit",
        "registry:read",
        "project:read",
        "ledger:read",
        "report:read",
    },
    ROLE_FINANCE: {
        "org:read",
        "finance:all",
        "finance:read",
        "finance:manage",
        "ledger:read",
        "ledger:mint",
        "ledger:manage",
        "billing:manage",
        "report:all",
        "report:read",
    },
    ROLE_INVESTOR: {
        "org:read",
        "project:read",
        "asset:read",
        "report:read",
        "ledger:read",
    },
    ROLE_VIEWER: {
        "org:read",
        "project:read",
        "asset:read",
        "activity:read",
        "report:read",
    },
}


def has_permission(user_role: str, permission: str) -> bool:
    """Check if a user role has the required permission."""
    if not user_role:
        return False

    canonical = normalize_canonical_role(user_role)

    # SUPER_ADMIN bypasses standard permission checks
    if canonical == ROLE_SUPER_ADMIN:
        return True

    permissions = ROLE_PERMISSIONS.get(canonical, set())
    if permission in permissions:
        return True

    # Wildcard check (e.g. 'project:all' satisfies 'project:read')
    category = permission.split(":")[0]
    if f"{category}:all" in permissions:
        return True

    return False


def require_permission(permission: str, entity_type: str = None):
    """FastAPI dependency factory that returns a dependency function gating routes based on permission."""

    async def dependency(
        user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
    ) -> User:
        canonical = normalize_canonical_role(user.role)
        if not has_permission(canonical, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access Denied: Role '{canonical}' lacks required permission '{permission}'.",
            )
        return user

    return dependency


# ─── Separation of Duties (SoD) Verification Helpers ─────────────────────────
def validate_separation_of_duties(actor: User, project_developer_id: Optional[UUID], action: str = "VERIFY"):
    """
    Enforces non-negotiable Separation of Duties:
    - A Project Developer cannot independently verify or audit their own project.
    - An actor verifying or signing off must hold accredited auditor/verifier credentials.
    """
    canonical_role = normalize_canonical_role(actor.role)

    # Super Admin can override for emergency platform governance
    if canonical_role == ROLE_SUPER_ADMIN:
        return

    # Verifier/Auditor credential check
    if action in ("VERIFY", "AUDIT", "SIGN_OFF"):
        if canonical_role not in (ROLE_VERIFIER, ROLE_AUDITOR):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Separation of Duties Violation: Action '{action}' requires accredited VVB auditor/verifier role, found '{canonical_role}'.",
            )

        if project_developer_id and str(actor.id).lower() == str(project_developer_id).lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Separation of Duties Violation: Project developer cannot independently audit, verify, or sign off their own project.",
            )
