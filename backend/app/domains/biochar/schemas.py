from pydantic import BaseModel, ConfigDict, Field

from typing import Optional, Dict, Any, List

from datetime import datetime

from uuid import UUID



class BiocharBatchCreate(BaseModel):

    project_id: UUID

    batch_number: str

    facility_name: str

    kiln_id: str

    feedstock_type: str

    feedstock_weight_tonnes: float = Field(..., gt=0)

    moisture_content_pct: float = Field(..., ge=0, le=100)

    origin_location: Optional[str] = None

    pyrolysis_temp_celsius: float = Field(..., ge=350, le=1000)

    residence_time_minutes: float = Field(..., gt=0)

    biochar_yield_tonnes: float = Field(..., gt=0)

    fixed_carbon_pct: float = Field(75.0, ge=0, le=100)

    ash_content_pct: float = Field(5.0, ge=0, le=100)

    molar_h_c_ratio: float = Field(0.4, ge=0, le=1.0)

    lab_report_number: Optional[str] = None

    lab_document_url: Optional[str] = None



class BiocharBatchResponse(BaseModel):

    id: UUID

    project_id: UUID

    batch_number: str

    facility_name: str

    kiln_id: str

    feedstock_type: str

    feedstock_weight_tonnes: float

    biochar_yield_tonnes: float

    fixed_carbon_pct: float

    molar_h_c_ratio: float

    carbon_permanence_factor: float

    net_co2e_removed_tonnes: float

    quality_grade: str

    status: str

    has_anomaly: bool

    anomaly_reason: Optional[str] = None

    created_at: datetime



    model_config = ConfigDict(from_attributes=True)



class BiocharSummaryResponse(BaseModel):

    total_batches: int

    total_feedstock_tonnes: float

    total_biochar_produced_tonnes: float

    total_net_co2e_removed_tonnes: float

    grade_a_percentage: float

    detected_anomalies_count: int
