import json
import logging
from typing import Dict, Set

from app.core.redis import get_redis_client

logger = logging.getLogger("verifield.rbac")

# Atomic Permission Definitions
CREATE_PROJECT = "CreateProject"
APPROVE_ACTIVITY = "ApproveActivity"
EXPORT_REGISTRY = "ExportRegistry"
MANAGE_USERS = "ManageUsers"
VIEW_LEDGER = "ViewLedger"
CREATE_ACTIVITY = "CreateActivity"
READ_ACTIVITY = "ReadActivity"
UPDATE_ACTIVITY = "UpdateActivity"
DELETE_ACTIVITY = "DeleteActivity"
VERIFY_ACTIVITY = "VerifyActivity"
MANAGE_JURISDICTIONS = "ManageJurisdictions"
MANAGE_ACCREDITATIONS = "ManageAccreditations"
RUN_COMPLIANCE = "RunCompliance"
VIEW_REPORT = "ViewReport"
MANAGE_ORG = "ManageOrg"

# Role definitions
ROLE_PLATFORM_SUPER_ADMIN = "SUPER_ADMIN"
ROLE_COMPLIANCE_ADMIN = "COMPLIANCE_ADMIN"
ROLE_PLATFORM_SUPPORT = "PLATFORM_SUPPORT"
ROLE_JURISDICTION_ADMIN = "JURISDICTION_ADMIN"
ROLE_REGISTRY_ADMIN = "REGISTRY_ADMIN"
ROLE_ORG_OWNER = "ORG_OWNER"
ROLE_ORG_ADMIN = "ORG_ADMIN"
ROLE_PROJECT_MANAGER = "PROJECT_MANAGER"
ROLE_FIELD_SUPERVISOR = "FIELD_SUPERVISOR"
ROLE_FIELD_AGENT = "field_agent"
ROLE_QA_OFFICER = "QA_OFFICER"
ROLE_VERIFIER = "VERIFIER"
ROLE_AUDITOR = "AUDITOR"
ROLE_INVESTOR = "INVESTOR"
ROLE_OBSERVER = "OBSERVER"
ROLE_VIEWER = "VIEWER"

# Roles to Atomic Permissions Mapping
ROLE_PERMISSIONS_MAP: Dict[str, Set[str]] = {
    ROLE_PLATFORM_SUPER_ADMIN: {
        CREATE_PROJECT,
        APPROVE_ACTIVITY,
        EXPORT_REGISTRY,
        MANAGE_USERS,
        VIEW_LEDGER,
        CREATE_ACTIVITY,
        READ_ACTIVITY,
        UPDATE_ACTIVITY,
        DELETE_ACTIVITY,
        VERIFY_ACTIVITY,
        MANAGE_JURISDICTIONS,
        MANAGE_ACCREDITATIONS,
        RUN_COMPLIANCE,
        VIEW_REPORT,
        MANAGE_ORG,
    },
    ROLE_COMPLIANCE_ADMIN: {
        MANAGE_ACCREDITATIONS,
        RUN_COMPLIANCE,
        READ_ACTIVITY,
        VIEW_REPORT,
    },
    ROLE_PLATFORM_SUPPORT: {READ_ACTIVITY, VIEW_REPORT, VIEW_LEDGER},
    ROLE_JURISDICTION_ADMIN: {
        MANAGE_JURISDICTIONS,
        READ_ACTIVITY,
        VIEW_REPORT,
        RUN_COMPLIANCE,
    },
    ROLE_REGISTRY_ADMIN: {READ_ACTIVITY, VIEW_LEDGER, VIEW_REPORT},
    ROLE_ORG_OWNER: {
        CREATE_PROJECT,
        EXPORT_REGISTRY,
        MANAGE_USERS,
        VIEW_LEDGER,
        CREATE_ACTIVITY,
        READ_ACTIVITY,
        UPDATE_ACTIVITY,
        DELETE_ACTIVITY,
        RUN_COMPLIANCE,
        VIEW_REPORT,
        MANAGE_ORG,
    },
    ROLE_ORG_ADMIN: {
        CREATE_PROJECT,
        MANAGE_USERS,
        VIEW_LEDGER,
        CREATE_ACTIVITY,
        READ_ACTIVITY,
        UPDATE_ACTIVITY,
        RUN_COMPLIANCE,
        VIEW_REPORT,
        MANAGE_ORG,
    },
    ROLE_PROJECT_MANAGER: {
        CREATE_PROJECT,
        CREATE_ACTIVITY,
        READ_ACTIVITY,
        UPDATE_ACTIVITY,
        VIEW_REPORT,
        VIEW_LEDGER,
    },
    ROLE_FIELD_SUPERVISOR: {CREATE_ACTIVITY, READ_ACTIVITY, UPDATE_ACTIVITY},
    ROLE_FIELD_AGENT: {CREATE_ACTIVITY, READ_ACTIVITY},
    ROLE_QA_OFFICER: {READ_ACTIVITY, VERIFY_ACTIVITY, VIEW_REPORT, VIEW_LEDGER},
    ROLE_VERIFIER: {READ_ACTIVITY, VERIFY_ACTIVITY, VIEW_REPORT, VIEW_LEDGER},
    ROLE_AUDITOR: {READ_ACTIVITY, VIEW_REPORT, VIEW_LEDGER},
    ROLE_INVESTOR: {READ_ACTIVITY, VIEW_REPORT, VIEW_LEDGER},
    ROLE_OBSERVER: {READ_ACTIVITY},
    ROLE_VIEWER: {READ_ACTIVITY, VIEW_REPORT},
}


async def load_rbac_cache():
    """Seeds and caches the RBAC mapping in Redis."""
    try:
        r = get_redis_client()
        for role, perms in ROLE_PERMISSIONS_MAP.items():
            await r.set(f"rbac:role:{role}", json.dumps(list(perms)))
        logger.info("Successfully loaded RBAC permissions cache in Redis")
    except Exception as e:
        logger.error(f"Failed to load RBAC permissions cache: {e}")


async def has_permission(user_role: str, permission: str) -> bool:
    """Checks if a role possesses the specified atomic permission (uses Redis cache)."""
    # Normalize legacy role
    role = ROLE_ORG_ADMIN if user_role == "admin" else user_role

    if role == ROLE_PLATFORM_SUPER_ADMIN:
        return True

    try:
        r = get_redis_client()
        cached = await r.get(f"rbac:role:{role}")
        if cached:
            perms = json.loads(cached)
            return permission in perms
    except Exception as e:
        logger.error(f"Redis RBAC lookup error: {e}")

    # Fallback to local map
    return permission in ROLE_PERMISSIONS_MAP.get(role, set())
