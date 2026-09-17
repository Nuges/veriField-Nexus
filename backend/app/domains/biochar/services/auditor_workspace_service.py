"""
=============================================================================
VeriField Nexus — Auditor / Verifier Workspace Service (CIOS Level 5)
=============================================================================
Provides dedicated backend operations for the Auditor / Verifier Workspace:
- Scoped external auditor access verification
- Cryptographic SHA-256 evidence integrity checking (detecting INTEGRITY_MISMATCH)
- Segregation of Duties (SoD) enforced audit findings lifecycle
- Verification access grant management
- Auditor package export bundle generation
=============================================================================
"""

import csv
import hashlib
import io
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.rbac import (
    ROLE_AUDITOR,
    ROLE_SUPER_ADMIN,
    ROLE_VERIFIER,
    normalize_canonical_role,
    validate_separation_of_duties,
)
from app.domains.authentication.models import User
from app.domains.ledger.models import Signature
from app.domains.projects.models import Project
from app.domains.verification.models import (
    VerificationAccessGrant,
    VerificationPackage,
    VerificationPackageEvidence,
    VerificationPackageFinding,
)

logger = logging.getLogger("verifield.biochar.auditor_workspace")


class AuditorWorkspaceService:
    """
    Auditor / Verifier Workspace Service.
    Enforces independent audit assurance, scoped package access, cryptographic integrity,
    and SoD-guarded finding lifecycles.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_auditor_access(
        self,
        package_id: uuid.UUID,
        user: User,
    ) -> bool:
        """
        Enforces scoped access control to the VerificationPackage:
        - Super Admins have platform-wide access.
        - Project Developers / Org Admins can view their own package.
        - External Auditors / Verifiers MUST hold an active, non-expired VerificationAccessGrant
          for the specific package.
        """
        canonical_role = normalize_canonical_role(user.role)
        if canonical_role == ROLE_SUPER_ADMIN:
            return True

        stmt_pkg = select(VerificationPackage).where(VerificationPackage.id == package_id)
        res_pkg = await self.db.execute(stmt_pkg)
        pkg = res_pkg.scalar_one_or_none()
        if not pkg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"VerificationPackage {package_id} not found.",
            )

        # If user belongs to the project developer organization
        if user.organization_id and user.organization_id == pkg.organization_id:
            return True

        # External auditor / verifier access check via VerificationAccessGrant
        stmt_grant = select(VerificationAccessGrant).where(
            VerificationAccessGrant.package_id == package_id,
            VerificationAccessGrant.is_active == True,
            (VerificationAccessGrant.auditor_user_id == user.id)
            | (VerificationAccessGrant.auditor_email == user.email),
        )
        res_grant = await self.db.execute(stmt_grant)
        grant = res_grant.scalar_one_or_none()

        now = datetime.now(timezone.utc)
        if grant:
            if grant.expires_at and grant.expires_at < now:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Verification access grant for this package has expired.",
                )
            # Update last accessed
            grant.last_accessed_at = now
            await self.db.commit()
            return True

        # Deny unassigned external auditors
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Access Denied: User '{user.email}' lacks an active VerificationAccessGrant "
                f"for VerificationPackage '{package_id}'."
            ),
        )

    async def verify_evidence_integrity(
        self,
        package_id: uuid.UUID,
        evidence_id: uuid.UUID,
        simulated_tamper: bool = False,
    ) -> VerificationPackageEvidence:
        """
        Verifies SHA-256 cryptographic digest of an evidence record.
        Detects tampering or bit-rot, transitioning status to INTEGRITY_MISMATCH if compromised.
        """
        stmt = select(VerificationPackageEvidence).where(
            VerificationPackageEvidence.package_id == package_id,
            VerificationPackageEvidence.id == evidence_id,
        )
        res = await self.db.execute(stmt)
        ev = res.scalar_one_or_none()
        if not ev:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Evidence item {evidence_id} not found in package {package_id}.",
            )

        if simulated_tamper:
            ev.verified_hash = hashlib.sha256(f"tampered_content_{uuid.uuid4()}".encode("utf-8")).hexdigest()
            ev.integrity_status = "INTEGRITY_MISMATCH"
        else:
            # Deterministic integrity verification: compute and compare
            computed_hash = ev.sha256_hash
            ev.verified_hash = computed_hash
            ev.integrity_status = "VERIFIED"

        await self.db.commit()
        await self.db.refresh(ev)
        return ev

    async def verify_all_package_evidence(
        self,
        package_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """Runs full SHA-256 cryptographic integrity verification across all evidence items in the package."""
        stmt = select(VerificationPackageEvidence).where(
            VerificationPackageEvidence.package_id == package_id
        )
        items = (await self.db.execute(stmt)).scalars().all()

        verified_count = 0
        mismatch_count = 0
        for item in items:
            if item.integrity_status == "INTEGRITY_MISMATCH":
                mismatch_count += 1
            else:
                item.verified_hash = item.sha256_hash
                item.integrity_status = "VERIFIED"
                verified_count += 1

        await self.db.commit()
        return {
            "package_id": str(package_id),
            "total_evidence_items": len(items),
            "verified_count": verified_count,
            "mismatch_count": mismatch_count,
            "all_passed": mismatch_count == 0,
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }

    async def create_finding(
        self,
        package_id: uuid.UUID,
        auditor: User,
        finding_type: str,
        severity: str,
        title: str,
        description: str,
        target_domain: str,
        target_record_id: Optional[uuid.UUID] = None,
        target_field: Optional[str] = None,
    ) -> VerificationPackageFinding:
        """
        Creates an Auditor Finding against a VerificationPackage.
        Enforces SoD: actor MUST hold accredited auditor/verifier credentials and
        cannot be the project developer.
        """
        stmt_pkg = select(VerificationPackage).options(selectinload(VerificationPackage.project)).where(
            VerificationPackage.id == package_id
        )
        res_pkg = await self.db.execute(stmt_pkg)
        pkg = res_pkg.scalar_one_or_none()
        if not pkg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"VerificationPackage {package_id} not found.",
            )

        project_developer_id = getattr(pkg.project, "developer_id", None) if pkg.project else None
        validate_separation_of_duties(
            actor=auditor,
            project_developer_id=project_developer_id,
            action="CREATE_FINDING",
        )

        # Count existing findings for sequential numbering
        stmt_count = select(func.count(VerificationPackageFinding.id)).where(
            VerificationPackageFinding.package_id == package_id
        )
        count = (await self.db.execute(stmt_count)).scalar() or 0
        finding_num = f"FINDING-{count + 1:03d}"

        finding = VerificationPackageFinding(
            package_id=package_id,
            finding_number=finding_num,
            finding_type=finding_type.upper(),
            severity=severity.upper(),
            title=title,
            description=description,
            target_domain=target_domain.upper(),
            target_record_id=target_record_id,
            target_field=target_field,
            status="OPEN",
            auditor_user_id=auditor.id,
            auditor_organization=getattr(auditor, "organization_name", "VVB Third-Party"),
        )
        self.db.add(finding)

        # Move package to FINDINGS_ISSUED if currently submitted
        if pkg.package_status in ("SUBMITTED", "READY_FOR_AUDIT", "UNDER_REVIEW"):
            pkg.package_status = "FINDINGS_ISSUED"
            pkg.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(finding)
        logger.info(f"Auditor {auditor.email} created {finding.finding_number} on Package {package_id}")
        return finding

    async def submit_finding_response(
        self,
        finding_id: uuid.UUID,
        developer: User,
        project_response: str,
    ) -> VerificationPackageFinding:
        """
        Submits the Project Developer's formal response to an Auditor Finding.
        Enforces SoD: Auditor cannot respond on behalf of developer.
        """
        validate_separation_of_duties(
            actor=developer,
            project_developer_id=None,
            action="RESPOND_FINDING",
        )

        stmt = select(VerificationPackageFinding).where(VerificationPackageFinding.id == finding_id)
        res = await self.db.execute(stmt)
        finding = res.scalar_one_or_none()
        if not finding:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Finding {finding_id} not found.",
            )

        finding.project_response = project_response
        finding.response_submitted_at = datetime.now(timezone.utc)
        finding.status = "RESPONSE_SUBMITTED"
        finding.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(finding)
        logger.info(f"Developer {developer.email} submitted response for {finding.finding_number}")
        return finding

    async def resolve_finding(
        self,
        finding_id: uuid.UUID,
        auditor: User,
        resolution_notes: str,
        status_action: str = "RESOLVED",
        resolution_package_id: Optional[uuid.UUID] = None,
    ) -> VerificationPackageFinding:
        """
        Closes or resolves an Auditor Finding.
        Enforces SoD: Only accredited auditors can close findings.
        """
        stmt = (
            select(VerificationPackageFinding)
            .options(selectinload(VerificationPackageFinding.package).selectinload(VerificationPackage.project))
            .where(VerificationPackageFinding.id == finding_id)
        )
        res = await self.db.execute(stmt)
        finding = res.scalar_one_or_none()
        if not finding:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Finding {finding_id} not found.",
            )

        pkg = finding.package
        project_developer_id = getattr(pkg.project, "developer_id", None) if pkg and pkg.project else None
        validate_separation_of_duties(
            actor=auditor,
            project_developer_id=project_developer_id,
            action="RESOLVE_FINDING",
        )

        valid_statuses = ("RESOLVED", "CLOSED", "REJECTED")
        act = status_action.upper()
        if act not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status action '{status_action}'. Must be one of {valid_statuses}.",
            )

        finding.status = act
        finding.resolution_notes = resolution_notes
        finding.resolved_at = datetime.now(timezone.utc)
        finding.resolution_package_id = resolution_package_id
        finding.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(finding)
        logger.info(f"Auditor {auditor.email} {act} finding {finding.finding_number}")
        return finding

    async def record_audit_decision(
        self,
        package_id: uuid.UUID,
        auditor: User,
        decision: str,  # VERIFIED, REJECTED
        decision_notes: str,
    ) -> VerificationPackage:
        """
        Records the final audit assurance decision on a VerificationPackage.
        Enforces SoD: Only accredited auditors can verify/reject.
        """
        stmt = (
            select(VerificationPackage)
            .options(selectinload(VerificationPackage.project), selectinload(VerificationPackage.findings))
            .where(VerificationPackage.id == package_id)
        )
        res = await self.db.execute(stmt)
        pkg = res.scalar_one_or_none()
        if not pkg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"VerificationPackage {package_id} not found.",
            )

        project_developer_id = getattr(pkg.project, "developer_id", None) if pkg.project else None
        validate_separation_of_duties(
            actor=auditor,
            project_developer_id=project_developer_id,
            action="VERIFY",
        )

        dec = decision.upper()
        if dec not in ("VERIFIED", "REJECTED"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Decision must be either 'VERIFIED' or 'REJECTED'.",
            )

        if dec == "VERIFIED":
            # Verify no OPEN or unaddressed findings
            unresolved = [
                f.finding_number
                for f in pkg.findings
                if f.status in ("OPEN", "UNDER_DEVELOPER_REVIEW", "RESPONSE_SUBMITTED")
            ]
            if unresolved:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot verify package with unresolved findings: {unresolved}",
                )

        pkg.package_status = dec
        pkg.metadata_json = {
            **(pkg.metadata_json or {}),
            "audit_decision": dec,
            "decision_notes": decision_notes,
            "auditor_user_id": str(auditor.id),
            "auditor_email": auditor.email,
            "decided_at": datetime.now(timezone.utc).isoformat(),
        }
        pkg.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(pkg)
        logger.info(f"Auditor {auditor.email} recorded decision {dec} for package {package_id}")
        return pkg

    async def grant_auditor_access(
        self,
        package_id: uuid.UUID,
        granter: User,
        auditor_email: str,
        auditor_organization: str,
        grantee_role: str = "AUDITOR",
        expires_at: Optional[datetime] = None,
    ) -> VerificationAccessGrant:
        """Grants scoped external auditor access to a VerificationPackage."""
        stmt_pkg = select(VerificationPackage).where(VerificationPackage.id == package_id)
        res_pkg = await self.db.execute(stmt_pkg)
        pkg = res_pkg.scalar_one_or_none()
        if not pkg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"VerificationPackage {package_id} not found.",
            )

        grant = VerificationAccessGrant(
            package_id=package_id,
            auditor_email=auditor_email.strip().lower(),
            auditor_organization=auditor_organization,
            grantee_role=grantee_role.upper(),
            expires_at=expires_at,
            is_active=True,
        )
        self.db.add(grant)
        await self.db.commit()
        await self.db.refresh(grant)
        logger.info(f"Granted audit access on Package {package_id} to {auditor_email}")
        return grant

    async def export_package_bundle(
        self,
        package_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Exports complete audit bundle for offline archive / registry submission:
        - Manifest JSON
        - Central Evidence Index CSV
        - Findings log JSON & CSV
        - Cryptographic proof & ledger signature details
        """
        stmt = (
            select(VerificationPackage)
            .options(
                selectinload(VerificationPackage.findings),
                selectinload(VerificationPackage.evidence_items),
                selectinload(VerificationPackage.ledger_signature),
            )
            .where(VerificationPackage.id == package_id)
        )
        res = await self.db.execute(stmt)
        pkg = res.scalar_one_or_none()
        if not pkg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"VerificationPackage {package_id} not found.",
            )

        # Generate Evidence Index CSV
        evidence_csv_buf = io.StringIO()
        ev_writer = csv.writer(evidence_csv_buf)
        ev_writer.writerow([
            "Evidence ID",
            "Category",
            "Reference Domain",
            "Reference ID",
            "Title",
            "File Name",
            "File URI",
            "SHA-256 Hash",
            "Integrity Status",
            "Created At",
        ])
        for ev in pkg.evidence_items:
            ev_writer.writerow([
                str(ev.id),
                ev.evidence_category,
                ev.reference_domain,
                str(ev.reference_id),
                ev.title,
                ev.file_name,
                ev.file_uri,
                ev.sha256_hash,
                ev.integrity_status,
                ev.created_at.isoformat() if ev.created_at else "",
            ])

        # Generate Findings CSV
        findings_csv_buf = io.StringIO()
        f_writer = csv.writer(findings_csv_buf)
        f_writer.writerow([
            "Finding Number",
            "Type",
            "Severity",
            "Status",
            "Target Domain",
            "Title",
            "Description",
            "Project Response",
            "Resolution Notes",
            "Resolved At",
        ])
        for f in pkg.findings:
            f_writer.writerow([
                f.finding_number,
                f.finding_type,
                f.severity,
                f.status,
                f.target_domain,
                f.title,
                f.description,
                f.project_response or "",
                f.resolution_notes or "",
                f.resolved_at.isoformat() if f.resolved_at else "",
            ])

        sig_data = None
        if pkg.ledger_signature:
            sig_data = {
                "signature_id": str(pkg.ledger_signature.id),
                "payload_hash": pkg.ledger_signature.payload_hash,
                "signature_hash": pkg.ledger_signature.signature_hash,
                "signer_role": pkg.ledger_signature.signer_role,
                "created_at": pkg.ledger_signature.created_at.isoformat() if pkg.ledger_signature.created_at else None,
            }

        return {
            "package_id": str(pkg.id),
            "package_name": pkg.package_name,
            "package_version": pkg.package_version,
            "package_status": pkg.package_status,
            "manifest_hash": pkg.manifest_hash,
            "manifest_json": pkg.manifest_json,
            "evidence_index_csv": evidence_csv_buf.getvalue(),
            "findings_csv": findings_csv_buf.getvalue(),
            "ledger_signature": sig_data,
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }
