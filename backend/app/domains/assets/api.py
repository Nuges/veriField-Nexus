from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.domains.assets.repository import AssetRepository
from app.domains.assets.schemas import AssetCreate, AssetResponse, AssetUpdate
from app.domains.assets.service import AssetService
from app.domains.authentication.models import User
from app.domains.projects.repository import ProjectRepository

router = APIRouter(prefix="/assets", tags=["Assets"])


@router.post("", response_model=AssetResponse)
async def create_asset(
    payload: AssetCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Retrieve project context
    proj_repo = ProjectRepository(db)
    project = await proj_repo.get_by_id(payload.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Associated Project not found")

    # Enforce tenant isolation
    if (
        current_user.role != "SUPER_ADMIN"
        and project.organization_id != current_user.organization_id
    ):
        raise HTTPException(
            status_code=403, detail="Project does not belong to your organization."
        )

    repo = AssetRepository(db)
    service = AssetService(repo)

    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(
            status_code=400, detail="User must belong to an organization."
        )

    asset = await service.create_asset(payload, org_id)
    return AssetResponse.model_validate(asset)


@router.get("", response_model=List[AssetResponse])
async def list_assets(
    project_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = AssetRepository(db)
    service = AssetService(repo)

    org_id = current_user.organization_id
    if not org_id:
        if current_user.role == "SUPER_ADMIN":
            from sqlalchemy import select

            from app.domains.assets.models import Asset

            res = await db.execute(select(Asset))
            return [AssetResponse.model_validate(a) for a in res.scalars().all()]
        return []

    assets = await service.list_assets(org_id, project_id)
    return [AssetResponse.model_validate(a) for a in assets]


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = AssetRepository(db)
    service = AssetService(repo)

    org_id = (
        current_user.organization_id if current_user.role != "SUPER_ADMIN" else None
    )
    asset = await service.get_asset(asset_id, org_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return AssetResponse.model_validate(asset)


@router.put("/{asset_id}", response_model=AssetResponse)
async def update_asset(
    asset_id: UUID,
    payload: AssetUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = AssetRepository(db)
    service = AssetService(repo)

    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(
            status_code=400, detail="User must belong to an organization."
        )

    asset = await repo.get_by_id(asset_id, org_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found or unauthorized.")

    # Fetch project context
    proj_repo = ProjectRepository(db)
    project = await proj_repo.get_by_id(asset.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    updated = await service.update_asset(asset_id, payload, org_id)
    return AssetResponse.model_validate(updated)


@router.delete("/{asset_id}")
async def delete_asset(
    asset_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = AssetRepository(db)
    service = AssetService(repo)

    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(
            status_code=400, detail="User must belong to an organization."
        )

    success = await service.delete_asset(asset_id, org_id)
    if not success:
        raise HTTPException(status_code=404, detail="Asset not found or unauthorized.")
    return {"status": "success", "message": "Asset deleted successfully."}
