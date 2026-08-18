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


class RegistryConfigResponse(BaseModel):
    """Response schema that NEVER exposes raw credentials."""
    id: UUID
    name: str
    adapter_type: str
    base_url: Optional[str] = None
    is_active: bool = True
    has_credentials: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_safe(cls, obj):
        """Create response with credential redaction."""
        creds = getattr(obj, "credentials", None) or {}
        return cls(
            id=obj.id,
            name=obj.name,
            adapter_type=obj.adapter_type,
            base_url=obj.base_url,
            is_active=obj.is_active,
            has_credentials=bool(creds),
            created_at=obj.created_at,
        )


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
