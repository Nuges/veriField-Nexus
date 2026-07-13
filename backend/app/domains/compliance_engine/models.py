import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ComplianceRun(Base):
    __tablename__ = "compliance_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    eligibility_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    sampling_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    conformance_issues: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list
    )
    risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    last_evaluated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )

    def __repr__(self) -> str:
        return f"<ComplianceRun(project_id={self.project_id}, status={self.eligibility_status}, risk={self.risk_score})>"
