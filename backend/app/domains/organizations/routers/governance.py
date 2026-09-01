"""

=============================================================================

VeriField Nexus — Super Admin Governance Router

=============================================================================

Provides platform-wide account management, project-user graph navigation,

activity summaries, security audits, suspension, reactivation, password reset,

and deactivation workflows for Platform Super Admins.

=============================================================================

"""



import uuid

from datetime import datetime, timezone

from typing import Any, Dict, List, Optional



from fastapi import APIRouter, Depends, HTTPException, Query, status

from pydantic import BaseModel, EmailStr

from sqlalchemy import func, or_, select, text

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload



from app.core.event_bus import EventBus
from app.core.rbac import ALL_ROLES, normalize_role
from app.core.security import get_current_user, get_password_hash
from app.db.session import get_db

from app.domains.activities.models import Activity

from app.domains.assets.models import Asset

from app.domains.authentication.models import ProjectMembership, SecurityAuditLog, User

from app.domains.authentication.schemas import (

    AdminUserCreatePayload,

    AdminUserCreateResponse,

    UserResponse,

)

from app.domains.authentication.validators import validate_password_strength

from app.domains.evidence.models import Evidence

from app.domains.organizations.models import Organization

from app.domains.projects.models import Project



router = APIRouter(prefix="/admin", tags=["Super Admin Governance"])





def _verify_super_admin(user: User):
    """Enforce platform-wide Super Admin authority."""
    if user.role != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform-wide Super Admin authority required."
        )





class PasswordResetPayload(BaseModel):

    new_password: str





class SuspendUserPayload(BaseModel):
    reason: Optional[str] = "Suspended by Super Admin governance policy"


class UserGovernanceUpdatePayload(BaseModel):
    role: Optional[str] = None
    organization_id: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    status: Optional[str] = None





