from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.rbac import (
    ROLE_SUPER_ADMIN,
    normalize_canonical_role,
    require_permission,
    validate_separation_of_duties,
)
from app.core.security import get_current_user
from app.db.session import get_db
from app.domains.authentication.models import User
from app.domains.biochar.services.auditor_workspace_service import AuditorWorkspaceService
from app.domains.biochar.services.package_compiler import BiocharVerificationPackageCompiler
from app.domains.projects.models import Project
from app.domains.verification.models import (
    VerificationAccessGrant,
    VerificationPackage,
    VerificationPackageEvidence,
    VerificationPackageFinding,
)

from .repository import VerificationRepository
from .schemas import (
    AuditReportCreate,
    AuditReportResponse,
    VerificationAccessGrantCreate,
    VerificationAccessGrantResponse,
    VerificationPackageCreate,
    VerificationPackageEvidenceResponse,
    VerificationPackageFindingCreate,
    VerificationPackageFindingResponse,
    VerificationPackageFindingUpdate,
    VerificationPackageResponse,
    VerificationTaskCreate,
    VerificationTaskResponse,
)
from .service import VerificationService

router = APIRouter()


def get_verification_service(db: AsyncSession = Depends(get_db)) -> VerificationService:
    repository = VerificationRepository(db)
    return VerificationService(repository)


@router.post(
    "/tasks",
    response_model=VerificationTaskResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_verification_task(
    data: VerificationTaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("audit:write")),
    service: VerificationService = Depends(get_verification_service),
):
    return await service.create_verification_task(data, actor_id=current_user.id, db=db)


@router.get("", response_model=None)
@router.get("/", response_model=None)
@router.get("/tasks", response_model=None)
@router.get("/audits", response_model=None)
async def get_audits_endpoint(
    status: Optional[str] = None,
    per_page: int = 50,
    page: int = 1,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("audit:read")),
    service: VerificationService = Depends(get_verification_service),
):
    tasks = await service.get_tasks()
    user_canonical = normalize_canonical_role(current_user.role)

    # Scoping: If not super admin, resolve projects in user's tenant or assigned to user
    permitted_project_ids = set()
    if user_canonical != ROLE_SUPER_ADMIN and current_user.organization_id:
        proj_stmt = select(Project.id).where(
            Project.organization_id == current_user.organization_id,
            Project.is_deleted == False,
        )
        proj_res = await db.execute(proj_stmt)
        permitted_project_ids = {row[0] for row in proj_res.fetchall()}

    audits = []
    for t in tasks:
        t_status = (t.status or "pending").lower()
        if status and status.lower() != "all" and t_status != status.lower():
            continue

        # Tenant & Verifier scope check
        if user_canonical != ROLE_SUPER_ADMIN:
            is_assigned = t.verifier_id and str(t.verifier_id) == str(current_user.id)
            is_org_project = t.project_id in permitted_project_ids
            if not is_assigned and not is_org_project:
                continue

        audits.append({
            "id": str(t.id),
            "status": t.status or "pending",
            "deadline": t.deadline.isoformat() if t.deadline else None,
            "property_name": "Registered Carbon Asset",
            "property_address": "Federal Capital Territory, Nigeria",
            "property_type": "Clean Energy",
            "agent_name": "Field Auditor",
            "assigned_agent": str(t.verifier_id) if t.verifier_id else None,
            "findings": t.findings or {},
            "created_at": t.created_at.isoformat() if t.created_at else None
        })
    return {"audits": audits, "total": len(audits), "page": page, "per_page": per_page}


