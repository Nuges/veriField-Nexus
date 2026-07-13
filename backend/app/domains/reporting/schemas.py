from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ReportBase(BaseModel):
    title: str
    report_type: str
    parameters: Dict[str, Any] = {}


class ReportCreate(ReportBase):
    org_id: UUID


class ReportResponse(ReportBase):
    id: UUID
    org_id: UUID
    status: str
    file_uri: Optional[str] = None
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
