"""
=============================================================================
VeriField Nexus — Audit Tasks API Routes
=============================================================================
CRUD operations for audit task management. Supports:
- Creating audit tasks (admin)
- Listing assigned audits for the current agent
- Updating audit status
=============================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from typing import Optional
from uuid import UUID

from app.db.session import get_db
from app.core.security import get_current_user, get_optional_user, require_admin
from app.models.user import User
from app.models.audit_task import AuditTask
from app.models.property import Property
from app.schemas.audit import (
    AuditTaskCreate, AuditTaskUpdate,
    AuditTaskResponse, AuditTaskListResponse,
)

router = APIRouter(prefix="/audits", tags=["Audits"])


def _serialize_audit(audit: AuditTask) -> AuditTaskResponse:
    """Convert an AuditTask ORM instance to a response model with joined fields."""
    return AuditTaskResponse(
        id=audit.id,
        asset_id=audit.asset_id,
        assigned_agent=audit.assigned_agent,
        status=audit.status,
        deadline=audit.deadline,
        created_at=audit.created_at,
        property_name=audit.property.name if audit.property else None,
        property_address=audit.property.address if audit.property else None,
        property_type=audit.property.property_type if audit.property else None,
        agent_name=audit.agent.full_name if audit.agent else None,
    )


# =============================================================================
# POST /api/v1/audits — Create audit task (admin)
# =============================================================================
@router.post(
    "",
    response_model=AuditTaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new audit task",
)
async def create_audit_task(
    payload: AuditTaskCreate,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new audit task and assign it to a field agent."""
    # Validate asset exists
    prop_result = await db.execute(select(Property).where(Property.id == payload.asset_id))
    prop = prop_result.scalar_one_or_none()
    if not prop:
        raise HTTPException(status_code=404, detail="Property/asset not found")

    # Validate agent exists
    agent_result = await db.execute(select(User).where(User.id == payload.assigned_agent))
    agent = agent_result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Check organization scoping for ORG_ADMIN/admin
    if user.role in ("ORG_ADMIN", "admin"):
        owner_res = await db.execute(select(User).where(User.id == prop.owner_id))
        owner = owner_res.scalar_one_or_none()
        if not owner or owner.organization != user.organization:
            raise HTTPException(status_code=403, detail="Access denied. Property belongs to another organization.")
        if agent.organization != user.organization:
            raise HTTPException(status_code=403, detail="Access denied. Agent belongs to another organization.")

    audit = AuditTask(
        asset_id=payload.asset_id,
        assigned_agent=payload.assigned_agent,
        status=payload.status,
        deadline=payload.deadline,
    )
    db.add(audit)
    await db.commit()

    # Reload with relationships
    result = await db.execute(
        select(AuditTask)
        .options(selectinload(AuditTask.property), selectinload(AuditTask.agent))
        .where(AuditTask.id == audit.id)
    )
    audit = result.scalar_one()
    return _serialize_audit(audit)


# =============================================================================
# GET /api/v1/audits — List audit tasks
# =============================================================================
@router.get(
    "",
    response_model=AuditTaskListResponse,
    summary="List audit tasks",
)
async def list_audit_tasks(
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """List audit tasks. Agents see only their own; admins see all."""
    query = select(AuditTask).options(
        selectinload(AuditTask.property), selectinload(AuditTask.agent)
    )
    count_query = select(func.count(AuditTask.id))

    conditions = []
    if user:
        if user.role == "SUPER_ADMIN":
            # Global view: no filters
            pass
        elif user.role in ("ORG_ADMIN", "admin"):
            query = query.join(Property, AuditTask.asset_id == Property.id).join(User, Property.owner_id == User.id)
            count_query = count_query.join(Property, AuditTask.asset_id == Property.id).join(User, Property.owner_id == User.id)
            if user.organization:
                conditions.append(User.organization == user.organization)
            else:
                conditions.append(User.organization == None)
        else:
            conditions.append(AuditTask.assigned_agent == user.id)
    if status_filter:
        conditions.append(AuditTask.status == status_filter)

    if conditions:
        query = query.where(and_(*conditions))
        count_query = count_query.where(and_(*conditions))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * per_page
    query = query.order_by(AuditTask.created_at.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    audits = result.scalars().all()

    return AuditTaskListResponse(
        audits=[_serialize_audit(a) for a in audits],
        total=total, page=page, per_page=per_page,
    )


# =============================================================================
# GET /api/v1/audits/my-tasks — List audit tasks for current agent
# =============================================================================
@router.get(
    "/my-tasks",
    response_model=list[AuditTaskResponse],
    summary="Get audit tasks assigned to the current agent",
)
async def get_my_audit_tasks(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get audit tasks assigned to the current agent."""
    result = await db.execute(
        select(AuditTask)
        .options(selectinload(AuditTask.property), selectinload(AuditTask.agent))
        .where(AuditTask.assigned_agent == user.id)
        .order_by(AuditTask.created_at.desc())
    )
    audits = result.scalars().all()
    return [_serialize_audit(a) for a in audits]


# =============================================================================
# PATCH /api/v1/audits/{id} — Update audit task status
# =============================================================================
@router.patch(
    "/{audit_id}",
    response_model=AuditTaskResponse,
    summary="Update audit task",
)
async def update_audit_task(
    audit_id: UUID,
    payload: AuditTaskUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an audit task's status or deadline."""
    result = await db.execute(
        select(AuditTask)
        .options(selectinload(AuditTask.property), selectinload(AuditTask.agent))
        .where(AuditTask.id == audit_id)
    )
    audit = result.scalar_one_or_none()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit task not found")

    # Scoping checks for update
    if user.role == "SUPER_ADMIN":
        pass
    elif user.role in ("ORG_ADMIN", "admin"):
        # Audit property owner organization must match
        is_authorized = False
        if audit.property:
            owner_res = await db.execute(select(User).where(User.id == audit.property.owner_id))
            owner = owner_res.scalar_one_or_none()
            if owner and owner.organization == user.organization:
                is_authorized = True
        if not is_authorized:
            raise HTTPException(status_code=403, detail="Access denied. Task does not belong to your organization.")
    else:
        # Field agent can only update if assigned to them
        if audit.assigned_agent != user.id:
            raise HTTPException(status_code=403, detail="Access denied")

    if payload.status is not None:
        audit.status = payload.status
    if payload.deadline is not None:
        audit.deadline = payload.deadline
    if payload.assigned_agent is not None:
        audit.assigned_agent = payload.assigned_agent

    await db.commit()
    await db.refresh(audit)

    # Reload relationships
    result = await db.execute(
        select(AuditTask)
        .options(selectinload(AuditTask.property), selectinload(AuditTask.agent))
        .where(AuditTask.id == audit.id)
    )
    audit = result.scalar_one()
    return _serialize_audit(audit)
