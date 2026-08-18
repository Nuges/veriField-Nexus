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
async def list_registry_configs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(RegistryConfig)
    if current_user.role != "SUPER_ADMIN" and hasattr(RegistryConfig, "organization_id"):
        stmt = stmt.where(RegistryConfig.organization_id == current_user.organization_id)
    result = await db.execute(stmt)
    configs = result.scalars().all()
    return [RegistryConfigResponse.from_orm_safe(c) for c in configs]

@router.get("/plugins")
async def list_registry_plugins(
    current_user: User = Depends(get_current_user)
):
    return [
        {"id": "verra", "name": "Verra Registry", "version": "1.0", "status": "PENDING_EXTERNAL_CREDENTIALS"},
        {"id": "gold_standard", "name": "Gold Standard", "version": "1.2", "status": "PENDING_EXTERNAL_CREDENTIALS"},
        {"id": "csi", "name": "CSI Hub", "version": "1.0", "status": "INTERNAL_PACKAGING_READY"}
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
    from app.domains.registry_integrations.providers.factory import get_registry_provider
    import uuid
    from app.domains.registry_integrations.models import RegistrySyncLog

    provider = get_registry_provider(provider_name)

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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.domains.registry_integrations.providers.factory import get_registry_provider
    import uuid

    provider = get_registry_provider(provider_name)
    status_result = await provider.check_status(uuid.UUID(sync_id))
    return status_result

@router.get("/export/{registry_type}")
async def export_registry_data(
    registry_type: str,
    min_trust_score: float = 80,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ["SUPER_ADMIN", "ORG_ADMIN", "REGISTRY_ADMIN", "COMPLIANCE_ADMIN"]:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Insufficient privileges to export registry bundles."
        )

    # Scoped strictly by tenant organization
    if current_user.role == "SUPER_ADMIN":
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
        params = {"min_trust": min_trust_score}
    else:
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
            WHERE act.trust_score >= :min_trust AND a.organization_id = :org_id
        """)
        params = {"min_trust": min_trust_score, "org_id": current_user.organization_id}

    res = await db.execute(query, params)

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



@router.get("/package/{registry_type}/{project_id}")
async def get_registry_submission_package(
    registry_type: str,
    project_id: UUID,
    min_trust_score: float = 80.0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generates a full registry submission package bundling metadata, methodology,
    verified assets, carbon math, and document integrity hashes.
    """
    from app.domains.registry_integrations.services.packaging import RegistryPackagingService
    service = RegistryPackagingService(db)
    package = await service.generate_registry_package(
        registry_type=registry_type,
        project_id=project_id,
        min_trust_score=min_trust_score,
    )
    # Enforce tenant check
    if current_user.role != "SUPER_ADMIN":
        if package["organization"]["id"] != str(current_user.organization_id):
            raise HTTPException(status_code=403, detail="Forbidden: Cannot generate registry packages for another organization.")

    return package
