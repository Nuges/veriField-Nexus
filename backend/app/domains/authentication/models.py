import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    """
    User account model.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=True, index=True
    )
    phone: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=True, index=True
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)

    role: Mapped[str] = mapped_column(String(20), nullable=False, default="field_agent")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    is_active: Mapped[bool] = mapped_column(default=True, server_default=text("true"))

    country: Mapped[str] = mapped_column(String(100), nullable=True)

    avatar_url: Mapped[str] = mapped_column(String(500), nullable=True)
    organization: Mapped[str] = mapped_column(String(255), nullable=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True
    )

    password_hash: Mapped[str] = mapped_column(String(255), nullable=True)
    requires_password_change: Mapped[bool] = mapped_column(
        default=False, server_default=text("false")
    )

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

    # Enterprise Architectural Requirements (G-09, G-21, G-27)
    version: Mapped[int] = mapped_column(default=1, server_default=text("1"))
    is_deleted: Mapped[bool] = mapped_column(
        default=False, server_default=text("false")
    )
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    meta_data: Mapped[dict] = mapped_column(
        JSONB, nullable=True, default=dict, server_default=text("'{}'::jsonb")
    )

    __mapper_args__ = {"version_id_col": version}

    # Relationships
    activities = relationship("Activity", back_populates="user", lazy="select")
    properties = relationship("Property", back_populates="owner", lazy="select")
    organization_rel = relationship("Organization", lazy="selectin")

    @property
    def licensed_methodologies(self) -> list:
        if self.role == "SUPER_ADMIN":
            return []  # Admin has access to all
        if self.organization_rel:
            return self.organization_rel.licensed_methodologies
        return []

    def has_permission(self, permission: str) -> bool:
        """Synchronous check using the local map for compatibility."""
        from app.domains.authentication.permissions import ROLE_PERMISSIONS_MAP

        role = "ORG_ADMIN" if self.role == "admin" else self.role
        if role == "SUPER_ADMIN":
            return True
        return permission in ROLE_PERMISSIONS_MAP.get(role, set())

    @property
    def is_field_agent(self) -> bool:
        return self.has_permission("CreateActivity") and not self.has_permission(
            "CreateProject"
        )

    @property
    def is_super_admin(self) -> bool:
        return self.role == "SUPER_ADMIN"

    @property
    def is_admin(self) -> bool:
        return self.has_permission("CreateProject")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, name={self.full_name}, role={self.role})>"
