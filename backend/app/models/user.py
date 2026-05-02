"""
=============================================================================
VeriField Nexus — User Model
=============================================================================
Represents a platform user (field agent or admin). Synced with Supabase
Auth — the ID matches the Supabase Auth user UUID.
=============================================================================
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    """
    User account model.
    
    Roles:
        - "field_agent": Field workers who submit activities via mobile app
        - "admin": Dashboard administrators who manage and review data
    
    The `id` field matches the Supabase Auth user UUID, ensuring
    seamless integration between our database and Supabase Auth.
    """
    __tablename__ = "users"

    # Primary key — matches Supabase Auth user UUID
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    # User identity
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=True, index=True
    )
    phone: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=True, index=True
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Role-based access control
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default="field_agent"
    )

    # Profile metadata
    avatar_url: Mapped[str] = mapped_column(String(500), nullable=True)
    organization: Mapped[str] = mapped_column(String(255), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )

    # --- Relationships ---
    activities = relationship("Activity", back_populates="user", lazy="selectin")
    properties = relationship("Property", back_populates="owner", lazy="selectin")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, name={self.full_name}, role={self.role})>"
