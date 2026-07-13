from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TransactionBase(BaseModel):
    from_org_id: UUID
    to_org_id: UUID
    amount: float
    currency: str = "USD"
    project_id: Optional[UUID] = None
    status: str = "PENDING"
    metadata_json: Dict[str, Any] = {}


class TransactionCreate(TransactionBase):
    pass


class TransactionResponse(TransactionBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