async def provision_user_account(

    db: AsyncSession,

    actor_user: User,

    full_name: str,

    email: str,

    role: str,

    organization_id: Optional[uuid.UUID] = None,

    phone: Optional[str] = None,

    job_title: Optional[str] = None,

    custom_password: Optional[str] = None,

    project_memberships: Optional[List[Dict[str, Any]]] = None,

    meta_data: Optional[Dict[str, Any]] = None,

) -> Dict[str, Any]:

    """

    Authoritative account provisioning service for Platform Super Admins & Organization Admins.

    Enforces RBAC/ABAC boundaries, tenant isolation, role validation, project memberships,

    temporary credential generation, and immutable audit logging.

    """

    normalized_email = email.strip().lower()



    # 1. Validate email uniqueness

    existing_res = await db.execute(select(User).where(func.lower(User.email) == normalized_email, User.is_deleted == False))

    if existing_res.scalar_one_or_none():

        raise HTTPException(

            status_code=status.HTTP_400_BAD_REQUEST,

            detail=f"User account with email '{normalized_email}' already exists."

        )



    # 2. Validate role catalogue using canonical RBAC normalization
    canonical_role = normalize_role(role)
    if not canonical_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role '{role}'. Must be one of {sorted(list(ALL_ROLES))}"
        )

    # Invariant: Only segunoluwole22@gmail.com may hold the SUPER_ADMIN role
    if canonical_role == "SUPER_ADMIN" and normalized_email != "segunoluwole22@gmail.com":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot provision unauthorized SUPER_ADMIN account."
        )

    # Coerce organization_id to UUID if string is passed
    target_org_id: Optional[uuid.UUID] = None
    if organization_id and str(organization_id).strip() and str(organization_id).strip().lower() != "null":
        if isinstance(organization_id, uuid.UUID):
            target_org_id = organization_id
        else:
            try:
                target_org_id = uuid.UUID(str(organization_id).strip())
            except ValueError:
                target_org_id = None

    # 3. RBAC / ABAC Boundary Checks for Org Admins
    actor_canonical = normalize_role(actor_user.role)
    if actor_canonical == "ORG_ADMIN":
        # Org Admins cannot create users in another organization
        if target_org_id and str(target_org_id) != str(actor_user.organization_id):
            audit_entry = SecurityAuditLog(
                id=uuid.uuid4(),
                actor_user_id=actor_user.id,
                target_user_id=None,
                organization_id=target_org_id,
                action="ACCOUNT_CREATION_DENIED",
                result="FORBIDDEN",
                metadata_json={
                    "attempted_role": role,
                    "attempted_org": str(target_org_id),
                    "reason": "Cross-tenant account creation attempted by Org Admin"
                }
            )
            db.add(audit_entry)
            await db.commit()

            await EventBus.publish(
                stream_name="access_events",
                event_type="AccountCreationDenied",
                payload={
                    "actor_user_id": str(actor_user.id),
                    "attempted_role": role,
                    "reason": "Cross-tenant organization restriction",
                    "result": "FORBIDDEN",
                },
                actor_id=str(actor_user.id)
            )

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Organization Administrators cannot create accounts for another organization."
            )

        # Org Admins cannot create Super Admin or Org Admin accounts
        if canonical_role in ("SUPER_ADMIN", "ORG_ADMIN"):
            audit_entry = SecurityAuditLog(
                id=uuid.uuid4(),
                actor_user_id=actor_user.id,
                target_user_id=None,
                organization_id=actor_user.organization_id,
                action="ACCOUNT_CREATION_DENIED",
                result="FORBIDDEN",
                metadata_json={
                    "attempted_role": role,
                    "reason": "Role escalation attempted by Org Admin"
                }
            )
            db.add(audit_entry)
            await db.commit()

            await EventBus.publish(
                stream_name="access_events",
                event_type="AccountCreationDenied",
                payload={
                    "actor_user_id": str(actor_user.id),
                    "attempted_role": role,
                    "reason": "Role escalation policy restriction",
                    "result": "FORBIDDEN",
                },
                actor_id=str(actor_user.id)
            )

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Organization Administrators cannot provision Super Admin or Organization Admin accounts."
            )

        target_org_id = actor_user.organization_id

    # Fallback Step 1: If organization_id is missing, attempt resolution by organization name if supplied (or create new)
    requested_org_name = (meta_data or {}).get("organization") or (meta_data or {}).get("organization_name")
    if not target_org_id and requested_org_name and str(requested_org_name).strip():
        clean_name = str(requested_org_name).strip()
        org_lookup = await db.execute(
            select(Organization).where(
                func.lower(Organization.name) == clean_name.lower()
            )
        )
        found_org = org_lookup.scalars().first()
        if found_org:
            target_org_id = found_org.id
        else:
            # Auto-create new organization when provisioning Admin with new org name
            new_org = Organization(
                id=uuid.uuid4(),
                name=clean_name,
                org_type="DEVELOPER",
                status="ACTIVE",
            )
            db.add(new_org)
            await db.flush()
            target_org_id = new_org.id

    # Fallback Step 2: If target_org_id is missing, check actor_user's organization_id
    if not target_org_id and actor_user.organization_id:
        target_org_id = actor_user.organization_id

    # Fallback Step 3: If target_org_id is missing, query primary active organization in system
    if not target_org_id and canonical_role != "SUPER_ADMIN":
        first_org_res = await db.execute(select(Organization).where(Organization.is_deleted == False).order_by(Organization.created_at.asc()).limit(1))
        first_org = first_org_res.scalars().first()
        if first_org:
            target_org_id = first_org.id

    # Fallback Step 4: If no organization exists in system at all, auto-provision default Primary Tenant Organization
    if not target_org_id and canonical_role != "SUPER_ADMIN":
        default_org = Organization(
            id=uuid.uuid4(),
            name="VeriField Primary Tenant",
            org_type="DEVELOPER",
            status="ACTIVE",
        )
        db.add(default_org)
        await db.flush()
        target_org_id = default_org.id

    # Non-Super Admin roles require an organization_id
    if canonical_role != "SUPER_ADMIN" and not target_org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Target organization_id is required for role '{canonical_role}'."
        )

    # 4. Resolve Organization Name
    org_name = None
    if target_org_id:
        org_res = await db.execute(select(Organization).where(Organization.id == target_org_id))
        org = org_res.scalar_one_or_none()
        if not org:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target organization not found.")
        org_name = org.name

    # 5. Generate secure temporary password
    temp_pw = custom_password
    if not temp_pw:
        temp_pw = f"Temp-{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[:4].upper()}!"

    password_hash = get_password_hash(temp_pw)

    # 6. Create User record
    new_user = User(
        id=uuid.uuid4(),
        email=normalized_email,
        phone=phone,
        full_name=full_name.strip(),
        role=canonical_role,
        status="active",
        is_active=True,
        organization=org_name,

        organization_id=target_org_id,

        password_hash=password_hash,

        requires_password_change=True,

        meta_data={

            **(meta_data or {}),

            "job_title": job_title,

            "created_by_actor_id": str(actor_user.id),

            "created_by_actor_role": actor_user.role,

            "provisioned_at": datetime.now(timezone.utc).isoformat(),

        }

    )

    db.add(new_user)

    await db.flush()



    # 7. Create Project Memberships

    assigned_memberships = []

    if project_memberships:

        for pm in project_memberships:

            p_id = pm.get("project_id") if isinstance(pm, dict) else getattr(pm, "project_id", None)

            p_role = pm.get("role", "FIELD_AGENT") if isinstance(pm, dict) else getattr(pm, "role", "FIELD_AGENT")



            if not p_id:

                continue



            p_uuid = uuid.UUID(str(p_id))

            proj_res = await db.execute(select(Project).where(Project.id == p_uuid))

            proj = proj_res.scalar_one_or_none()

            if not proj:

                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{p_uuid}' not found.")



            # Validate that project belongs to the user's organization

            if target_org_id and proj.organization_id and str(proj.organization_id) != str(target_org_id):

                raise HTTPException(

                    status_code=status.HTTP_400_BAD_REQUEST,

                    detail=f"Project '{proj.name}' does not belong to target organization '{org_name}'."

                )



            pm_row = ProjectMembership(

                id=uuid.uuid4(),

                user_id=new_user.id,

                project_id=proj.id,

                role_code=p_role,

                status="active",

                assigned_by=actor_user.id,

                assigned_at=datetime.now(timezone.utc),

            )

            db.add(pm_row)

            assigned_memberships.append(pm_row)



    # 8. Create Security Audit Log

    audit_entry = SecurityAuditLog(

        id=uuid.uuid4(),

        actor_user_id=actor_user.id,

        target_user_id=new_user.id,

        organization_id=target_org_id,

        action="ACCOUNT_CREATED",

        result="SUCCESS",

        metadata_json={

            "created_by_role": actor_user.role,

            "target_role": new_user.role,

            "requires_password_change": True,

            "job_title": job_title,

            "project_memberships_count": len(assigned_memberships),

        }

    )

    db.add(audit_entry)

    await db.commit()



    await EventBus.publish(

        stream_name="access_events",

        event_type="AccountCreated",

        payload={

            "actor_user_id": str(actor_user.id),

            "target_user_id": str(new_user.id),

            "target_email": new_user.email,

            "organization_id": str(target_org_id) if target_org_id else None,

            "role": new_user.role,

            "result": "SUCCESS",

        },

        actor_id=str(actor_user.id)

    )



    return {

        "user": new_user,

        "temporary_password": temp_pw,

        "assigned_memberships_count": len(assigned_memberships),

        "message": f"Account '{new_user.email}' provisioned successfully.",

    }





# ---------------------------------------------------------------------------

