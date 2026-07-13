from datetime import datetime
from typing import Any, Dict
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TrustLogBase(BaseModel):
    activity_id: UUID
    gps_score: float = 0.0
    image_score: float = 0.0
    frequency_score: float = 0.0
    final_score: float = 0.0
    flags: Dict[str, Any] = {}


class TrustLogResponse(TrustLogBase):
    id: UUID
    calculated_at: datetime

    model_config = ConfigDict(from_attributes=True)
