from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class VerificationTaskBase(BaseModel):
    project_id: UUID
    verifier_id: Optional[UUID] = None
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
