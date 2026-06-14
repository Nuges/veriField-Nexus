"""
=============================================================================
VeriField Nexus — Access Request & Super Admin API Routes
=============================================================================
Endpoints for public access lead submission, and admin-only dashboard management.
=============================================================================
"""

import uuid
import random
import string
import logging
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.db.session import get_db
from app.models.user import User
from app.models.organization import Organization
from app.models.access_request import AccessRequest
from app.core.security import require_super_admin, get_password_hash
from app.schemas.access_request import (
    AccessRequestCreate,
    AccessRequestResponse,
    AccessRequestApprovalResponse
)
from app.schemas.user import UserResponse

logger = logging.getLogger("verifield.admin")
router = APIRouter(tags=["Super Admin Governance"])


# Helper to generate a readable temporary password
def generate_temp_password(length=10) -> str:
    # Capital letter, lowercase, number, special sign
    caps = string.ascii_uppercase
    lowers = string.ascii_lowercase
    digits = string.digits
    all_chars = caps + lowers + digits
    
    password = [
        random.choice(caps),
        random.choice(lowers),
        random.choice(digits)
    ]
    for _ in range(length - 3):
        password.append(random.choice(all_chars))
    
    random.shuffle(password)
    return "VF-" + "".join(password)


# =============================================================================
# POST /api/v1/access-requests — Public Onboarding Request
# =============================================================================
@router.post(
    "/access-requests",
    status_code=status.HTTP_201_CREATED,
    summary="Submit onboarding access request",
    description="Public endpoint to request platform organization provisioning."
)
async def submit_access_request(
    payload: AccessRequestCreate,
    db: AsyncSession = Depends(get_db)
):
    # Check if a request already exists with this email
    stmt = select(AccessRequest).where(AccessRequest.email == payload.email)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing and existing.status == "PENDING":
        return {
            "status": "PENDING_REVIEW",
            "message": "An onboarding request for this email is already under review by a Super Admin."
        }

    # Save request
    req = AccessRequest(
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        organization_name=payload.organization_name,
        country=payload.country,
        use_case=payload.use_case,
        status="PENDING"
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)

    logger.info(f"Access request submitted for {payload.email} (Org: {payload.organization_name})")
    
    return {
        "status": "PENDING_REVIEW",
        "message": "Your request is under review by Super Admin"
    }


# =============================================================================
# GET /api/v1/admin/access-requests — Super Admin List
# =============================================================================
@router.get(
    "/admin/access-requests",
    response_model=List[AccessRequestResponse],
    summary="List onboarding access requests (Super Admin)",
)
async def list_access_requests(
    status_filter: Optional[str] = Query(None, alias="status"),
    country_filter: Optional[str] = Query(None, alias="country"),
    org_filter: Optional[str] = Query(None, alias="organization_name"),
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_super_admin)
):
    stmt = select(AccessRequest).order_by(desc(AccessRequest.created_at))
    if status_filter:
        stmt = stmt.where(AccessRequest.status == status_filter.upper())
    if country_filter:
        stmt = stmt.where(AccessRequest.country == country_filter)
    if org_filter:
        stmt = stmt.where(AccessRequest.organization_name.ilike(f"%{org_filter}%"))

    result = await db.execute(stmt)
    return result.scalars().all()