@router.get("/tasks/{task_id}")
@router.get("/audits/{task_id}")
@router.get("/{task_id}")
async def get_audit_by_id(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("audit:read")),
    service: VerificationService = Depends(get_verification_service),
):
    task = await service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Audit task not found")

    # Scoping / BOLA / IDOR protection
    if current_user.role != "SUPER_ADMIN":
        is_assigned_verifier = task.verifier_id and str(task.verifier_id).lower() == str(current_user.id).lower()
        has_org_access = False
        if task.project_id:
            proj_stmt = select(Project.organization_id).where(Project.id == task.project_id)
            proj_res = await db.execute(proj_stmt)
            proj_org = proj_res.scalar_one_or_none()
            if proj_org and current_user.organization_id and str(proj_org).lower() == str(current_user.organization_id).lower():
                has_org_access = True

        if not is_assigned_verifier and not has_org_access:
            raise HTTPException(
                status_code=403,
                detail="Forbidden: Cannot access verification task belonging to another organization or verifier."
            )

    return {
        "id": str(task.id),
        "status": task.status or "pending",
        "deadline": task.deadline.isoformat() if task.deadline else None,
        "property_name": "Registered Carbon Asset",
        "property_address": "Federal Capital Territory, Nigeria",
        "property_type": "Clean Energy",
        "agent_name": "Field Auditor",
        "assigned_agent": str(task.verifier_id) if task.verifier_id else None,
        "findings": task.findings or {},
        "created_at": task.created_at.isoformat() if task.created_at else None
    }


from pydantic import BaseModel
class TaskUpdate(BaseModel):
    status: Optional[str] = None
    deadline: Optional[str] = None
    assigned_agent: Optional[str] = None

@router.patch("/tasks/{task_id}")
@router.patch("/audits/{task_id}")
@router.patch("/{task_id}")
async def update_verification_task(
    task_id: UUID,
    data: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("audit:write")),
    service: VerificationService = Depends(get_verification_service),
):
    task = await service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Scoping / BOLA / IDOR protection
    if current_user.role != "SUPER_ADMIN":
        is_assigned_verifier = task.verifier_id and str(task.verifier_id).lower() == str(current_user.id).lower()
        has_org_admin_access = False
        if task.project_id and current_user.role in ("ORG_ADMIN", "admin"):
            proj_stmt = select(Project.organization_id).where(Project.id == task.project_id)
            proj_res = await db.execute(proj_stmt)
            proj_org = proj_res.scalar_one_or_none()
            if proj_org and current_user.organization_id and str(proj_org).lower() == str(current_user.organization_id).lower():
                has_org_admin_access = True

        if not is_assigned_verifier and not has_org_admin_access:
            raise HTTPException(
                status_code=403,
                detail="Forbidden: Cannot update verification task belonging to another organization or verifier."
            )

    if data.status:
        updated = await service.repository.update_task_status(task_id, data.status, {})
        if not updated:
            raise HTTPException(status_code=404, detail="Task not found")
        return updated
    
    return task


@router.post(
    "/audits", response_model=AuditReportResponse, status_code=status.HTTP_201_CREATED
)
async def submit_audit_report(
    data: AuditReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("audit:write")),
    service: VerificationService = Depends(get_verification_service),
):
    # Enforce Separation of Duties: Check if actor is the developer of the project
    proj_stmt = select(Project).where(Project.id == data.project_id)
    proj_res = await db.execute(proj_stmt)
    proj = proj_res.scalar_one_or_none()
    developer_id = proj.developer_id if proj else None

    validate_separation_of_duties(current_user, developer_id, action="VERIFY")

    return await service.submit_audit_report(data, actor_id=current_user.id, db=db)


@router.get("/sensors/{asset_id}")
async def get_sensor_readings(
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("asset:read")),
):
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=501,
        content={"detail": "Sensor telemetry integration not yet implemented", "asset_id": asset_id},
    )


@router.get("/community/{asset_id}")
async def get_asset_community_validations(
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("asset:read")),
):
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=501,
        content={"detail": "Community validations integration not yet implemented", "asset_id": asset_id},
    )


