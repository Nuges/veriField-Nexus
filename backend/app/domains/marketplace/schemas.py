from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ListingBase(BaseModel):
    org_id: UUID
    project_id: UUID
    quantity: float
    price_per_unit: float
    currency: str = "USD"
    status: str = "ACTIVE"


class ListingCreate(ListingBase):
    pass


class ListingResponse(ListingBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
