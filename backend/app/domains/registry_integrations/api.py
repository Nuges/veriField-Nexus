from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.domains.authentication.models import User

from .models import RegistryConfig
from .schemas import (RegistryConfigCreate, RegistryConfigResponse,
                      RegistrySyncLogResponse, SyncActionRequest)
from .service import RegistryFederationService

router = APIRouter()


@router.get("/configs", response_model=List[RegistryConfigResponse])
async def list_registry_configs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RegistryConfig))
    return result.scalars().all()


@router.post("/configs", response_model=RegistryConfigResponse)
async def create_registry_config(
    data: RegistryConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ["SUPER_ADMIN", "COMPLIANCE_ADMIN"]:
        raise HTTPException(
            status_code=403, detail="Not authorized to configure registries"
        )

    config = RegistryConfig(**data.model_dump())
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return config


@router.post("/{registry_id}/sync", response_model=RegistrySyncLogResponse)
async def trigger_sync_action(
    registry_id: UUID,
    data: SyncActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = RegistryFederationService(db)
    # Simple idempotency key generation for direct API calls
    import uuid

    idempotency_key = f"api-trigger-{uuid.uuid4()}"

    try:
        log = await service.sync_action(
            registry_id=registry_id,
            project_id=data.project_id,
            action=data.action,
            payload=data.payload,
            idempotency_key=idempotency_key,
        )
        return log
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