# ---------------------------------------------------------------------------
# Verification Package & Auditor Workspace Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/packages/compile",
    response_model=VerificationPackageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def compile_verification_package(
    payload: VerificationPackageCreate,
    current_user: User = Depends(require_permission("audit:package:compile")),
    db: AsyncSession = Depends(get_db),
):
    """
    Compiles the project's complete biochar verification data graph into ONE
    immutable, audit-ready verification package linked to the monitoring period.
    """
    compiler = BiocharVerificationPackageCompiler(db)
    return await compiler.compile_package(
        project_id=payload.project_id,
        monitoring_period_start=payload.monitoring_period_start,
        monitoring_period_end=payload.monitoring_period_end,
        package_name=payload.package_name,
        registry_target=payload.registry_target,
        audit_type=payload.audit_type,
        created_by_user_id=current_user.id,
    )


@router.get(
    "/packages",
    response_model=List[VerificationPackageResponse],
)
async def list_verification_packages(
    project_id: Optional[UUID] = None,
    current_user: User = Depends(require_permission("audit:package:read")),
    db: AsyncSession = Depends(get_db),
):
    """Lists verification packages accessible to the user."""
    stmt = select(VerificationPackage).order_by(VerificationPackage.created_at.desc())
    if project_id:
        stmt = stmt.where(VerificationPackage.project_id == project_id)
    elif normalize_canonical_role(current_user.role) != ROLE_SUPER_ADMIN:
        if current_user.organization_id:
            stmt = stmt.where(VerificationPackage.organization_id == current_user.organization_id)

    res = await db.execute(stmt)
    return res.scalars().all()


@router.get(
    "/packages/{package_id}",
    response_model=VerificationPackageResponse,
)
async def get_verification_package(
    package_id: UUID,
    current_user: User = Depends(require_permission("audit:package:read")),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves full verification package with manifest, trace trees, and completeness gates."""
    service = AuditorWorkspaceService(db)
    await service.check_auditor_access(package_id=package_id, user=current_user)

    stmt = select(VerificationPackage).where(VerificationPackage.id == package_id)
    res = await db.execute(stmt)
    pkg = res.scalar_one_or_none()
    if not pkg:
        raise HTTPException(status_code=404, detail=f"VerificationPackage {package_id} not found")
    return pkg


@router.post(
    "/packages/{package_id}/seal",
    response_model=VerificationPackageResponse,
)
async def seal_verification_package(
    package_id: UUID,
    current_user: User = Depends(require_permission("audit:package:compile")),
    db: AsyncSession = Depends(get_db),
):
    """
    Cryptographically seals and submits a VerificationPackage via LedgerService.
    Package version 1 becomes permanently immutable.
    """
    compiler = BiocharVerificationPackageCompiler(db)
    return await compiler.seal_and_submit_package(
        package_id=package_id,
        user=current_user,
    )


@router.get(
    "/packages/{package_id}/evidence",
    response_model=List[VerificationPackageEvidenceResponse],
)
async def list_package_evidence(
    package_id: UUID,
    current_user: User = Depends(require_permission("audit:package:read")),
    db: AsyncSession = Depends(get_db),
):
    """Lists Central Evidence Index items for the verification package."""
    service = AuditorWorkspaceService(db)
    await service.check_auditor_access(package_id=package_id, user=current_user)

    stmt = select(VerificationPackageEvidence).where(
        VerificationPackageEvidence.package_id == package_id
    ).order_by(VerificationPackageEvidence.created_at.asc())
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post(
    "/packages/{package_id}/evidence/{evidence_id}/verify",
    response_model=VerificationPackageEvidenceResponse,
)
async def verify_single_evidence(
    package_id: UUID,
    evidence_id: UUID,
    simulated_tamper: bool = False,
    current_user: User = Depends(require_permission("audit:package:read")),
    db: AsyncSession = Depends(get_db),
):
    """Verifies SHA-256 cryptographic digest of an evidence item."""
    service = AuditorWorkspaceService(db)
    await service.check_auditor_access(package_id=package_id, user=current_user)
    return await service.verify_evidence_integrity(
        package_id=package_id,
        evidence_id=evidence_id,
        simulated_tamper=simulated_tamper,
    )


@router.post(
    "/packages/{package_id}/evidence/verify-all",
)
async def verify_all_package_evidence(
    package_id: UUID,
    current_user: User = Depends(require_permission("audit:package:read")),
    db: AsyncSession = Depends(get_db),
):
    """Verifies all evidence items for a verification package."""
    service = AuditorWorkspaceService(db)
    await service.check_auditor_access(package_id=package_id, user=current_user)
    return await service.verify_all_package_evidence(package_id=package_id)


@router.get(
    "/packages/{package_id}/evidence/{evidence_id}/content",
)
async def get_evidence_file_content(
    package_id: UUID,
    evidence_id: UUID,
    current_user: User = Depends(require_permission("audit:package:read")),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves genuine raw bytes of an evidence file from storage with SHA-256 validation.
    Enforces scoped access: 403 on unassigned, expired grant, revoked grant, foreign tenant.
    """
    service = AuditorWorkspaceService(db)
    content_bytes, media_type, filename, sha256_hash, integrity_status = await service.get_evidence_content(
        package_id=package_id,
        evidence_id=evidence_id,
        user=current_user,
    )
    return Response(
        content=content_bytes,
        media_type=media_type,
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "X-Evidence-Hash": sha256_hash,
            "X-Integrity-Status": integrity_status,
        },
    )


