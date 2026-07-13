import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Organization(Base):
    """
    SaaS tenant organization. Foundational multi-tenant unit.
    """

    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    org_type: Mapped[str] = mapped_column(
        "org_type", String(50), nullable=False, default="DEVELOPER"
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    metadata_context: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )

    # Legacy fields
    plan: Mapped[str] = mapped_column(String(30), nullable=False, default="FREE")
    max_installations: Mapped[int] = mapped_column(nullable=False, default=100)
    max_agents: Mapped[int] = mapped_column(nullable=False, default=5)
    api_calls_count: Mapped[int] = mapped_column(nullable=False, default=0)
    licensed_methodologies: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    is_deleted: Mapped[bool] = mapped_column(nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<Organization(id={self.id}, name={self.name}, status={self.status}, type={self.type})>"
