"""
=============================================================================
VeriField Nexus — Document Intelligence Schemas
=============================================================================
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class DocumentFraudFlagResponse(BaseModel):
    id: UUID
    document_id: UUID
    organization_id: UUID
    flag_type: str
    severity: str
    description: str
    evidence_details: Dict[str, Any] = {}
    resolved: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectDocumentResponse(BaseModel):
    id: UUID
    organization_id: UUID
    project_id: Optional[UUID] = None
    sector_id: Optional[UUID] = None
    methodology_id: Optional[UUID] = None
    document_type: str
    title: str
    original_filename: str
    mime_type: str
    file_size: int
    sha256: str
    status: str
    parser_status: str
    extraction_status: str
    verification_status: str
    trust_score: float
    trust_breakdown: Dict[str, Any] = {}
    extracted_data: Dict[str, Any] = {}
    version: int = 1
    parent_document_id: Optional[UUID] = None
    uploaded_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    fraud_flags: List[DocumentFraudFlagResponse] = []

    model_config = ConfigDict(from_attributes=True)


class DocumentUploadResponse(BaseModel):
    document: ProjectDocumentResponse
    message: str
    processing_status: str


class DocumentSearchResult(BaseModel):
    document_id: str
    title: str
    document_type: str
    page_number: Optional[int] = None
    section: Optional[str] = None
    chunk_index: int
    content: str
    score: Optional[float] = None
    citation: str
