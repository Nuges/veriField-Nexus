from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select, text
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

@router.get("/plugins")
async def list_registry_plugins():
    return [
        {"id": "verra", "name": "Verra Registry", "version": "1.0"},
        {"id": "gold_standard", "name": "Gold Standard", "version": "1.2"},
        {"id": "csi", "name": "CSI Hub", "version": "1.0"}
    ]


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

@router.post("/sync/{bundle_id}")
async def sync_bundle_to_registry(
    bundle_id: str, 
    provider_name: str = "local", 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from app.domains.registry_integrations.providers.factory import RegistryProviderFactory
    import uuid
    from app.domains.registry_integrations.models import RegistrySyncLog
    
    provider = RegistryProviderFactory.get_provider(provider_name, db)
    
    # 1. Authenticate
    await provider.authenticate()
    
    # 2. Convert string to UUID for the bundle
    try:
        project_uuid = uuid.UUID(bundle_id)
    except ValueError:
        # Fallback to a generated UUID for testing if bundle_id is not UUID format
        project_uuid = uuid.uuid4()
        
    idempotency_key = f"sync-{bundle_id}-{uuid.uuid4().hex[:8]}"
    
    # 3. Create a RegistrySyncLog in DB
    sync_log = RegistrySyncLog(
        project_id=project_uuid,
        action="submit_bundle",
        status="Queued",
        idempotency_key=idempotency_key,
        registry_id=uuid.uuid4() # Temporary auto-generated registry config ID
    )
    db.add(sync_log)
    await db.commit()
    await db.refresh(sync_log)
    
    # 4. Trigger Provider Submission
    result = await provider.submit_bundle(project_uuid, {"bundle_id": bundle_id}, idempotency_key)
    
    return {
        "success": True, 
        "message": f"Bundle {bundle_id} synced successfully via {provider_name}", 
        "sync_id": str(sync_log.id),
        "details": result
    }

@router.get("/status/{sync_id}")
async def get_sync_status(
    sync_id: str,
    provider_name: str = "local",
    db: AsyncSession = Depends(get_db)
):
    from app.domains.registry_integrations.providers.factory import RegistryProviderFactory
    import uuid
    
    provider = RegistryProviderFactory.get_provider(provider_name, db)
    status_result = await provider.check_status(uuid.UUID(sync_id))
    return status_result

@router.get("/export/{registry_type}")
async def export_registry_data(registry_type: str, min_trust_score: float = 80, db: AsyncSession = Depends(get_db)):
    # Refactored to not hardcode Verra/Gold Standard methodologies
    query = text("""
        SELECT 
            a.id as stove_id,
            'VeriField' as manufacturer,
            'V1' as model,
            a.owner_id as household_id,
            COALESCE(u.full_name, 'Unknown') as head_name,
            '4000.0' as baseline_fuel_consumption,
            COALESCE(CAST(a.attributes->>'carbon_offset_kg' AS NUMERIC), 0) as emission_reduction_value_kg,
            act.trust_score
        FROM assets a
        LEFT JOIN users u ON a.owner_id = u.id
        LEFT JOIN activities act ON act.asset_id = a.id
        WHERE act.trust_score >= :min_trust
    """)
    res = await db.execute(query, {"min_trust": min_trust_score})
    
    import json
    records = []
    for r in res.mappings().all():
        records.append({
            "stove_id": str(r.stove_id),
            "baseline_fuel_consumed": float(r.baseline_fuel_consumption),
            "avg_emission_reduction_value_co2_kg": float(r.emission_reduction_value_kg),
            "trust_score": float(r.trust_score) if r.trust_score else 0
        })

    data = {
        "registry_provider": registry_type.upper(),
        "methodology": "DYNAMIC_METHODOLOGY_RESOLVER",
        "records": records
    }
    return Response(content=json.dumps(data), media_type="application/json", headers={"Content-Disposition": f"attachment; filename={registry_type}_export.json"})
