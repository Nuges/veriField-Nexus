from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProgrammeBase(BaseModel):
    name: str
    org_id: UUID
    jurisdiction_id: Optional[UUID] = None
    funding_sources: List[str] = []
    budget: float = 0.0
    status: str = "ACTIVE"
    version: int = 1


class ProgrammeCreate(ProgrammeBase):
    pass


class ProgrammeResponse(ProgrammeBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
