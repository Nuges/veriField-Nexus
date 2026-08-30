from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.domains.authentication.models import User
from app.domains.projects.models import Project

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
    current_user: User = Depends(get_current_user),
):
    from app.domains.registry_integrations.providers.factory import get_registry_provider
    import uuid
    from app.domains.registry_integrations.models import RegistrySyncLog

    try:
        provider = get_registry_provider(provider_name, db=db)
        # 1. Authenticate
        await provider.authenticate()
    except NotImplementedError as nie:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"Registry provider '{provider_name}' is currently in staging/local packaging mode. Direct external API synchronization requires production registry credentials: {str(nie)}",
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )

    # 2. Convert string to UUID for the bundle
    try:
        project_uuid = uuid.UUID(bundle_id)
    except ValueError:
        project_uuid = uuid.uuid4()

    idempotency_key = f"sync-{bundle_id}-{uuid.uuid4().hex[:8]}"

    # 3. Create a RegistrySyncLog in DB
    sync_log = RegistrySyncLog(
        project_id=project_uuid,
        action="submit_bundle",
        status="Queued",
        idempotency_key=idempotency_key,
        registry_id=uuid.uuid4(),
    )
    db.add(sync_log)
    await db.commit()
    await db.refresh(sync_log)

    # 4. Trigger Provider Submission
    try:
        result = await provider.submit_bundle(project_uuid, {"bundle_id": bundle_id}, idempotency_key)
    except NotImplementedError as nie:
        sync_log.status = "Failed"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"Registry submission for '{provider_name}' pending live credentials: {str(nie)}",
        )

    return {
        "success": True,
        "message": f"Bundle {bundle_id} synced successfully via {provider_name}",
        "sync_id": str(sync_log.id),
        "details": result,
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
    try:
        package = await service.generate_registry_package(
            registry_type=registry_type,
            project_id=project_id,
            min_trust_score=min_trust_score,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Enforce tenant check
    if current_user.role != "SUPER_ADMIN":
        pkg_org = package.get("organization", {}).get("id")
        user_org = str(current_user.organization_id) if current_user.organization_id else None
        if pkg_org and user_org and pkg_org.lower() != user_org.lower():
            raise HTTPException(status_code=403, detail="Forbidden: Cannot generate registry packages for another organization.")

    return package


@router.get("/dossier/{standard}/{project_id}")
async def get_compliance_dossier(
    standard: str,
    project_id: UUID,
    stage: str = "monitoring",
    version: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generates an authoritative, standard-specific compliance dossier (NCCC, Article 6.2, Article 6.4, Verra, Gold Standard).
    """
    p_stmt = select(Project.organization_id).where(Project.id == project_id)
    p_res = await db.execute(p_stmt)
    proj_org = p_res.scalar_one_or_none()
    if not proj_org and current_user.role != "SUPER_ADMIN":
        # Check if project exists
        p_check = await db.execute(select(Project.id).where(Project.id == project_id))
        if not p_check.scalar_one_or_none():
            raise HTTPException(status_code=404, detail=f"Project with ID {project_id} not found.")

    if current_user.role != "SUPER_ADMIN":
        user_org = current_user.organization_id
        if not user_org or (proj_org and str(proj_org).lower() != str(user_org).lower()):
            raise HTTPException(status_code=403, detail="Forbidden: Cannot access compliance dossiers for another organization.")

    from app.domains.registry_integrations.services.compliance_dossier import RegistryComplianceDossierService
    service = RegistryComplianceDossierService(db)
    try:
        dossier = await service.generate_dossier(standard=standard, project_id=project_id, stage=stage, version=version)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return dossier


@router.get("/readiness/{project_id}")
async def get_project_registry_readiness(
    project_id: UUID,
    target_standard: str = "VERRA",
    target_stage: str = "verification",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Computes deterministic documentation completeness and registry readiness score across 9 pillars.
    """
    p_stmt = select(Project.organization_id).where(Project.id == project_id)
    p_res = await db.execute(p_stmt)
    proj_org = p_res.scalar_one_or_none()
    if not proj_org and current_user.role != "SUPER_ADMIN":
        p_check = await db.execute(select(Project.id).where(Project.id == project_id))
        if not p_check.scalar_one_or_none():
            raise HTTPException(status_code=404, detail=f"Project with ID {project_id} not found.")

    if current_user.role != "SUPER_ADMIN":
        user_org = current_user.organization_id
        if not user_org or (proj_org and str(proj_org).lower() != str(user_org).lower()):
            raise HTTPException(status_code=403, detail="Forbidden: Cannot access readiness scores for another organization.")

    from app.domains.registry_integrations.services.readiness_engine import RegistryReadinessEngine
    engine = RegistryReadinessEngine(db)
    try:
        readiness = await engine.evaluate_readiness(project_id=project_id, target_standard=target_standard, target_stage=target_stage)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return readiness


@router.get("/lineage/{project_id}")
async def get_project_data_lineage(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns end-to-end data lineage provenance graph connecting raw sensor/field observations to approved carbon credits.
    """
    p_stmt = select(Project.organization_id).where(Project.id == project_id)
    p_res = await db.execute(p_stmt)
    proj_org = p_res.scalar_one_or_none()
    if not proj_org and current_user.role != "SUPER_ADMIN":
        p_check = await db.execute(select(Project.id).where(Project.id == project_id))
        if not p_check.scalar_one_or_none():
            raise HTTPException(status_code=404, detail=f"Project with ID {project_id} not found.")

    if current_user.role != "SUPER_ADMIN":
        user_org = current_user.organization_id
        if not user_org or (proj_org and str(proj_org).lower() != str(user_org).lower()):
            raise HTTPException(status_code=403, detail="Forbidden: Cannot access data lineage for another organization.")

    from app.domains.reporting.services.lineage import DataLineageEngine
    engine = DataLineageEngine(db)
    try:
        lineage = await engine.get_project_data_lineage(project_id=project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return lineage


@router.get("/package-download/{standard}/{project_id}")
async def download_registry_package_zip(
    standard: str,
    project_id: UUID,
    stage: str = "verification",
    version: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generates and downloads a standardized, multi-directory, cryptographically sealed ZIP submission package.
    """
    p_stmt = select(Project.organization_id).where(Project.id == project_id)
    p_res = await db.execute(p_stmt)
    proj_org = p_res.scalar_one_or_none()
    if not proj_org and current_user.role != "SUPER_ADMIN":
        p_check = await db.execute(select(Project.id).where(Project.id == project_id))
        if not p_check.scalar_one_or_none():
            raise HTTPException(status_code=404, detail=f"Project with ID {project_id} not found.")

    if current_user.role != "SUPER_ADMIN":
        user_org = current_user.organization_id
        if not user_org or (proj_org and str(proj_org).lower() != str(user_org).lower()):
            raise HTTPException(status_code=403, detail="Forbidden: Cannot download registry packages for another organization.")

    from app.domains.registry_integrations.services.package_builder import ComprehensivePackageBuilder
    builder = ComprehensivePackageBuilder(db)
    try:
        zip_bytes, zip_filename, manifest = await builder.build_package_zip(
            project_id=project_id, standard=standard, stage=stage, version=version
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_filename}"'},
    )
