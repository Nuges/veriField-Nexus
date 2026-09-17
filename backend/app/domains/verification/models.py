import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class VerificationTask(Base):
    """
    Verification Task assigned to an internal or external verifier
    to review a batch of evidence or a project period.
    """

    __tablename__ = "verification_tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    verifier_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    status: Mapped[str] = mapped_column(
        String(50), default="ASSIGNED"
    )  # ASSIGNED, IN_PROGRESS, COMPLETED, REJECTED
    findings: Mapped[dict] = mapped_column(JSONB, default=dict)

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


class AuditReport(Base):
    """
    Formal Audit Report submitted by a VVB (Validation and Verification Body)
    """

    __tablename__ = "audit_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    vvb_org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    report_uri: Mapped[str] = mapped_column(String(500), nullable=False)
    report_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    is_positive_opinion: Mapped[bool] = mapped_column(Boolean, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )


class VerificationPackage(Base):
    """
    Immutable, audit-ready verification package compiling the complete MRV graph
    for a project and monitoring period into a cryptographically sealed dossier.
    """
    __tablename__ = "verification_packages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    monitoring_period_start: Mapped[date] = mapped_column(Date, nullable=False)
    monitoring_period_end: Mapped[date] = mapped_column(Date, nullable=False)

    package_name: Mapped[str] = mapped_column(String(255), nullable=False)
    package_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    parent_package_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("verification_packages.id", ondelete="SET NULL"),
        nullable=True,
    )

    package_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="DRAFT", index=True
    )  # DRAFT, COMPILING, READY_FOR_AUDIT, SUBMITTED, UNDER_REVIEW, FINDINGS_ISSUED, RESUBMITTED, VERIFIED, REJECTED

    registry_target: Mapped[str] = mapped_column(
        String(50), nullable=False, default="PURO_STANDARD"
    )  # PURO_STANDARD, VERRA, GENERIC
    audit_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="OUTPUT_AUDIT"
    )  # PRODUCTION_FACILITY_AUDIT, OUTPUT_AUDIT, COMBINED_AUDIT, VALIDATION

    manifest_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    ledger_signature_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("signatures.id", ondelete="SET NULL"),
        nullable=True,
    )
    sealed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sealed_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    diff_summary_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    completeness_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    blocker_reasons: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

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
    project = relationship("Project")
    organization = relationship("Organization")
    parent_package = relationship("VerificationPackage", remote_side=[id], backref="child_packages")
    ledger_signature = relationship("Signature")
    findings = relationship("VerificationPackageFinding", back_populates="package", cascade="all, delete-orphan", foreign_keys="VerificationPackageFinding.package_id")
    evidence_items = relationship("VerificationPackageEvidence", back_populates="package", cascade="all, delete-orphan")
    access_grants = relationship("VerificationAccessGrant", back_populates="package", cascade="all, delete-orphan")


class VerificationPackageFinding(Base):
    """
    Auditor / Verifier Finding logged against a Verification Package.
    Supports CAR, CL, FAR, NCR findings with full audit response lifecycle.
    """
    __tablename__ = "verification_package_findings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    package_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("verification_packages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    finding_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    finding_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="CAR"
    )  # CAR, CL, FAR, NCR
    severity: Mapped[str] = mapped_column(
        String(50), nullable=False, default="MAJOR"
    )  # CRITICAL, MAJOR, MINOR, OBSERVATION

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    target_domain: Mapped[str] = mapped_column(String(100), nullable=False)
    target_record_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    target_field: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="OPEN", index=True
    )  # OPEN, UNDER_DEVELOPER_REVIEW, RESPONSE_SUBMITTED, RESOLVED, CLOSED, REJECTED

    auditor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    auditor_organization: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    project_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolution_package_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("verification_packages.id", ondelete="SET NULL"),
        nullable=True,
    )

    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
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
    package = relationship("VerificationPackage", foreign_keys=[package_id], back_populates="findings")
    resolution_package = relationship("VerificationPackage", foreign_keys=[resolution_package_id])
    auditor = relationship("User", foreign_keys=[auditor_user_id])


class VerificationPackageEvidence(Base):
    """
    Central Evidence Index item linked to a Verification Package.
    Stores immutable cryptographic SHA-256 digest and file integrity status.
    """
    __tablename__ = "verification_package_evidence"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    package_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("verification_packages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    evidence_category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    reference_domain: Mapped[str] = mapped_column(String(100), nullable=False)
    reference_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_uri: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    verified_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    integrity_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="VERIFIED"
    )  # VERIFIED, INTEGRITY_MISMATCH, UNVERIFIED, MISSING

    uploaded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )

    # Relationships
    package = relationship("VerificationPackage", back_populates="evidence_items")


class VerificationAccessGrant(Base):
    """
    Scoped external auditor / verifier access grant for a specific Verification Package.
    Enforces time-bound, role-restricted, audited read-only access.
    """
    __tablename__ = "verification_access_grants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    package_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("verification_packages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    auditor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    auditor_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    auditor_organization: Mapped[str] = mapped_column(String(255), nullable=False)
    grantee_role: Mapped[str] = mapped_column(String(50), nullable=False, default="AUDITOR")

    access_key_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_accessed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )

    # Relationships
    package = relationship("VerificationPackage", back_populates="access_grants")
    auditor_user = relationship("User")