# =============================================================================
# POST /api/v1/admin/access-requests/{id}/approve — Approve Request
# =============================================================================
@router.post(
    "/admin/access-requests/{id}/approve",
    response_model=AccessRequestApprovalResponse,
    summary="Approve access request & provision tenant (Super Admin)",
)
async def approve_access_request(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_super_admin)
):
    # Fetch request
    stmt = select(AccessRequest).where(AccessRequest.id == id)
    result = await db.execute(stmt)
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Access request not found")

    if req.status != "PENDING":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve request in '{req.status}' state."
        )

    # 1. Provision Organization
    org_stmt = select(Organization).where(Organization.name == req.organization_name)
    org_result = await db.execute(org_stmt)
    org = org_result.scalar_one_or_none()
    if not org:
        org = Organization(
            name=req.organization_name,
            created_by=admin_user.id,
            status="ACTIVE"
        )
        db.add(org)
        await db.flush()  # Capture org ID for user mapping

    # 2. Check if Org Admin User already exists
    user_stmt = select(User).where(User.email == req.email)
    user_result = await db.execute(user_stmt)
    existing_user = user_result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail=f"A user with email '{req.email}' already exists in the system."
        )

    # 3. Generate credentials for ORG_ADMIN
    temp_pw = generate_temp_password()
    pw_hash = get_password_hash(temp_pw)

    # Determine sector dynamically from use case (e.g. "ENERGY - ...", "COOKSTOVE - ...", "SOLAR - ...")
    assigned_sector = "cookstove"
    if req.use_case:
        use_case_upper = req.use_case.upper()
        if any(prefix in use_case_upper for prefix in ("ENERGY", "SOLAR", "HYBRID")):
            assigned_sector = "energy"

    # Provision in Supabase Auth
    supabase_user_id = None
    try:
        import httpx
        from app.core.config import settings
        admin_key = settings.supabase_admin_key
        async with httpx.AsyncClient(timeout=30.0) as client:
            auth_data = {
                "email": req.email,
                "password": temp_pw,
                "email_confirm": True,
                "phone_confirm": True,
            }
            response = await client.post(
                f"{settings.supabase_url}/auth/v1/admin/users",
                json=auth_data,
                headers={
                    "apikey": admin_key,
                    "Authorization": f"Bearer {admin_key}",
                    "Content-Type": "application/json",
                },
            )

            if response.status_code not in (200, 201):
                error_detail = response.json().get("msg", "Registration failed")
                logger.warning(f"Supabase Auth provisioning failed for access request: {error_detail}")
                if not settings.dev_mode:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Auth Service Error: {error_detail}",
                    )
            else:
                auth_result = response.json()
                user_id_str = auth_result.get("id") or auth_result.get("user", {}).get("id")
                if user_id_str:
                    supabase_user_id = uuid.UUID(user_id_str)
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        logger.warning(f"Failed to create user in Supabase Auth: {e}")
        if not settings.dev_mode:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Auth server unreachable: {str(e)}",
            )

    # If we couldn't get a Supabase ID (e.g., in dev mode fallback), generate a local UUID
    if supabase_user_id is None:
        supabase_user_id = uuid.uuid4()
        logger.info(f"DEV MODE fallback: generated local UUID {supabase_user_id} for {req.email}")

    org_admin = User(
        id=supabase_user_id,
        email=req.email,
        full_name=req.full_name,
        role="ORG_ADMIN",  # Tenant-level control
        organization=org.name,
        organization_id=org.id,
        password_hash=pw_hash,
        requires_password_change=True,
        is_active=True,
        status="active",
        sector=assigned_sector,
        country=req.country
    )
    db.add(org_admin)

    # 4. Update request status
    req.status = "APPROVED"
    req.reviewed_by = admin_user.id
    req.reviewed_at = datetime.now(timezone.utc)

    await db.commit()

    # 5. Simulate Onboarding Email Delivery in Logs
    mock_email = (
        f"\n\n============================================================\n"
        f"📧 [MOCK EMAIL SERVICE] Delivery to: {req.email}\n"
        f"Subject: VeriField Nexus Access Request Approved!\n"
        f"------------------------------------------------------------\n"
        f"Welcome to VeriField Nexus, {req.full_name}!\n"
        f"Your organization workspace '{org.name}' has been created.\n\n"
        f"Login Details:\n"
        f"- Portal Url: http://localhost:3000/login\n"
        f"- Username/Email: {req.email}\n"
        f"- Temporary Password: {temp_pw}\n\n"
        f"Security Requirement: You must rotate your password on your first login.\n"
        f"============================================================\n"
    )
    print(mock_email)
    logger.info(f"Access request {id} approved. Tenant Admin created: {req.email}")

    return AccessRequestApprovalResponse(
        message="Onboarding request approved. Organization and tenant administrator created successfully.",
        organization_id=org.id,
        organization_name=org.name,
        org_admin_email=req.email,
        temporary_password=temp_pw
    )