@router.post(
    "/packages/{package_id}/findings",
    response_model=VerificationPackageFindingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_package_finding(
    package_id: UUID,
    payload: VerificationPackageFindingCreate,
    current_user: User = Depends(require_permission("audit:finding:create")),
    db: AsyncSession = Depends(get_db),
):
    """
    Creates an Auditor Finding (CAR, CL, FAR, NCR) on a Verification Package.
    Enforces Separation of Duties: user must be an accredited auditor/verifier.
    """
    service = AuditorWorkspaceService(db)
    await service.check_auditor_access(package_id=package_id, user=current_user)
    return await service.create_finding(
        package_id=package_id,
        auditor=current_user,
        finding_type=payload.finding_type,
        severity=payload.severity,
        title=payload.title,
        description=payload.description,
        target_domain=payload.target_domain,
        target_record_id=payload.target_record_id,
        target_field=payload.target_field,
    )


@router.get(
    "/packages/{package_id}/findings",
    response_model=List[VerificationPackageFindingResponse],
)
async def list_package_findings(
    package_id: UUID,
    current_user: User = Depends(require_permission("audit:package:read")),
    db: AsyncSession = Depends(get_db),
):
    """Lists audit findings logged against a verification package."""
    service = AuditorWorkspaceService(db)
    await service.check_auditor_access(package_id=package_id, user=current_user)

    stmt = select(VerificationPackageFinding).where(
        VerificationPackageFinding.package_id == package_id
    ).order_by(VerificationPackageFinding.created_at.asc())
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post(
    "/findings/{finding_id}/respond",
    response_model=VerificationPackageFindingResponse,
)
async def respond_to_package_finding(
    finding_id: UUID,
    payload: VerificationPackageFindingUpdate,
    current_user: User = Depends(require_permission("audit:finding:respond")),
    db: AsyncSession = Depends(get_db),
):
    """
    Submits project developer response to an auditor finding.
    Enforces SoD: Auditor cannot respond on behalf of developer.
    """
    if not payload.project_response:
        raise HTTPException(status_code=400, detail="project_response is required")
    service = AuditorWorkspaceService(db)
    return await service.submit_finding_response(
        finding_id=finding_id,
        developer=current_user,
        project_response=payload.project_response,
    )


@router.post(
    "/findings/{finding_id}/resolve",
    response_model=VerificationPackageFindingResponse,
)
async def resolve_package_finding(
    finding_id: UUID,
    payload: VerificationPackageFindingUpdate,
    resolution_package_id: Optional[UUID] = None,
    current_user: User = Depends(require_permission("audit:finding:resolve")),
    db: AsyncSession = Depends(get_db),
):
    """
    Closes or resolves an auditor finding.
    Enforces SoD: Only accredited auditors can resolve findings.
    """
    if not payload.resolution_notes:
        raise HTTPException(status_code=400, detail="resolution_notes is required")
    service = AuditorWorkspaceService(db)
    return await service.resolve_finding(
        finding_id=finding_id,
        auditor=current_user,
        resolution_notes=payload.resolution_notes,
        status_action=payload.status or "RESOLVED",
        resolution_package_id=resolution_package_id,
    )


from pydantic import BaseModel
class AuditDecisionRequest(BaseModel):
    decision: str  # VERIFIED, REJECTED
    decision_notes: str


@router.post(
    "/packages/{package_id}/decision",
    response_model=VerificationPackageResponse,
)
async def record_audit_decision(
    package_id: UUID,
    payload: AuditDecisionRequest,
    current_user: User = Depends(require_permission("audit:package:sign")),
    db: AsyncSession = Depends(get_db),
):
    """Records final audit decision (VERIFIED, REJECTED) on a VerificationPackage."""
    service = AuditorWorkspaceService(db)
    await service.check_auditor_access(package_id=package_id, user=current_user)
    return await service.record_audit_decision(
        package_id=package_id,
        auditor=current_user,
        decision=payload.decision,
        decision_notes=payload.decision_notes,
    )


@router.post(
    "/packages/{package_id}/grants",
    response_model=VerificationAccessGrantResponse,
    status_code=status.HTTP_201_CREATED,
)
async def grant_auditor_access(
    package_id: UUID,
    payload: VerificationAccessGrantCreate,
    current_user: User = Depends(require_permission("audit:grant:manage")),
    db: AsyncSession = Depends(get_db),
):
    """Grants scoped external auditor access to a VerificationPackage."""
    service = AuditorWorkspaceService(db)
    return await service.grant_auditor_access(
        package_id=package_id,
        granter=current_user,
        auditor_email=payload.auditor_email,
        auditor_organization=payload.auditor_organization,
        grantee_role=payload.grantee_role,
        expires_at=payload.expires_at,
    )


@router.get(
    "/packages/{package_id}/grants",
    response_model=List[VerificationAccessGrantResponse],
)
async def list_package_grants(
    package_id: UUID,
    current_user: User = Depends(require_permission("audit:package:read")),
    db: AsyncSession = Depends(get_db),
):
    """Lists external access grants for a VerificationPackage."""
    service = AuditorWorkspaceService(db)
    await service.check_auditor_access(package_id=package_id, user=current_user)

    stmt = select(VerificationAccessGrant).where(
        VerificationAccessGrant.package_id == package_id
    )
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get(
    "/packages/{package_id}/export",
)
async def export_package_bundle(
    package_id: UUID,
    current_user: User = Depends(require_permission("audit:package:read")),
    db: AsyncSession = Depends(get_db),
):
    """Exports audit package bundle (manifest JSON + evidence CSV + findings CSV)."""
    service = AuditorWorkspaceService(db)
    await service.check_auditor_access(package_id=package_id, user=current_user)
    return await service.export_package_bundle(package_id=package_id)


@router.get(
    "/packages/{package_id}/export/archive",
)
async def export_package_archive_endpoint(
    package_id: UUID,
    current_user: User = Depends(require_permission("audit:package:read")),
    db: AsyncSession = Depends(get_db),
):
    """Exports full audit package archive (ZIP containing all reports and CHECKSUMS.sha256)."""
    service = AuditorWorkspaceService(db)
    await service.check_auditor_access(package_id=package_id, user=current_user)
    zip_bytes, filename, checksums = await service.export_package_archive(package_id=package_id)
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Package-Checksums": str(checksums),
        },
    )


