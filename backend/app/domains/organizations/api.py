from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import require_permission
from app.core.security import get_current_user
from app.db.session import get_db
from app.domains.authentication.models import User
from app.domains.authentication.permissions import MANAGE_ORG
from app.domains.organizations.repository import OrganizationRepository
from app.domains.organizations.schemas import (OrganizationCreate,
                                               OrganizationResponse,
                                               OrganizationUpdate)
from app.domains.organizations.service import OrganizationService

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.post("", response_model=OrganizationResponse)
async def create_organization(
    payload: OrganizationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != "SUPER_ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Only Platform Super Admins can create organizations.",
        )

    repo = OrganizationRepository(db)
    service = OrganizationService(repo)

    # Check duplicate
    if await repo.get_by_name(payload.name):
        raise HTTPException(status_code=400, detail="Organization name already exists")

    org = await service.create_org(payload, creator_id=current_user.id)
    return OrganizationResponse.model_validate(org)


@router.get("", response_model=List[OrganizationResponse])
async def list_organizations(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    if current_user.role != "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail="Access denied.")

    repo = OrganizationRepository(db)
    service = OrganizationService(repo)
    orgs = await service.list_orgs()
    return [OrganizationResponse.model_validate(o) for o in orgs]


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Enforce tenant isolation boundary
    if current_user.role != "SUPER_ADMIN" and current_user.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Tenant boundary violation.")

    repo = OrganizationRepository(db)
    service = OrganizationService(repo)
    org = await service.get_org(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return OrganizationResponse.model_validate(org)


@router.put("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: UUID,
    payload: OrganizationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(MANAGE_ORG)),
):
    if current_user.role != "SUPER_ADMIN" and current_user.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Tenant boundary violation.")

    repo = OrganizationRepository(db)
    service = OrganizationService(repo)

    try:
        updated = await service.update_org(
            org_id, payload, actor_id=current_user.id, db=db
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    if not updated:
        raise HTTPException(status_code=404, detail="Organization not found")
    return OrganizationResponse.model_validate(updated)


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    org_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != "SUPER_ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Only Platform Super Admins can archive organizations.",
        )

    repo = OrganizationRepository(db)
    service = OrganizationService(repo)

    success = await service.soft_delete_org(org_id, actor_id=current_user.id, db=db)
    if not success:
        raise HTTPException(status_code=404, detail="Organization not found")
    return None
