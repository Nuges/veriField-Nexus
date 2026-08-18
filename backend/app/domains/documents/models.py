"""
=============================================================================
VeriField Nexus — Document Intelligence Models
=============================================================================
Defines ProjectDocument, DocumentChunk, and DocumentFraudFlag models
with strict multi-tenant isolation, sector/methodology binding, and fraud audit trails.
=============================================================================
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ProjectDocument(Base):
    """
    Project-level and Organization-level supporting documents (PDDs, Monitoring Reports, etc.)
    with complete provenance, cryptographic hashes, parsing statuses, and fraud scores.
    """

    __tablename__ = "project_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    sector_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("methodology_families.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    methodology_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("methodologies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Document Taxonomy
    document_type: Mapped[str] = mapped_column(
        String(60),
        nullable=False,
        index=True,
    )  # PDD, MONITORING_REPORT, VALIDATION_REPORT, VERIFICATION_REPORT, METHODOLOGY,
       # STAKEHOLDER_DOCUMENT, LEGAL_DOCUMENT, CALIBRATION_DOCUMENT, FIELD_REPORT,
       # MRV_SUPPORTING_DOCUMENT, OTHER_SUPPORTING_DOCUMENT

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Processing & Verification Lifecycle
    status: Mapped[str] = mapped_column(
        String(50),
        default="UPLOADED",
        index=True,
    )  # UPLOADING, UPLOADED, PROCESSING, PROCESSED, OCR_REQUIRED, FAILED, REVIEW_REQUIRED, VERIFIED, REJECTED

    parser_status: Mapped[str] = mapped_column(String(50), default="PENDING")
    extraction_status: Mapped[str] = mapped_column(String(50), default="PENDING")
    verification_status: Mapped[str] = mapped_column(String(50), default="UNVERIFIED")

    # Trust Scoring & Reconciliation Breakdown
    trust_score: Mapped[float] = mapped_column(Float, default=100.0)
    trust_breakdown: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    extracted_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)

    # Versioning & Audit
    version: Mapped[int] = mapped_column(Integer, default=1)
    parent_document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("project_documents.id", ondelete="SET NULL"),
        nullable=True,
    )

    uploaded_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    fraud_flags: Mapped[list["DocumentFraudFlag"]] = relationship(
        "DocumentFraudFlag", back_populates="document", lazy="selectin", cascade="all, delete-orphan"
    )


    __table_args__ = (
        Index("ix_project_documents_org_project", "organization_id", "project_id"),
        Index("ix_project_documents_sha_org", "sha256", "organization_id"),
    )


class DocumentFraudFlag(Base):
    """
    Evidence-backed discrepancy & fraud audit logs for documents.
    """

    __tablename__ = "document_fraud_flags"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("project_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    flag_type: Mapped[str] = mapped_column(
        String(60),
        nullable=False,
    )  # DUPLICATE_FILE, METHODOLOGY_SECTOR_MISMATCH, METHODOLOGY_INACTIVE,
       # ASSET_COUNT_DISCREPANCY, DATE_INCONSISTENCY, LOCATION_MISMATCH, SUSPICIOUS_METADATA

    severity: Mapped[str] = mapped_column(
        String(20),
        default="MEDIUM",
    )  # LOW, MEDIUM, HIGH, CRITICAL

    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_details: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )

    document: Mapped["ProjectDocument"] = relationship(
        "ProjectDocument", back_populates="fraud_flags"
    )