# =============================================================================
# POST /api/v1/admin/access-requests/{id}/reject — Reject Request
# =============================================================================
@router.post(
    "/admin/access-requests/{id}/reject",
    response_model=AccessRequestResponse,
    summary="Reject access request (Super Admin)",
)
async def reject_access_request(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_super_admin)
):
    stmt = select(AccessRequest).where(AccessRequest.id == id)
    result = await db.execute(stmt)
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Access request not found")

    if req.status != "PENDING":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reject request in '{req.status}' state."
        )

    req.status = "REJECTED"
    req.reviewed_by = admin_user.id
    req.reviewed_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(req)

    logger.info(f"Access request {id} rejected by Super Admin {admin_user.email}")
    return req


# =============================================================================
# GET /api/v1/admin/organizations — List Tenants (Super Admin)
# =============================================================================
@router.get(
    "/admin/organizations",
    summary="List all SaaS tenant organizations (Super Admin)",
)
async def list_organizations(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_super_admin)
):
    stmt = select(Organization).order_by(Organization.created_at.desc())
    result = await db.execute(stmt)
    orgs = result.scalars().all()
    return orgs


# =============================================================================
# GET /api/v1/admin/users — List Users Globally (Super Admin)
# =============================================================================
@router.get(
    "/admin/users",
    response_model=List[UserResponse],
    summary="List all users globally across tenants (Super Admin)",
)
async def list_users_global(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_super_admin)
):
    stmt = select(User).order_by(User.created_at.desc())
    result = await db.execute(stmt)
    users = result.scalars().all()
    return users


# =============================================================================
# PATCH /api/v1/admin/users/{id}/status — Toggle Suspend Status (Super Admin)
# =============================================================================
from pydantic import BaseModel

class UserStatusToggle(BaseModel):
    is_active: bool

@router.patch(
    "/admin/users/{id}/status",
    response_model=UserResponse,
    summary="Toggle user suspension status (Super Admin)",
)
async def toggle_user_suspension(
    id: uuid.UUID,
    payload: UserStatusToggle,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_super_admin)
):
    stmt = select(User).where(User.id == id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = payload.is_active
    user.status = "active" if payload.is_active else "suspended"
    await db.commit()
    await db.refresh(user)

    logger.info(f"User {user.email} status toggled is_active={payload.is_active} by Super Admin")
    return user


# =============================================================================
# GET /api/v1/admin/audit-logs — Super Admin Audit Timeline
# =============================================================================
@router.get(
    "/admin/audit-logs",
    summary="Fetch platform governance audit logs (Super Admin)",
)
async def get_audit_logs(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_super_admin)
):
    # Construct a high-fidelity dynamic audit log sequence based on database actions
    logs = []
    
    # 1. Base log (Super Admin creation)
    sa_stmt = select(User).where(User.role == "SUPER_ADMIN").order_by(User.created_at.asc()).limit(1)
    sa_res = await db.execute(sa_stmt)
    sa_user = sa_res.scalar_one_or_none()
    
    bootstrap_timestamp = "2026-06-12 12:00:00"
    bootstrap_email = "superadmin@verifield.io"
    if sa_user:
        bootstrap_timestamp = sa_user.created_at.strftime("%Y-%m-%d %H:%M:%S")
        bootstrap_email = sa_user.email

    logs.append({
        "timestamp": bootstrap_timestamp,
        "action": "SUPER_ADMIN_BOOTSTRAP",
        "details": f"Super Admin system user '{bootstrap_email}' initialized.",
        "user": "System Seed"
    })

    # 2. Query access requests reviews
    req_stmt = select(AccessRequest).where(AccessRequest.status != "PENDING").order_by(AccessRequest.reviewed_at.asc())
    req_res = await db.execute(req_stmt)
    requests = req_res.scalars().all()
    for req in requests:
        status_action = "REQUEST_APPROVED" if req.status == "APPROVED" else "REQUEST_REJECTED"
        logs.append({
            "timestamp": req.reviewed_at.strftime("%Y-%m-%d %H:%M:%S") if req.reviewed_at else req.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "action": status_action,
            "details": f"Access Request for '{req.organization_name}' ({req.email}) reviewed status: {req.status}",
            "user": "superadmin@verifield.io"
        })

    # 3. Query created users
    users_stmt = select(User).where(User.email != "superadmin@verifield.io").order_by(User.created_at.asc())
    users_res = await db.execute(users_stmt)
    users = users_res.scalars().all()
    for u in users:
        logs.append({
            "timestamp": u.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "action": "USER_PROVISIONED",
            "details": f"User '{u.email}' created with role={u.role} in organization={u.organization or 'None'}",
            "user": "System Ingestion" if u.role == "field_agent" else "superadmin@verifield.io"
        })

    # Sort logs by timestamp descending
    logs.sort(key=lambda x: x["timestamp"], reverse=True)
    return logs[:50]


