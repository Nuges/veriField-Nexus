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

from pydantic import BaseModel



class AddSectorRequest(BaseModel):

    sector_id: UUID

    methodology_id: UUID



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
    role_upper = (current_user.role or "").upper().replace(" ", "_")
    if role_upper not in ("SUPER_ADMIN", "ADMIN", "ORG_ADMIN"):
        raise HTTPException(status_code=403, detail="Access denied.")

    repo = OrganizationRepository(db)
    service = OrganizationService(repo)

    if role_upper in ("SUPER_ADMIN", "ADMIN") or not current_user.organization_id:
        orgs = await service.list_orgs()
    else:
        org = await repo.get_by_id(current_user.organization_id)
        orgs = [org] if org else []

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





@router.post("/{org_id}/sectors", response_model=OrganizationResponse)

async def add_sector_to_organization(

    org_id: UUID,

    payload: AddSectorRequest,

    current_user: User = Depends(require_permission(MANAGE_ORG)),

    db: AsyncSession = Depends(get_db),

):

    if current_user.role != "SUPER_ADMIN" and current_user.organization_id != org_id:

        raise HTTPException(status_code=403, detail="Tenant boundary violation.")



    repo = OrganizationRepository(db)

    service = OrganizationService(repo)



    org = await service.get_org(org_id)

    if not org:

        raise HTTPException(status_code=404, detail="Organization not found")



    from sqlalchemy import text



    # Verify sector and methodology

    res_sec = await db.execute(text("SELECT code FROM methodology_families WHERE id = :id"), {"id": str(payload.sector_id)})

    sec_row = res_sec.fetchone()

    if not sec_row:

        raise HTTPException(status_code=400, detail="Invalid sector_id")



    res_meth = await db.execute(text("SELECT code FROM methodologies WHERE id = :id"), {"id": str(payload.methodology_id)})

    meth_row = res_meth.fetchone()

    if not meth_row:

        raise HTTPException(status_code=400, detail="Invalid methodology_id")



    licensed_sectors = org.licensed_sectors or []

    if sec_row.code not in licensed_sectors:

        licensed_sectors.append(sec_row.code)

        org.licensed_sectors = licensed_sectors



    # Auto-provision project

    from app.domains.projects.models import Project

    proj_exists = await db.execute(

        text("SELECT id FROM projects WHERE organization_id = :org_id AND sector_id = :sec_id"),

        {"org_id": org_id, "sec_id": str(payload.sector_id)}

    )

    if not proj_exists.fetchone():

        default_proj = Project(

            name=f"Default Project - {sec_row.code}",

            organization_id=org_id,

            sector_id=payload.sector_id,

            methodology_id=payload.methodology_id,

            country="Global"

        )

        db.add(default_proj)



    await db.commit()

    await db.refresh(org)



    return OrganizationResponse.model_validate(org)
