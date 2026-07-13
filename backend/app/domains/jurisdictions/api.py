from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import require_permission
from app.db.session import get_db
from app.domains.authentication.models import User
from app.domains.jurisdictions.repository import JurisdictionRepository
from app.domains.jurisdictions.schemas import (JurisdictionCreate,
                                               JurisdictionResponse,
                                               JurisdictionUpdate)
from app.domains.jurisdictions.service import (GovernanceMetadataResolver,
                                               JurisdictionService)

router = APIRouter(prefix="/jurisdictions", tags=["Jurisdictions"])


@router.get("", response_model=List[JurisdictionResponse])
async def list_jurisdictions(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_permission("jurisdiction:read")),
    db: AsyncSession = Depends(get_db),
):
    repo = JurisdictionRepository(db)
    service = JurisdictionService(repo)
    jurisdictions = await service.list_jurisdictions(limit, offset)
    return [JurisdictionResponse.model_validate(j) for j in jurisdictions]


@router.post(
    "", response_model=JurisdictionResponse, status_code=status.HTTP_201_CREATED
)
async def create_jurisdiction(
    payload: JurisdictionCreate,
    x_idempotency_key: Optional[str] = Header(None),
    current_user: User = Depends(require_permission("jurisdiction:all")),
    db: AsyncSession = Depends(get_db),
):
    repo = JurisdictionRepository(db)
    service = JurisdictionService(repo)
    jurisdiction = await service.create_jurisdiction(
        payload.model_dump(), actor_id=str(current_user.id)
    )
    return JurisdictionResponse.model_validate(jurisdiction)


@router.get("/{jurisdiction_id}", response_model=JurisdictionResponse)
async def get_jurisdiction(
    jurisdiction_id: UUID,
    current_user: User = Depends(require_permission("jurisdiction:read")),
    db: AsyncSession = Depends(get_db),
):
    repo = JurisdictionRepository(db)
    service = JurisdictionService(repo)
    jurisdiction = await service.get_jurisdiction(jurisdiction_id)
    return JurisdictionResponse.model_validate(jurisdiction)


@router.put("/{jurisdiction_id}", response_model=JurisdictionResponse)
async def update_jurisdiction(
    jurisdiction_id: UUID,
    payload: JurisdictionUpdate,
    x_idempotency_key: Optional[str] = Header(None),
    current_user: User = Depends(require_permission("jurisdiction:all")),
    db: AsyncSession = Depends(get_db),
):
    repo = JurisdictionRepository(db)
    service = JurisdictionService(repo)
    updates = payload.model_dump(exclude_unset=True)
    updated = await service.update_jurisdiction(
        jurisdiction_id, updates, actor_id=str(current_user.id)
    )
    return JurisdictionResponse.model_validate(updated)


@router.delete("/{jurisdiction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_jurisdiction(
    jurisdiction_id: UUID,
    current_user: User = Depends(require_permission("jurisdiction:all")),
    db: AsyncSession = Depends(get_db),
):
    repo = JurisdictionRepository(db)
    service = JurisdictionService(repo)
    await service.delete_jurisdiction(jurisdiction_id, actor_id=str(current_user.id))
    return None


@router.get("/{jurisdiction_id}/context")
async def get_jurisdiction_context(
    jurisdiction_id: UUID,
    current_user: User = Depends(require_permission("jurisdiction:read")),
    db: AsyncSession = Depends(get_db),
):
    resolver = GovernanceMetadataResolver(db)
    context = await resolver.resolve_context(jurisdiction_id)
    return context