# =============================================================================
# DELETE /api/v1/admin/organizations/{id} — Delete Tenant (Super Admin)
# =============================================================================
@router.delete(
    "/admin/organizations/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a SaaS tenant organization (Super Admin)",
)
async def delete_organization(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_super_admin)
):
    stmt = select(Organization).where(Organization.id == id)
    result = await db.execute(stmt)
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Deactivate / suspend all users belonging to this organization
    users_stmt = select(User).where(User.organization == org.name)
    users_res = await db.execute(users_stmt)
    users = users_res.scalars().all()
    for u in users:
        u.is_active = False
        u.status = "suspended"
        u.organization = None
        u.organization_id = None

    # Delete the organization
    await db.delete(org)
    await db.commit()

    logger.info(f"Organization '{org.name}' and its users suspended by Super Admin")
    return None


# =============================================================================
# GET /api/v1/admin/organizations/{id}/analytics — Dynamic Tenant Analytics (Super Admin)
# =============================================================================
@router.get(
    "/admin/organizations/{id}/analytics",
    summary="Fetch dynamic real-time analytics for a specific SaaS tenant (Super Admin)",
)
async def get_organization_analytics(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_super_admin)
):
    from sqlalchemy import func
    from app.models.property import Property
    from app.models.activity import Activity
    from app.models.carbon_calculation import CarbonCalculation

    # Fetch organization
    org_stmt = select(Organization).where(Organization.id == id)
    org_res = await db.execute(org_stmt)
    org = org_res.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    org_name = org.name

    # 1. User Counts
    users_stmt = select(func.count(User.id)).where(User.organization == org_name)
    users_res = await db.execute(users_stmt)
    user_count = users_res.scalar() or 0

    # Role breakdown
    role_stmt = select(User.role, func.count(User.id)).where(User.organization == org_name).group_by(User.role)
    role_res = await db.execute(role_stmt)
    roles = {row[0]: row[1] for row in role_res.all()}

    # 2. Properties (Installations) Counts
    props_stmt = select(func.count(Property.id)).join(User, Property.owner_id == User.id).where(User.organization == org_name)
    props_res = await db.execute(props_stmt)
    properties_count = props_res.scalar() or 0

    # 3. Activities Counts
    acts_stmt = select(func.count(Activity.id)).join(User, Activity.user_id == User.id).where(User.organization == org_name)
    acts_res = await db.execute(acts_stmt)
    activities_count = acts_res.scalar() or 0

    # Average Trust Score
    trust_stmt = select(func.avg(Activity.trust_score)).join(User, Activity.user_id == User.id).where(
        User.organization == org_name,
        Activity.trust_score.isnot(None)
    )
    trust_res = await db.execute(trust_stmt)
    avg_trust = float(trust_res.scalar() or 0.0)

    # 4. Carbon Reductions sum (tCO2e generated)
    carbon_stmt = select(func.sum(CarbonCalculation.tco2e_generated)).\
        join(Activity, CarbonCalculation.activity_id == Activity.id).\
        join(User, Activity.user_id == User.id).\
        where(User.organization == org_name)
    carbon_res = await db.execute(carbon_stmt)
    total_co2 = float(carbon_res.scalar() or 0.0)

    # 5. Sector Mix Breakdown based on users registered in the organization
    sector_stmt = select(User.sector, func.count(User.id)).where(User.organization == org_name).group_by(User.sector)
    sector_res = await db.execute(sector_stmt)
    sector_mix = {row[0]: row[1] for row in sector_res.all()}

    # Group metrics
    return {
        "organization_id": str(org.id),
        "organization_name": org.name,
        "created_at": org.created_at.isoformat(),
        "status": org.status,
        "metrics": {
            "users_count": user_count,
            "roles": roles,
            "installations_count": properties_count,
            "activities_count": activities_count,
            "average_trust_score": round(avg_trust, 1),
            "total_co2_offset": round(total_co2, 2),
            "sector_mix": sector_mix
        }
    }


