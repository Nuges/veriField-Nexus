from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    full_name: str = Field(..., min_length=2, max_length=255)
    password: str = Field(..., min_length=8)
    role: str = Field(default="field_agent")
    organization: Optional[str] = Field(None, max_length=255)
    organization_id: Optional[UUID] = None
    country: Optional[str] = Field(None, max_length=100)
    meta_data: Optional[dict] = Field(default_factory=dict)


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=255)
    avatar_url: Optional[str] = Field(None, max_length=500)
    organization: Optional[str] = Field(None, max_length=255)
    organization_id: Optional[UUID] = None
    phone: Optional[str] = Field(None, max_length=20)
    role: Optional[str] = Field(None, max_length=20)
    status: Optional[str] = Field(None, max_length=20)
    meta_data: Optional[dict] = None


class UserLogin(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    password: str


class UserResponse(BaseModel):
    id: UUID
    email: Optional[str] = None
    phone: Optional[str] = None
    full_name: str
    role: str
    avatar_url: Optional[str] = None
    organization: Optional[str] = None
    organization_id: Optional[UUID] = None
    is_active: Optional[bool] = True
    requires_password_change: Optional[bool] = False
    licensed_methodologies: Optional[List[str]] = None
    country: Optional[str] = None
    version: int
    is_deleted: bool
    meta_data: Optional[dict] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    user: UserResponse
    access_token: str
    token_type: str = "bearer"
    expires_in: int
