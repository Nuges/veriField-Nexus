"""
=============================================================================
VeriField Nexus — Role-Based Access Control (RBAC)
=============================================================================
Defines standard platform permissions and maps them to enterprise roles.
Gates API requests dynamically to eliminate hardcoded role checks.
=============================================================================
"""

from typing import Dict, Set

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.domains.authentication.models import User

# Enterprise Platform Roles
ROLE_PLATFORM_SUPER_ADMIN = "SUPER_ADMIN"  # Global superadmin
ROLE_COMPLIANCE_ADMIN = "COMPLIANCE_ADMIN"  # Global compliance admin
ROLE_PLATFORM_SUPPORT = "PLATFORM_SUPPORT"  # Global support
ROLE_JURISDICTION_ADMIN = "JURISDICTION_ADMIN"  # Regulator / jurisdiction admin
ROLE_REGISTRY_ADMIN = "REGISTRY_ADMIN"  # External registry admin
ROLE_ORG_OWNER = "ORG_OWNER"  # Tenant owner (full control)
ROLE_ORG_ADMIN = "ORG_ADMIN"  # Tenant admin (operational control)
ROLE_PROJECT_MANAGER = "PROJECT_MANAGER"  # Project manager (write projects/assets)
ROLE_FIELD_SUPERVISOR = "FIELD_SUPERVISOR"  # Team supervisor (manages agents)
ROLE_FIELD_AGENT = "field_agent"  # Field mobile agent (submits activities)
ROLE_QA_OFFICER = "QA_OFFICER"  # Quality assurance reviewer
ROLE_VERIFIER = "VERIFIER"  # Independent verifier
ROLE_AUDITOR = "AUDITOR"  # Independent auditor
ROLE_INVESTOR = "INVESTOR"  # Read-only investor
ROLE_OBSERVER = "OBSERVER"  # Observer
ROLE_VIEWER = "VIEWER"  # Read-only viewer

# Role to Permissions Mapping
ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    ROLE_PLATFORM_SUPER_ADMIN: {
        "admin:all",
        "support:all",
        "org:manage",
        "project:all",
        "asset:all",
        "activity:all",
        "activity:verify",
        "team:manage",
        "billing:manage",
        "report:all",
        "ledger:all",
        "audit:all",
        "jurisdiction:all",
        "accreditation:all",
    },
    ROLE_COMPLIANCE_ADMIN: {
        "accreditation:all",
        "compliance:all",
        "project:read",
        "asset:read",
        "activity:read",
    },
    ROLE_PLATFORM_SUPPORT: {
        "support:all",
        "org:read",
        "project:read",
        "asset:read",
        "activity:read",
        "report:read",
        "ledger:read",
        "audit:read",
    },
    ROLE_JURISDICTION_ADMIN: {
        "jurisdiction:all",
        "project:read",
        "asset:read",
        "activity:read",
        "report:read",
        "compliance:read",
    },
    ROLE_REGISTRY_ADMIN: {"project:read", "ledger:read", "report:read"},
    ROLE_ORG_OWNER: {
        "org:manage",
        "project:all",
        "asset:all",
        "activity:all",
        "team:manage",
        "billing:manage",
        "report:all",
        "ledger:all",
        "audit:read",
    },
    ROLE_ORG_ADMIN: {
        "org:read",
        "org:update",
        "project:all",
        "asset:all",
        "activity:all",
        "team:manage",
        "billing:read",
        "report:all",
        "ledger:all",
        "audit:read",
    },
    ROLE_PROJECT_MANAGER: {
        "project:read",
        "project:update",
        "asset:all",
        "activity:all",
        "team:manage",
        "report:all",
        "ledger:read",
        "audit:read",
    },
    ROLE_FIELD_SUPERVISOR: {
        "project:read",
        "asset:read",
        "activity:create",
        "activity:read",
        "activity:update",
        "team:manage",
    },
    ROLE_FIELD_AGENT: {"activity:create", "activity:read", "asset:read"},
    ROLE_QA_OFFICER: {
        "project:read",
        "asset:read",
        "activity:read",
        "activity:verify",
        "report:read",
        "ledger:read",
    },
    ROLE_VERIFIER: {
        "project:read",
        "asset:read",
        "activity:read",
        "activity:verify",
        "report:read",
        "ledger:read",
        "audit:write",
    },
    ROLE_AUDITOR: {
        "project:read",
        "asset:read",
        "activity:read",
        "report:read",
        "ledger:read",
        "audit:read",
    },
    ROLE_INVESTOR: {"project:read", "asset:read", "report:read", "ledger:read"},
    ROLE_OBSERVER: {"project:read", "asset:read"},
    ROLE_VIEWER: {"project:read", "asset:read", "activity:read", "report:read"},
}


def has_permission(user_role: str, permission: str) -> bool:
    """
    Check if a user role has the required permission.
    Maps legacy 'admin' to ORG_ADMIN for backward compatibility.
    """
    if not user_role:
        return False

    role_normalized = "ORG_ADMIN" if user_role.lower() == "admin" else user_role

    # Find the matching key in ROLE_PERMISSIONS case-insensitively
    matched_role = None
    for k in ROLE_PERMISSIONS.keys():
        if k.lower() == role_normalized.lower():
            matched_role = k
            break

    if not matched_role:
        return False

    # SUPER_ADMIN bypasses all checks
    if matched_role == ROLE_PLATFORM_SUPER_ADMIN:
        return True

    permissions = ROLE_PERMISSIONS.get(matched_role, set())

    if permission in permissions:
        return True

    # Check wildcard categories (e.g. 'project:all' satisfies 'project:read')
    category = permission.split(":")[0]
    if f"{category}:all" in permissions:
        return True

    return False


def require_permission(permission: str, entity_type: str = None):
    """
    FastAPI dependency factory that returns a dependency function
    gating routes based on the required permission.
    In Level 5 CIOS, this also integrates with the ABAC Policy Engine if an entity_type is specified.
    """

    async def dependency(
        user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
    ) -> User:
        if not has_permission(user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access Denied: Missing required permission '{permission}'",
            )

        # If an entity context is provided at the route level, ABAC is evaluated later in the endpoint logic
        # Since we don't have entity_id at the dependency injection level easily, we pass the user.
        return user

    return dependency
