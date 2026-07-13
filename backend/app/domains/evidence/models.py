import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Evidence(Base):
    """
    Evidence Model for MRV (Monitoring, Reporting & Verification)
    Stores proof points (e.g., IoT readings, field photos) with cryptographic hashes.
    """

    __tablename__ = "evidence_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    activity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    file_uri: Mapped[str] = mapped_column(String(500), nullable=False)
    file_hash: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # SHA-256 hash for immutability

    status: Mapped[str] = mapped_column(
        String(20), default="PENDING"
    )  # PENDING, VERIFIED, INVALID
    evidence_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # e.g., "PHOTO", "METER_READING", "DOCUMENT"
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)

    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    verified_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
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

    def __repr__(self) -> str:
        return (
            f"<Evidence(id={self.id}, type={self.evidence_type}, status={self.status})>"
        )
