from datetime import datetime

from typing import List, Optional

from uuid import UUID



from pydantic import BaseModel, Field





class UserCreate(BaseModel):

    email: Optional[str] = Field(None, max_length=255)

    phone: Optional[str] = Field(None, max_length=20)

    full_name: str = Field(..., min_length=2, max_length=255)

    password: Optional[str] = Field(None)

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

    status: Optional[str] = "active"

    avatar_url: Optional[str] = None

    organization: Optional[str] = None

    organization_id: Optional[UUID] = None

    is_active: Optional[bool] = True

    requires_password_change: Optional[bool] = False

    licensed_methodologies: Optional[List[str]] = None

    licensed_sectors: Optional[List[str]] = None

    country: Optional[str] = None

    version: Optional[int] = 1

    is_deleted: Optional[bool] = False

    meta_data: Optional[dict] = Field(default_factory=dict)

    created_at: Optional[datetime] = None

    updated_at: Optional[datetime] = None



    model_config = {"from_attributes": True}





class ProjectMembershipCreatePayload(BaseModel):

    project_id: UUID

    role: str = "FIELD_AGENT"





class AdminUserCreatePayload(BaseModel):

    full_name: str = Field(..., min_length=2, max_length=255)

    email: str = Field(..., max_length=255)

    phone: Optional[str] = Field(None, max_length=20)

    job_title: Optional[str] = Field(None, max_length=100)

    role: str = Field(..., max_length=50)

    organization_id: Optional[UUID] = None

    password: Optional[str] = None

    project_memberships: Optional[List[ProjectMembershipCreatePayload]] = Field(default_factory=list)

    meta_data: Optional[dict] = Field(default_factory=dict)





class AdminUserCreateResponse(BaseModel):

    user: UserResponse

    temporary_password: Optional[str] = None

    assigned_memberships_count: int = 0

    message: str = "Account provisioned successfully"





class AuthResponse(BaseModel):

    user: UserResponse

    access_token: str

    token_type: str = "bearer"

    expires_in: int
