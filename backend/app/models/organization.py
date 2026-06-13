"""
=============================================================================
VeriField Nexus — Organization Model
=============================================================================
Represents a tenant organization (e.g., carbon developer, energy company)
that owns clean energy projects and registers MRV ledgers.
=============================================================================
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Organization(Base):
    """
    SaaS tenant organization.
    """
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    plan: Mapped[str] = mapped_column(String(30), nullable=False, default="FREE")
    max_installations: Mapped[int] = mapped_column(nullable=False, default=100)
    max_agents: Mapped[int] = mapped_column(nullable=False, default=5)
    api_calls_count: Mapped[int] = mapped_column(nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )

    def __repr__(self) -> str:
        return f"<Organization(id={self.id}, name={self.name}, status={self.status}, plan={self.plan})>"
