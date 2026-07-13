from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EvidenceBase(BaseModel):
    activity_id: UUID
    file_uri: str
    file_hash: str
    evidence_type: str
    metadata_json: Dict[str, Any] = {}


class EvidenceCreate(EvidenceBase):
    pass


class EvidenceUpdate(BaseModel):
    status: str


class EvidenceResponse(EvidenceBase):
    id: UUID
    status: str
    uploaded_by: Optional[UUID] = None
    verified_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
