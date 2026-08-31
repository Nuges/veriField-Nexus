from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel
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


@router.get("/document-matrix")
async def get_registry_document_matrix(
    current_user: User = Depends(get_current_user),
):
    """
    Returns the authoritative registry document requirements matrix across NCCC, Article 6.2, Article 6.4, Verra, and Gold Standard.
    """
    from app.domains.registry_integrations.services.template_registry import TemplateRegistry
    registry = TemplateRegistry.get_instance()
    return registry.get_matrix()


@router.get("/documents/{standard}/{project_id}/{document_id}")
async def get_registry_document(
    standard: str,
    project_id: UUID,
    document_id: str,
    format: str = "pdf",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Renders and streams a specific structured registry submission document in PDF, DOCX, or JSON format.
    """
    # 1. Tenant Verification
    p_stmt = select(Project).where(Project.id == project_id)
    p_res = await db.execute(p_stmt)
    project = p_res.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project with ID {project_id} not found.")

    if current_user.role != "SUPER_ADMIN":
        user_org = current_user.organization_id
        if not user_org or str(project.organization_id).lower() != str(user_org).lower():
            raise HTTPException(status_code=403, detail="Forbidden: Cannot access registry documents for another organization.")

    from app.domains.registry_integrations.services.readiness_engine import RegistryReadinessEngine
    from app.domains.reporting.services.lineage import DataLineageEngine
    from app.domains.registry_integrations.services.document_renderer import RegistryDocumentRenderer
    from app.domains.assets.models import Asset
    from app.domains.activities.models import Activity
    from app.domains.organizations.models import Organization
    from app.domains.methodologies.models.base_registry import Methodology, MethodologyFamily

    readiness_engine = RegistryReadinessEngine(db)
    lineage_engine = DataLineageEngine(db)
    renderer = RegistryDocumentRenderer()

    readiness = await readiness_engine.evaluate_readiness(project_id=project_id, target_standard=standard)
    lineage = await lineage_engine.get_project_data_lineage(project_id=project_id)

    org = None
    if project.organization_id:
        org_stmt = select(Organization).where(Organization.id == project.organization_id)
        org_res = await db.execute(org_stmt)
        org = org_res.scalar_one_or_none()

    meth = None
    if project.methodology_id:
        m_stmt = select(Methodology).where(Methodology.id == project.methodology_id)
        m_res = await db.execute(m_stmt)
        meth = m_res.scalar_one_or_none()

    sector = None
    if project.sector_id:
        sec_stmt = select(MethodologyFamily).where(MethodologyFamily.id == project.sector_id)
        sec_res = await db.execute(sec_stmt)
        sector = sec_res.scalar_one_or_none()

    asset_stmt = select(Asset).where(Asset.project_id == project_id)
    a_res = await db.execute(asset_stmt)
    assets = a_res.scalars().all()

    asset_ids = [a.id for a in assets]
    if asset_ids:
        act_stmt = select(Activity).where(Activity.asset_id.in_(asset_ids))
    elif project.organization_id:
        act_stmt = select(Activity).where(Activity.organization_id == project.organization_id)
    else:
        act_stmt = select(Activity).where(Activity.id.is_(None))
    act_res = await db.execute(act_stmt)
    activities = act_res.scalars().all()

    base_params = project.baseline_parameters if isinstance(project.baseline_parameters, dict) else {}
    project_context = {
        "id": str(project.id),
        "name": project.name,
        "project_code": lineage.get("project_code", f"PRJ-{str(project.id)[:8]}"),
        "country": project.country or "Nigeria",
        "registry_id": getattr(project, "registry_id", None),
        "developer_name": org.name if org else "Authorized Developer",
        "methodology_code": meth.code if meth else "Standard Methodology",
        "sector_name": sector.name if sector else "Clean Energy / MRV",
        "asset_count": len(assets),
        "activity_count": len(activities),
        "total_tco2e": lineage.get("summary_metrics", {}).get("total_emission_reductions_tco2e", 0.0),
        "qa_qc_rate": lineage.get("summary_metrics", {}).get("lineage_integrity_score", 100.0),
        "authorization_status": readiness.get("authorization_status", "NOT_STARTED"),
        "authorization_reference": base_params.get("authorization_reference", "PENDING_OFFICIAL_FILING"),
        "stakeholder_completed": bool(readiness.get("pillar_breakdown", {}).get("stakeholder_requirements", {}).get("score", 0) > 0),
        "safeguards_cleared": bool(readiness.get("pillar_breakdown", {}).get("safeguards", {}).get("score", 0) > 0),
        "submission_status": readiness.get("readiness_status", "DRAFT"),
    }

    if format.lower() == "json":
        doc_spec = renderer.template_registry.get_document_spec(document_id)
        if not doc_spec:
            raise HTTPException(status_code=404, detail=f"Document specification {document_id} not found.")
        return {
            "document_metadata": doc_spec,
            "project_context": project_context,
            "readiness": readiness,
        }

    try:
        file_bytes, filename, sha256_hash = renderer.render_document(
            document_id=document_id, project_data=project_context, format_type=format
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    media_type = "application/pdf" if format.lower() == "pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return Response(
        content=file_bytes,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Document-SHA256": sha256_hash,
        },
    )


class ITMOAuthorizationRequest(BaseModel):
    project_id: UUID
    acquiring_party: Optional[str] = "Bilateral Partner DNA"
    authorized_use_scope: Optional[str] = "NDC Achievement / Other International Mitigation Purposes (OIMP)"
    cooperative_approach_id: Optional[str] = None
    authorization_reference: Optional[str] = None


from app.core.rbac import require_permission

@router.post("/itmo/authorize")
async def submit_itmo_authorization(
    data: ITMOAuthorizationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("compliance:authorize")),
):
    """
    Formally records and seals an Article 6.2 ITMO authorization for a verified mitigation project.
    """
    from datetime import datetime, timezone
    from sqlalchemy.orm.attributes import flag_modified
    import hashlib

    p_stmt = select(Project).where(Project.id == data.project_id)
    p_res = await db.execute(p_stmt)
    project = p_res.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project with ID {data.project_id} not found.")

    if current_user.role != "SUPER_ADMIN":
        user_org = current_user.organization_id
        if not user_org or str(project.organization_id).lower() != str(user_org).lower():
            raise HTTPException(status_code=403, detail="Forbidden: Cannot authorize ITMOs for another organization's project.")

    # Update project baseline parameters with Article 6 authorization metadata
    params = dict(project.baseline_parameters) if isinstance(project.baseline_parameters, dict) else {}
    params["article_6_authorized"] = True
    params["itmo_authorized_at"] = datetime.now(timezone.utc).isoformat()
    params["authorized_by"] = current_user.email
    params["acquiring_party"] = data.acquiring_party or "Bilateral Partner DNA"
    params["authorized_use_scope"] = data.authorized_use_scope or "NDC Achievement / Other International Mitigation Purposes (OIMP)"
    params["authorization_reference"] = data.authorization_reference or f"DNA/A6/{str(project.country or 'NGA')[:3].upper()}/2026/{str(project.id)[:6].upper()}"
    if data.cooperative_approach_id:
        params["cooperative_approach_id"] = data.cooperative_approach_id
    elif not params.get("cooperative_approach_id"):
        params["cooperative_approach_id"] = f"CA-{str(project.country or 'NGA')[:3].upper()}-2026-{str(project.id)[:6].upper()}"

    project.baseline_parameters = params
    flag_modified(project, "baseline_parameters")

    # Record sync log entry
    from app.domains.registry_integrations.models import RegistrySyncLog
    import uuid
    sync_log = RegistrySyncLog(
        project_id=project.id,
        action="ITMO_AUTHORIZATION",
        status="AUTHORIZED",
        idempotency_key=f"itmo-auth-{project.id}-{uuid.uuid4().hex[:8]}",
        registry_id=uuid.uuid4(),
        request_payload={
            "acquiring_party": params["acquiring_party"],
            "authorized_use_scope": params["authorized_use_scope"],
        },
        response_payload={
            "status": "AUTHORIZED",
            "cooperative_approach_id": params["cooperative_approach_id"],
            "authorized_by": current_user.email,
        }
    )
    db.add(sync_log)
    await db.commit()
    await db.refresh(project)

    # Generate the resulting updated Article 6.2 dossier
    from app.domains.registry_integrations.services.compliance_dossier import RegistryComplianceDossierService
    service = RegistryComplianceDossierService(db)
    dossier = await service.generate_dossier(standard="ARTICLE6_2", project_id=project.id)

    return {
        "status": "AUTHORIZED",
        "message": "Article 6.2 ITMO Authorization successfully registered and sealed.",
        "project_id": str(project.id),
        "project_name": project.name,
        "serial_number": dossier.get("itmo_accounting_ledger", {}).get("serial_number_format"),
        "cumulative_itmos_tco2e": dossier.get("itmo_accounting_ledger", {}).get("cumulative_itmos_generated_tco2e", 0.0),
        "cooperative_approach_id": params["cooperative_approach_id"],
        "acquiring_party": params["acquiring_party"],
        "dossier_sha256": dossier.get("dossier_sha256"),
        "authorized_at": params["itmo_authorized_at"],
        "dossier": dossier,
    }