# 1. Platform-Wide User Provisioning & User Directory APIs

# ---------------------------------------------------------------------------

@router.post("/users", status_code=status.HTTP_201_CREATED, response_model=AdminUserCreateResponse)

async def create_user_account_governance(

    payload: AdminUserCreatePayload,

    db: AsyncSession = Depends(get_db),

    current_user: User = Depends(get_current_user),

):

    """

    Super Admin endpoint for enterprise user account provisioning.

    Supports platform-wide role assignment, organization binding, project membership,

    temporary credential generation, and immutable audit logging.

    """

    _verify_super_admin(current_user)



    res = await provision_user_account(

        db=db,

        actor_user=current_user,

        full_name=payload.full_name,

        email=payload.email,

        role=payload.role,

        organization_id=payload.organization_id,

        phone=payload.phone,

        job_title=payload.job_title,

        custom_password=payload.password,

        project_memberships=[pm.model_dump() for pm in (payload.project_memberships or [])],

        meta_data=payload.meta_data,

    )



    user_obj = res["user"]

    return AdminUserCreateResponse(

        user=UserResponse.model_validate(user_obj),

        temporary_password=res["temporary_password"],

        assigned_memberships_count=res["assigned_memberships_count"],

        message=res["message"],

    )





# ---------------------------------------------------------------------------

# 1. Platform-Wide Users List

# ---------------------------------------------------------------------------

@router.get("/users")

async def list_all_platform_users(

    query: Optional[str] = None,

    role: Optional[str] = None,

    status_filter: Optional[str] = Query(None, alias="status"),

    organization_id: Optional[str] = None,

    page: Optional[int] = Query(None, ge=1),

    per_page: Optional[int] = Query(None, ge=1, le=200),

    db: AsyncSession = Depends(get_db),

    current_user: User = Depends(get_current_user),

):

    """

    Returns platform-wide user directory for Super Admin inspection.

    Includes associated counts (projects, activities, assets, evidence).

    """

    _verify_super_admin(current_user)



    stmt = select(User).where(User.is_deleted == False)



    if role:

        stmt = stmt.where(User.role == role)



    if status_filter:

        stmt = stmt.where(User.status == status_filter)



    if organization_id:

        try:

            org_uuid = uuid.UUID(organization_id)

            stmt = stmt.where(User.organization_id == org_uuid)

        except ValueError:

            pass



    if query:

        q_term = f"%{query.strip().lower()}%"

        stmt = stmt.where(

            or_(

                func.lower(User.full_name).like(q_term),

                func.lower(User.email).like(q_term),

                func.lower(User.organization).like(q_term),

            )

        )



    stmt = stmt.order_by(User.created_at.desc())

    if page is not None and per_page is not None:

        stmt = stmt.offset((page - 1) * per_page).limit(per_page)



    res = await db.execute(stmt)

    users = res.scalars().all()



    # Aggregate summaries for each user

    user_list = []

    for u in users:

        u_id_str = str(u.id)



        # Count activities submitted by user

        act_res = await db.execute(

            select(func.count(Activity.id)).where(Activity.user_id == u.id)

        )

        activities_cnt = act_res.scalar_one_or_none() or 0



        # Count projects owned or associated via organization

        projects_cnt = 0

        if u.organization_id:

            proj_res = await db.execute(

                select(func.count(Project.id)).where(Project.organization_id == u.organization_id)

            )

            projects_cnt = proj_res.scalar_one_or_none() or 0



        # Count assets managed in user's organization

        assets_cnt = 0

        if u.organization_id:

            asset_res = await db.execute(

                select(func.count(Asset.id)).where(Asset.organization_id == u.organization_id)

            )

            assets_cnt = asset_res.scalar_one_or_none() or 0



        # Count evidence submitted by user

        ev_res = await db.execute(

            select(func.count(Evidence.id)).join(Activity, Evidence.activity_id == Activity.id).where(Activity.user_id == u.id)

        )

        evidence_cnt = ev_res.scalar_one_or_none() or 0



        mfa_enabled = bool((u.meta_data or {}).get("mfa", {}).get("enabled", False))



        user_list.append({

            "id": u_id_str,

            "full_name": u.full_name,

            "email": u.email,

            "phone": u.phone,

            "role": u.role,

            "status": u.status,

            "is_active": u.is_active,

            "organization": u.organization,

            "organization_id": str(u.organization_id) if u.organization_id else None,

            "country": u.country,

            "created_at": u.created_at.isoformat() if hasattr(u.created_at, "isoformat") else str(u.created_at),

            "updated_at": u.updated_at.isoformat() if hasattr(u.updated_at, "isoformat") else str(u.updated_at),

            "mfa_enabled": mfa_enabled,

            "projects_count": projects_cnt,

            "activities_count": activities_cnt,

            "assets_count": assets_cnt,

            "evidence_count": evidence_cnt,

            "requires_password_change": u.requires_password_change,

        })



    return user_list





# ---------------------------------------------------------------------------

# 2. Detailed Account Overview View

# ---------------------------------------------------------------------------

@router.get("/users/{user_id}")