# =============================================================================
# POST /api/v1/admin/users/{id}/reset-password — Reset User Password (Super Admin)
# =============================================================================
from pydantic import Field

class AdminUserPasswordReset(BaseModel):
    new_password: str = Field(..., min_length=8)

@router.post(
    "/admin/users/{id}/reset-password",
    summary="Force reset user password (Super Admin)",
)
async def reset_user_password(
    id: uuid.UUID,
    payload: AdminUserPasswordReset,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_super_admin)
):
    stmt = select(User).where(User.id == id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    from app.core.security import get_password_hash
    user.password_hash = get_password_hash(payload.new_password)
    user.requires_password_change = False
    await db.commit()

    logger.info(f"Password reset forced for user {user.email} by Super Admin")
    return {"message": f"Password for {user.email} successfully updated."}


# =============================================================================
# GET /api/v1/admin/global-analytics — Global telemetry metrics (Super Admin)
# =============================================================================
@router.get(
    "/admin/global-analytics",
    summary="Fetch dynamic global telemetry metrics across all tenants (Super Admin)",
)
async def get_global_analytics(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_super_admin)
):
    from sqlalchemy import func
    from app.models.property import Property
    from app.models.activity import Activity
    from app.models.carbon_calculation import CarbonCalculation
    from app.models.organization import Organization

    # 1. Total installations (Property objects)
    props_stmt = select(func.count(Property.id))
    props_res = await db.execute(props_stmt)
    properties_count = props_res.scalar() or 0

    # 2. Average trust score across all activities
    trust_stmt = select(func.avg(Activity.trust_score)).where(Activity.trust_score.isnot(None))
    trust_res = await db.execute(trust_stmt)
    avg_trust = float(trust_res.scalar() or 0.0)

    # 3. Total CO2 offset (CarbonCalculation.tco2e_generated)
    carbon_stmt = select(func.sum(CarbonCalculation.tco2e_generated))
    carbon_res = await db.execute(carbon_stmt)
    total_co2 = float(carbon_res.scalar() or 0.0)

    # 4. Total registered organizations
    orgs_stmt = select(func.count(Organization.id))
    orgs_res = await db.execute(orgs_stmt)
    orgs_count = orgs_res.scalar() or 0

    # 5. Sector breakdown based on ORG_ADMIN users
    sector_stmt = select(User.sector, func.count(User.id)).where(User.role == "ORG_ADMIN").group_by(User.sector)
    sector_res = await db.execute(sector_stmt)
    sectors = {row[0]: row[1] for row in sector_res.all()}

    return {
        "installations": properties_count,
        "avgTrust": round(avg_trust, 1),
        "tCO2": round(total_co2, 2),
        "activeOrgs": orgs_count,
        "sectors": {
            "cookstove": sectors.get("cookstove", 0),
            "energy": sectors.get("energy", 0)
        }
    }


