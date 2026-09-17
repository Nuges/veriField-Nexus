from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class VerificationTaskBase(BaseModel):
    project_id: Optional[UUID] = None
    asset_id: Optional[UUID] = None
    verifier_id: Optional[UUID] = None
    deadline: Optional[datetime] = None
    status: str = "ASSIGNED"
    findings: Dict[str, Any] = {}


class VerificationTaskCreate(VerificationTaskBase):
    pass


class VerificationTaskResponse(VerificationTaskBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditReportBase(BaseModel):
    project_id: UUID
    vvb_org_id: UUID
    report_uri: str
    report_hash: str
    is_positive_opinion: bool


class AuditReportCreate(AuditReportBase):
    pass


class AuditReportResponse(AuditReportBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── Verification Package Schemas ─────────────────────────────────────────────

class VerificationPackageCreate(BaseModel):
    project_id: UUID
    monitoring_period_start: date
    monitoring_period_end: date
    package_name: str
    registry_target: str = "PURO_STANDARD"
    audit_type: str = "OUTPUT_AUDIT"


class VerificationPackageResponse(BaseModel):
    id: UUID
    project_id: UUID
    organization_id: UUID
    monitoring_period_start: date
    monitoring_period_end: date
    package_name: str
    package_version: int
    parent_package_id: Optional[UUID] = None
    package_status: str
    registry_target: str
    audit_type: str
    manifest_hash: str
    manifest_json: Dict[str, Any] = {}
    ledger_signature_id: Optional[UUID] = None
    sealed_at: Optional[datetime] = None
    sealed_by_user_id: Optional[UUID] = None
    diff_summary_json: Dict[str, Any] = {}
    completeness_score: float = 0.0
    blocker_reasons: List[Any] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VerificationPackageFindingCreate(BaseModel):
    finding_number: Optional[str] = None
    finding_type: str = "CAR"  # CAR, CL, FAR, NCR
    severity: str = "MAJOR"    # CRITICAL, MAJOR, MINOR, OBSERVATION
    title: str
    description: str
    target_domain: str
    target_record_id: Optional[UUID] = None
    target_field: Optional[str] = None


class VerificationPackageFindingResponse(BaseModel):
    id: UUID
    package_id: UUID
    finding_number: str
    finding_type: str
    severity: str
    title: str
    description: str
    target_domain: str
    target_record_id: Optional[UUID] = None
    target_field: Optional[str] = None
    status: str
    auditor_user_id: Optional[UUID] = None
    auditor_organization: Optional[str] = None
    project_response: Optional[str] = None
    response_submitted_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    resolution_package_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VerificationPackageFindingUpdate(BaseModel):
    project_response: Optional[str] = None
    resolution_notes: Optional[str] = None
    status: Optional[str] = None


class VerificationPackageEvidenceResponse(BaseModel):
    id: UUID
    package_id: UUID
    evidence_category: str
    reference_domain: str
    reference_id: UUID
    title: str
    file_name: str
    file_uri: str
    file_size_bytes: int
    sha256_hash: str
    verified_hash: Optional[str] = None
    integrity_status: str
    uploaded_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VerificationAccessGrantCreate(BaseModel):
    auditor_email: str
    auditor_organization: str
    grantee_role: str = "AUDITOR"
    expires_at: Optional[datetime] = None


class VerificationAccessGrantResponse(BaseModel):
    id: UUID
    package_id: UUID
    auditor_user_id: Optional[UUID] = None
    auditor_email: str
    auditor_organization: str
    grantee_role: str
    is_active: bool
    expires_at: Optional[datetime] = None
    last_accessed_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
