"""
=============================================================================
VeriField Nexus — Community Validation Schemas
=============================================================================
Pydantic models for community validation request/response handling.
=============================================================================
"""

from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class CommunityValidationCreate(BaseModel):
    asset_id: UUID
    response: str  # 'yes', 'no', 'pending'
    comment: Optional[str] = None


class CommunityValidationResponse(BaseModel):
    id: UUID
    asset_id: UUID
    validator_id: UUID
    response: str
    timestamp: datetime

    # Joined fields
    property_name: Optional[str] = None
    property_type: Optional[str] = None
    validator_name: Optional[str] = None
    validator_role: Optional[str] = None

    model_config = {"from_attributes": True}


class CommunityValidationListResponse(BaseModel):
    validations: List[CommunityValidationResponse]
    total: int
    page: int
    per_page: int


class CommunityFeedItem(BaseModel):
    """A feed-style view combining validations with user context."""
    id: UUID
    user_name: str
    user_role: str
    action: str  # 'validated', 'flagged', 'submitted'
    content: str
    property_name: Optional[str] = None
    property_type: Optional[str] = None
    response: str
    timestamp: datetime
    upvotes: int = 0


class CommunityFeedResponse(BaseModel):
    posts: List[CommunityFeedItem]
    total: int
    page: int
    per_page: int