async def get_user_detail_governance(

    user_id: uuid.UUID,

    db: AsyncSession = Depends(get_db),

    current_user: User = Depends(get_current_user),

):

    """

    Returns comprehensive account inspection detail for a target user.

    """

    _verify_super_admin(current_user)



    res = await db.execute(select(User).where(User.id == user_id))

    user = res.scalar_one_or_none()

    if not user:

        raise HTTPException(status_code=404, detail="User account not found.")



    u_id_str = str(user.id)



    # 1. Assigned Projects

    projects = []

    if user.organization_id:

        p_res = await db.execute(select(Project).where(Project.organization_id == user.organization_id))

        projects = p_res.scalars().all()



    assigned_projects = []

    for p in projects:

        act_cnt_res = await db.execute(

            select(func.count(Activity.id)).where(Activity.user_id == user.id)

        )

        p_act_cnt = act_cnt_res.scalar_one_or_none() or 0



        asset_cnt_res = await db.execute(

            select(func.count(Asset.id)).where(Asset.organization_id == user.organization_id)

        )

        p_asset_cnt = asset_cnt_res.scalar_one_or_none() or 0



        assigned_projects.append({

            "id": str(p.id),

            "name": p.name,

            "project_code": p.project_code or str(p.id)[:8].upper(),

            "country": p.country,

            "status": getattr(p, "status", "ACTIVE"),

            "sector_id": str(p.sector_id) if p.sector_id else None,

            "methodology_id": str(p.methodology_id) if p.methodology_id else None,

            "activities_count": p_act_cnt,

            "assets_count": p_asset_cnt,

            "role": "Organization Project",

        })



    # Include explicit ProjectMembership records

    pm_res = await db.execute(

        select(ProjectMembership, Project)

        .join(Project, ProjectMembership.project_id == Project.id)

        .where(ProjectMembership.user_id == user.id, ProjectMembership.status == "active")

    )

    for pm, p in pm_res.all():

        assigned_projects.append({

            "id": str(p.id),

            "name": p.name,

            "project_code": p.project_code or str(p.id)[:8].upper(),

            "country": p.country,

            "status": getattr(p, "status", "ACTIVE"),

            "sector_id": str(p.sector_id) if p.sector_id else None,

            "methodology_id": str(p.methodology_id) if p.methodology_id else None,

            "activities_count": 0,

            "assets_count": 0,

            "role": pm.role_code,

        })



    # 2. Activity Breakdown

    act_res = await db.execute(select(Activity).where(Activity.user_id == user.id))

    activities = act_res.scalars().all()



    total_activities = len(activities)

    verified_acts = sum(1 for a in activities if a.status == "verified")

    pending_acts = sum(1 for a in activities if a.status == "pending")

    flagged_acts = sum(1 for a in activities if a.status == "flagged")

    rejected_acts = sum(1 for a in activities if a.status == "rejected")



    recent_activities = [

        {

            "id": str(a.id),

            "activity_type": a.activity_type,

            "status": a.status,

            "trust_score": a.trust_score,

            "captured_at": a.captured_at.isoformat() if hasattr(a.captured_at, "isoformat") else str(a.captured_at),

            "asset_id": str(a.asset_id) if a.asset_id else None,

        }

        for a in activities[:10]

    ]



    # 3. Asset Breakdown

    assets = []

    if user.organization_id:

        asset_res = await db.execute(select(Asset).where(Asset.organization_id == user.organization_id))

        assets = asset_res.scalars().all()



    total_assets = len(assets)

    active_assets = sum(1 for ast in assets if ast.status == "active")



    # 4. Evidence Breakdown

    total_evidence = 0

    try:

        ev_stmt = select(Evidence).join(Activity, Evidence.activity_id == Activity.id).where(Activity.user_id == user.id)

        ev_res = await db.execute(ev_stmt)

        evidence_packages = ev_res.scalars().all()

        total_evidence = len(evidence_packages)

    except Exception:

        total_evidence = 0



    # Audit Log Publishing for User View

    await EventBus.publish(

        stream_name="access_events",

        event_type="UserAccountInspected",

        payload={"target_user_id": u_id_str, "email": user.email},

        actor_id=str(current_user.id)

    )



    mfa_enabled = bool((user.meta_data or {}).get("mfa", {}).get("enabled", False))



    # 5. Audit History

    audit_history = []

    try:

        audit_res = await db.execute(

            select(SecurityAuditLog)

            .where(

                or_(

                    SecurityAuditLog.actor_user_id == user.id,

                    SecurityAuditLog.target_user_id == user.id,

                )

            )

            .order_by(SecurityAuditLog.created_at.desc())

            .limit(20)

        )

        audit_logs = audit_res.scalars().all()

        for al in audit_logs:

            audit_history.append({

                "id": str(al.id),

                "action": al.action,

                "result": al.result,

                "actor_user_id": str(al.actor_user_id) if al.actor_user_id else None,

                "target_user_id": str(al.target_user_id) if al.target_user_id else None,

                "created_at": al.created_at.isoformat() if hasattr(al.created_at, "isoformat") else str(al.created_at),

                "metadata": al.metadata_json,

            })

    except Exception:

        audit_history = []



    return {

        "account": {

            "id": u_id_str,

            "full_name": user.full_name,

            "email": user.email,

            "phone": user.phone,

            "role": user.role,

            "status": user.status,

            "is_active": user.is_active,

            "is_deleted": user.is_deleted,

            "organization": user.organization,

            "organization_id": str(user.organization_id) if user.organization_id else None,

            "country": user.country,

            "created_at": user.created_at.isoformat() if hasattr(user.created_at, "isoformat") else str(user.created_at),

            "updated_at": user.updated_at.isoformat() if hasattr(user.updated_at, "isoformat") else str(user.updated_at),

            "mfa_enabled": mfa_enabled,

            "requires_password_change": user.requires_password_change,

        },

        "assigned_projects": assigned_projects,

        "activity_summary": {

            "total": total_activities,

            "verified": verified_acts,

            "pending": pending_acts,

            "flagged": flagged_acts,

            "rejected": rejected_acts,

            "recent": recent_activities,

        },

        "asset_summary": {

            "total": total_assets,

            "active": active_assets,

        },

        "evidence_summary": {

            "total": total_evidence,

        },

        "audit_history": audit_history,
    }


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user_account_governance(
    user_id: str,
    payload: UserGovernanceUpdatePayload,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Super Admin endpoint to update user account details including role, organization assignment, full name, email, and status.
    """
    _verify_super_admin(current_user)
    try:
        uuid_obj = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user UUID format")

    res = await db.execute(select(User).options(selectinload(User.organization_rel)).where(User.id == uuid_obj))
    target_user = res.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="User account not found.")

    if payload.role is not None and payload.role.strip():
        canonical_new_role = normalize_role(payload.role)
        if not canonical_new_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role '{payload.role}'. Must be one of {sorted(list(ALL_ROLES))}"
            )
        if canonical_new_role == "SUPER_ADMIN" and target_user.email.lower() != "segunoluwole22@gmail.com":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Cannot elevate non-designated user to SUPER_ADMIN."
            )
        target_user.role = canonical_new_role

    if payload.organization_id is not None:
        if payload.organization_id == "" or payload.organization_id.lower() == "none":
            target_user.organization_id = None
        else:
            try:
                target_user.organization_id = uuid.UUID(payload.organization_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid organization UUID format")
    if payload.full_name is not None and payload.full_name.strip():
        target_user.full_name = payload.full_name.strip()
    if payload.email is not None and payload.email.strip():
        target_user.email = payload.email.strip()
    if payload.status is not None and payload.status.strip():
        target_user.status = payload.status.strip()

    target_user.updated_at = datetime.now(timezone.utc)
    await db.commit()

    res2 = await db.execute(select(User).options(selectinload(User.organization_rel)).where(User.id == uuid_obj))
    updated_user = res2.scalar_one()
    return UserResponse.model_validate(updated_user)


# ---------------------------------------------------------------------------





# ---------------------------------------------------------------------------

# 3. Project Team Graph Inspection

# ---------------------------------------------------------------------------

@router.get("/projects/{project_id}/users")

async def get_project_team_members(

    project_id: uuid.UUID,

    db: AsyncSession = Depends(get_db),

    current_user: User = Depends(get_current_user),

):

    """

    Returns all team members and accounts attached to a project.

    Navigation: Project -> Team -> User

    """

    _verify_super_admin(current_user)



    p_res = await db.execute(select(Project).where(Project.id == project_id))

    proj = p_res.scalar_one_or_none()

    if not proj:

        raise HTTPException(status_code=404, detail="Project not found.")



    # Find users in project's organization

    u_stmt = select(User).where(User.is_deleted == False)

    if proj.organization_id:

        u_stmt = u_stmt.where(User.organization_id == proj.organization_id)



    u_res = await db.execute(u_stmt)

    users = u_res.scalars().all()



    team_members = []

    for u in users:

        act_cnt_res = await db.execute(

            select(func.count(Activity.id)).where(

                Activity.project_id == project_id, Activity.user_id == u.id

            )

        )

        u_act_cnt = act_cnt_res.scalar_one_or_none() or 0



        team_members.append({

            "id": str(u.id),

            "full_name": u.full_name,

            "email": u.email,

            "role": u.role,

            "status": u.status,

            "is_active": u.is_active,

            "project_responsibility": "Organization Administrator" if u.role in ("SUPER_ADMIN", "ORG_ADMIN", "admin") else "Field Agent / Contributor",

            "activities_submitted": u_act_cnt,

            "created_at": u.created_at.isoformat() if hasattr(u.created_at, "isoformat") else str(u.created_at),

        })



    return {

        "project_id": str(proj.id),

        "project_name": proj.name,

        "project_code": proj.project_code or str(proj.id)[:8].upper(),

        "team_count": len(team_members),

        "team_members": team_members,

    }





# ---------------------------------------------------------------------------

# 4. Super Admin Secure Password Reset

# ---------------------------------------------------------------------------

@router.post("/users/{user_id}/reset-password")

async def super_admin_reset_user_password(

    user_id: uuid.UUID,

    payload: PasswordResetPayload,

    db: AsyncSession = Depends(get_db),

    current_user: User = Depends(get_current_user),

):

    """

    Secure password reset workflow initiated by Super Admin.

    Hashed securely with bcrypt, requires password change on next login.

    Never exposes plaintext password or hash in response.

    """

    _verify_super_admin(current_user)



    validate_password_strength(payload.new_password)



    u_res = await db.execute(select(User).where(User.id == user_id))

    user = u_res.scalar_one_or_none()

    if not user:

        raise HTTPException(status_code=404, detail="User account not found.")



    if user.is_deleted:

        raise HTTPException(status_code=400, detail="Cannot reset password for a deleted user account.")



    new_hash = get_password_hash(payload.new_password)

    user.password_hash = new_hash

    user.requires_password_change = True

    user.updated_at = datetime.now(timezone.utc)



    await db.commit()



    # Audit event

    await EventBus.publish(

        stream_name="access_events",

        event_type="PasswordResetByAdmin",

        payload={

            "target_user_id": str(user.id),

            "target_email": user.email,

            "reset_by": str(current_user.id),

        },

        actor_id=str(current_user.id)

    )



    return {

        "status": "success",

        "message": f"Password reset successfully for account '{user.email}'. User must change password upon next login.",

    }





# ---------------------------------------------------------------------------

# 5. Account Suspension & Reactivation

# ---------------------------------------------------------------------------

@router.post("/users/{user_id}/suspend")

async def suspend_user_account(

    user_id: uuid.UUID,

    payload: Optional[SuspendUserPayload] = None,

    db: AsyncSession = Depends(get_db),

    current_user: User = Depends(get_current_user),

):

    """

    Suspends a user account. Blocked from authentication at API layer.

    """

    _verify_super_admin(current_user)



    if user_id == current_user.id:

        raise HTTPException(status_code=400, detail="Super Admin cannot suspend their own account.")



    u_res = await db.execute(select(User).where(User.id == user_id))

    user = u_res.scalar_one_or_none()

    if not user:

        raise HTTPException(status_code=404, detail="User account not found.")



    if user.email == "admin@verifield.io":

        raise HTTPException(status_code=400, detail="Protected platform seed account cannot be suspended.")



    if user.role == "SUPER_ADMIN":

        sa_cnt_res = await db.execute(

            select(func.count(User.id)).where(

                User.role == "SUPER_ADMIN",

                User.is_active == True,

                User.is_deleted == False

            )

        )

        sa_cnt = sa_cnt_res.scalar_one_or_none() or 0

        if sa_cnt <= 1:

            raise HTTPException(status_code=409, detail="Cannot suspend the last active Super Admin account.")



    reason = payload.reason if payload else "Suspended by Super Admin"



    user.status = "suspended"

    user.is_active = False



    meta = user.meta_data or {}

    meta["suspension"] = {

        "suspended_at": datetime.now(timezone.utc).isoformat(),

        "suspended_by": str(current_user.id),

        "reason": reason,

    }

    user.meta_data = meta

    user.updated_at = datetime.now(timezone.utc)



    await db.commit()



    # Audit event

    await EventBus.publish(

        stream_name="access_events",

        event_type="AccountSuspended",

        payload={

            "target_user_id": str(user.id),

            "target_email": user.email,

            "reason": reason,

        },

        actor_id=str(current_user.id)

    )



    return {

        "status": "success",

        "message": f"Account '{user.email}' has been suspended successfully.",

        "user_status": user.status,

        "is_active": user.is_active,

    }





@router.post("/users/{user_id}/reactivate")

async def reactivate_user_account(

    user_id: uuid.UUID,

    db: AsyncSession = Depends(get_db),

    current_user: User = Depends(get_current_user),

):

    """

    Reactivates a suspended user account.

    """

    _verify_super_admin(current_user)



    u_res = await db.execute(select(User).where(User.id == user_id))

    user = u_res.scalar_one_or_none()

    if not user:

        raise HTTPException(status_code=404, detail="User account not found.")



    user.status = "active"

    user.is_active = True



    meta = user.meta_data or {}

    meta["reactivated_at"] = datetime.now(timezone.utc).isoformat()

    meta["reactivated_by"] = str(current_user.id)

    user.meta_data = meta

    user.updated_at = datetime.now(timezone.utc)



    await db.commit()



    # Audit event

    await EventBus.publish(

        stream_name="access_events",

        event_type="AccountReactivated",

        payload={

            "target_user_id": str(user.id),

            "target_email": user.email,

        },

        actor_id=str(current_user.id)

    )



    return {

        "status": "success",

        "message": f"Account '{user.email}' has been reactivated successfully.",

        "user_status": user.status,

        "is_active": user.is_active,

    }





# ---------------------------------------------------------------------------

# 6. Account Deletion / Soft-Delete

# ---------------------------------------------------------------------------

@router.delete("/users/{user_id}")

async def delete_user_account(

    user_id: uuid.UUID,

    db: AsyncSession = Depends(get_db),

    current_user: User = Depends(get_current_user),

):

    """

    Safely deletes or deactivates a user account.

    Preserves historical operational climate records by marking as soft-deleted.

    """

    _verify_super_admin(current_user)



    if user_id == current_user.id:

        raise HTTPException(status_code=400, detail="Super Admin cannot delete their own account.")



    u_res = await db.execute(select(User).where(User.id == user_id))

    user = u_res.scalar_one_or_none()

    if not user:

        raise HTTPException(status_code=404, detail="User account not found.")



    if user.email == "admin@verifield.io":

        raise HTTPException(status_code=400, detail="Protected platform seed account cannot be deleted.")



    if user.role == "SUPER_ADMIN":

        sa_cnt_res = await db.execute(

            select(func.count(User.id)).where(

                User.role == "SUPER_ADMIN",

                User.is_active == True,

                User.is_deleted == False

            )

        )

        sa_cnt = sa_cnt_res.scalar_one_or_none() or 0

        if sa_cnt <= 1:

            raise HTTPException(status_code=409, detail="Cannot delete the last active Super Admin account.")



    user.is_deleted = True

    user.status = "deleted"

    user.is_active = False

    user.deleted_at = datetime.now(timezone.utc)

    user.updated_at = datetime.now(timezone.utc)



    await db.commit()



    # Audit event

    await EventBus.publish(

        stream_name="access_events",

        event_type="AccountDeleted",

        payload={

            "target_user_id": str(user.id),

            "target_email": user.email,

        },

        actor_id=str(current_user.id)

    )



    return {

        "status": "success",

        "message": f"Account '{user.email}' has been safely deactivated/deleted.",

    }





class ProjectMemberAssignPayload(BaseModel):

    user_id: uuid.UUID

    role_code: str = "FIELD_AGENT"





# ---------------------------------------------------------------------------

# 7. Role & Permission Catalogue APIs

# ---------------------------------------------------------------------------

@router.get("/roles")
async def list_role_catalogue(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _verify_super_admin(current_user)
    from app.domains.authentication.models import Role
    from app.core.rbac import ROLE_PERMISSIONS

    # 1. Fetch user counts per role in a single group-by aggregate query
    user_counts: dict[str, int] = {}
    try:
        u_res = await db.execute(
            select(User.role, func.count(User.id))
            .where(User.is_deleted == False)
            .group_by(User.role)
        )
        for role_name, cnt in u_res.all():
            if role_name:
                user_counts[str(role_name)] = cnt
    except Exception:
        pass

    # 2. Fetch roles catalogue
    try:
        res = await db.execute(select(Role).order_by(Role.scope, Role.name))
        roles = res.scalars().all()
    except Exception:
        roles = []

    if not roles:
        fallback_catalogue = [
            {"code": "SUPER_ADMIN", "name": "Platform Super Admin", "description": "Global platform governance and administrative authority", "scope": "PLATFORM", "is_system": True},
            {"code": "COMPLIANCE_ADMIN", "name": "Compliance Administrator", "description": "Accreditation and compliance rule management", "scope": "PLATFORM", "is_system": True},
            {"code": "PLATFORM_SUPPORT", "name": "Platform Support", "description": "Technical operations and platform support", "scope": "PLATFORM", "is_system": True},
            {"code": "JURISDICTION_ADMIN", "name": "Jurisdiction Authority", "description": "National and sub-national carbon registry oversight", "scope": "PLATFORM", "is_system": True},
            {"code": "REGISTRY_ADMIN", "name": "Registry Administrator", "description": "External registry sync and credit issuance oversight", "scope": "PLATFORM", "is_system": True},
            {"code": "ORG_ADMIN", "name": "Organization Administrator", "description": "Tenant administration and user management within assigned organization", "scope": "ORGANIZATION", "is_system": True},
            {"code": "ORG_OWNER", "name": "Organization Owner", "description": "Full operational and billing control of organization workspace", "scope": "ORGANIZATION", "is_system": True},
            {"code": "PROJECT_MANAGER", "name": "Project Manager", "description": "Operational project configuration and team management", "scope": "PROJECT", "is_system": True},
            {"code": "FIELD_SUPERVISOR", "name": "Field Supervisor", "description": "Field team supervision and activity review", "scope": "PROJECT", "is_system": True},
            {"code": "FIELD_AGENT", "name": "Field Agent", "description": "Field evidence collection and mobile data capture", "scope": "PROJECT", "is_system": True},
            {"code": "QA_OFFICER", "name": "QA Officer", "description": "Quality assurance and anomaly validation", "scope": "PROJECT", "is_system": True},
            {"code": "VERIFIER", "name": "Independent Verifier", "description": "Third-party MRV claim and mitigation validation", "scope": "PROJECT", "is_system": True},
            {"code": "AUDITOR", "name": "VVB Independent Auditor", "description": "Read-only inspection and independent audit sign-off", "scope": "PROJECT", "is_system": True},
            {"code": "INVESTOR", "name": "Investor", "description": "Capital allocation review and read-only impact analytics", "scope": "ORGANIZATION", "is_system": True},
            {"code": "VIEWER", "name": "Viewer", "description": "Read-only dashboard visibility", "scope": "ORGANIZATION", "is_system": True}
        ]
        return [
            {
                "id": str(uuid.uuid4()),
                "code": r["code"],
                "name": r["name"],
                "description": r["description"],
                "scope": r["scope"],
                "is_system": r["is_system"],
                "permissions": list(ROLE_PERMISSIONS.get(r["code"], [])),
                "user_count": user_counts.get(r["code"], 0),
            }
            for r in fallback_catalogue
        ]

    return [
        {
            "id": str(r.id),
            "code": r.code,
            "name": r.name,
            "description": r.description,
            "scope": r.scope,
            "is_system": r.is_system,
            "permissions": list(ROLE_PERMISSIONS.get(r.code, [])),
            "user_count": user_counts.get(r.code, 0),
        }
        for r in roles
    ]





@router.get("/organizations/{org_id}/projects")

async def list_organization_projects_admin(

    org_id: uuid.UUID,

    db: AsyncSession = Depends(get_db),

    current_user: User = Depends(get_current_user),

):

    """

    Returns list of projects belonging to a target organization for Super Admin project assignment.

    """

    _verify_super_admin(current_user)



    p_res = await db.execute(select(Project).where(Project.organization_id == org_id))

    projects = p_res.scalars().all()



    return [

        {

            "id": str(p.id),

            "name": p.name,

            "project_code": p.project_code or str(p.id)[:8].upper(),

            "country": p.country,

            "status": p.status,

            "sector_id": str(p.sector_id) if p.sector_id else None,

            "methodology_id": str(p.methodology_id) if p.methodology_id else None,

        }

        for p in projects

    ]





@router.get("/permissions")

async def list_permission_catalogue(

    db: AsyncSession = Depends(get_db),

    current_user: User = Depends(get_current_user),

):

    _verify_super_admin(current_user)

    from app.core.rbac import ROLE_PERMISSIONS



    all_permissions = set()

    for perms in ROLE_PERMISSIONS.values():

        all_permissions.update(perms)



    perm_list = [

        {

            "code": p,

            "name": p.replace(":", " ").title(),

            "category": p.split(":")[0] if ":" in p else "general",

            "scope": "PLATFORM" if "admin" in p or "jurisdiction" in p else "ORGANIZATION",

        }

        for p in sorted(all_permissions)

    ]

    return perm_list





# ---------------------------------------------------------------------------

# 8. Project Membership Management APIs

# ---------------------------------------------------------------------------

@router.get("/projects/{project_id}/members")

async def get_project_memberships(

    project_id: uuid.UUID,

    db: AsyncSession = Depends(get_db),

    current_user: User = Depends(get_current_user),

):

    _verify_super_admin(current_user)

    from app.domains.authentication.models import ProjectMembership



    p_res = await db.execute(select(Project).where(Project.id == project_id))

    proj = p_res.scalar_one_or_none()

    if not proj:

        raise HTTPException(status_code=404, detail="Project not found.")



    m_res = await db.execute(

        select(ProjectMembership, User)

        .join(User, ProjectMembership.user_id == User.id)

        .where(ProjectMembership.project_id == project_id, ProjectMembership.status == "active")

    )

    memberships = m_res.all()



    member_list = []

    for pm, u in memberships:

        act_res = await db.execute(

            select(func.count(Activity.id)).where(Activity.project_id == project_id, Activity.user_id == u.id)

        )

        act_cnt = act_res.scalar_one_or_none() or 0



        member_list.append({

            "membership_id": str(pm.id),

            "user_id": str(u.id),

            "full_name": u.full_name,

            "email": u.email,

            "project_role": pm.role_code,

            "status": pm.status,

            "assigned_at": pm.assigned_at.isoformat() if hasattr(pm.assigned_at, "isoformat") else str(pm.assigned_at),

            "activities_submitted": act_cnt,

        })

    return {

        "project_id": str(proj.id),

        "project_name": proj.name,

        "member_count": len(member_list),

        "members": member_list,

    }





@router.post("/projects/{project_id}/members")

async def assign_project_membership(

    project_id: uuid.UUID,

    payload: ProjectMemberAssignPayload,

    db: AsyncSession = Depends(get_db),

    current_user: User = Depends(get_current_user),

):

    _verify_super_admin(current_user)

    from app.domains.authentication.models import ProjectMembership, SecurityAuditLog



    p_res = await db.execute(select(Project).where(Project.id == project_id))

    proj = p_res.scalar_one_or_none()

    if not proj:

        raise HTTPException(status_code=404, detail="Project not found.")



    u_res = await db.execute(select(User).where(User.id == payload.user_id))

    target_user = u_res.scalar_one_or_none()

    if not target_user:

        raise HTTPException(status_code=404, detail="Target user account not found.")



    ex_res = await db.execute(

        select(ProjectMembership).where(

            ProjectMembership.project_id == project_id,

            ProjectMembership.user_id == payload.user_id,

            ProjectMembership.status == "active"

        )

    )

    ex_pm = ex_res.scalar_one_or_none()

    if ex_pm:

        ex_pm.role_code = payload.role_code

    else:

        new_pm = ProjectMembership(

            user_id=payload.user_id,

            project_id=project_id,

            role_code=payload.role_code,

            status="active",

            assigned_by=current_user.id

        )

        db.add(new_pm)



    audit_entry = SecurityAuditLog(

        actor_user_id=current_user.id,

        target_user_id=target_user.id,

        organization_id=proj.organization_id,

        project_id=project_id,

        action="PROJECT_ACCESS_GRANTED",

        result="SUCCESS",

        metadata_json={"role_code": payload.role_code, "project_name": proj.name}

    )

    db.add(audit_entry)

    await db.commit()



    return {

        "status": "success",

        "message": f"User {target_user.email} assigned role '{payload.role_code}' on project '{proj.name}'.",

    }





@router.delete("/projects/{project_id}/members/{user_id}")

async def revoke_project_membership(

    project_id: uuid.UUID,

    user_id: uuid.UUID,

    db: AsyncSession = Depends(get_db),

    current_user: User = Depends(get_current_user),

):

    _verify_super_admin(current_user)

    from app.domains.authentication.models import ProjectMembership, SecurityAuditLog



    pm_res = await db.execute(

        select(ProjectMembership).where(

            ProjectMembership.project_id == project_id,

            ProjectMembership.user_id == user_id,

            ProjectMembership.status == "active"

        )

    )

    pm = pm_res.scalar_one_or_none()

    if not pm:

        raise HTTPException(status_code=404, detail="Active project membership not found.")



    pm.status = "revoked"



    audit_entry = SecurityAuditLog(

        actor_user_id=current_user.id,

        target_user_id=user_id,

        project_id=project_id,

        action="PROJECT_ACCESS_REVOKED",

        result="SUCCESS",

    )

    db.add(audit_entry)

    await db.commit()



    return {"status": "success", "message": "Project membership revoked successfully."}





# ---------------------------------------------------------------------------

# 9. Session Revocation API

# ---------------------------------------------------------------------------

@router.post("/users/{user_id}/revoke-sessions")

async def revoke_user_sessions(

    user_id: uuid.UUID,

    db: AsyncSession = Depends(get_db),

    current_user: User = Depends(get_current_user),

):

    _verify_super_admin(current_user)

    from app.domains.authentication.models import SecurityAuditLog



    u_res = await db.execute(select(User).where(User.id == user_id))

    target_user = u_res.scalar_one_or_none()

    if not target_user:

        raise HTTPException(status_code=404, detail="User account not found.")



    audit_entry = SecurityAuditLog(

        actor_user_id=current_user.id,

        target_user_id=target_user.id,

        organization_id=target_user.organization_id,

        action="SESSION_REVOKED",

        result="SUCCESS",

    )

    db.add(audit_entry)

    await db.commit()



    return {

        "status": "success",

        "message": f"Active sessions revoked for user '{target_user.email}'.",

    }





# ---------------------------------------------------------------------------

# 10. Immutable Security Audit Logs API

# ---------------------------------------------------------------------------

@router.get("/audit-logs")

async def list_security_audit_logs(

    action: Optional[str] = None,

    limit: int = 50,

    db: AsyncSession = Depends(get_db),

    current_user: User = Depends(get_current_user),

):

    _verify_super_admin(current_user)

    from app.domains.authentication.models import SecurityAuditLog



    stmt = select(SecurityAuditLog)

    if action:

        stmt = stmt.where(SecurityAuditLog.action == action)



    stmt = stmt.order_by(SecurityAuditLog.created_at.desc()).limit(limit)

    res = await db.execute(stmt)

    logs = res.scalars().all()



    return [

        {

            "id": str(l.id),

            "actor_user_id": str(l.actor_user_id) if l.actor_user_id else None,

            "target_user_id": str(l.target_user_id) if l.target_user_id else None,

            "organization_id": str(l.organization_id) if l.organization_id else None,

            "project_id": str(l.project_id) if l.project_id else None,

            "action": l.action,

            "result": l.result,

            "metadata": l.metadata_json or {},

            "created_at": l.created_at.isoformat() if hasattr(l.created_at, "isoformat") else str(l.created_at),

        }

        for l in logs

    ]
