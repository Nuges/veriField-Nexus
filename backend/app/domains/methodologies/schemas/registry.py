from datetime import date
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# Shared generic schemas
class RegistrySchema(BaseModel):
    id: UUID
    code: str
    name: str
    description: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


class FamilySchema(BaseModel):
    id: UUID
    code: str
    name: str

    class Config:
        from_attributes = True


class MethodologyVersionSchema(BaseModel):
    id: UUID
    version: str
    status: str
    release_date: date
    retirement_date: Optional[date]

    class Config:
        from_attributes = True


class MethodologySchema(BaseModel):
    id: UUID
    code: str
    name: str
    description: Optional[str]
    registry: RegistrySchema
    family: FamilySchema
    versions: List[MethodologyVersionSchema] = []
    ui_config: Optional[Dict[str, Any]] = Field(default_factory=dict)
    form_schema: Optional[Dict[str, Any]] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class MonitoringTemplateSchema(BaseModel):
    id: UUID
    code: str
    name: str
    data_type: str
    unit: Optional[str]
    validation_schema: Dict[str, Any]

    class Config:
        from_attributes = True


class MethodologyCreate(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    registry_id: UUID
    family_id: UUID


class MethodologyVersionCreate(BaseModel):
    version: str
    release_date: date
    migration_notes: Optional[str] = None


class MethodologyVersionStatusUpdate(BaseModel):
    status: str  # 'draft', 'active', 'deprecated', 'retired'
    retirement_date: Optional[date] = None
