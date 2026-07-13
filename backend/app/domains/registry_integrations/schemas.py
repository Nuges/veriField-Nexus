from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RegistryConfigBase(BaseModel):
    name: str
    adapter_type: str
    base_url: Optional[str] = None
    is_active: bool = True
    credentials: Dict[str, Any] = Field(default_factory=dict)


class RegistryConfigCreate(RegistryConfigBase):
    pass


class RegistryConfigResponse(RegistryConfigBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RegistrySyncLogResponse(BaseModel):
    id: UUID
    registry_id: UUID
    project_id: Optional[UUID]
    action: str
    status: str
    idempotency_key: str
    request_payload: Optional[Dict[str, Any]]
    response_payload: Optional[Dict[str, Any]]
    error_message: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class SyncActionRequest(BaseModel):
    project_id: UUID
    action: str  # 'registerProject', 'issueCredits', 'retireCredits'
    payload: Dict[str, Any]
