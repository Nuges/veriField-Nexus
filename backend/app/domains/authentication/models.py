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

            return []  # Super Admin has access to all

        try:

            if self.organization_rel:

                lm = getattr(self.organization_rel, "licensed_methodologies", [])

                if lm:

                    return lm

        except Exception:

            pass

        if self.meta_data and isinstance(self.meta_data, dict):
            return self.meta_data.get("licensed_methodologies", [])
        return []

    @property
    def licensed_sectors(self) -> list:
        if self.role == "SUPER_ADMIN":
            return []
        try:
            if self.organization_rel:
                ls = getattr(self.organization_rel, "licensed_sectors", [])
                if ls:
                    res = []
                    for item in ls:
                        clean_item = str(item).upper().strip()
                        if "7F12BFE9" in clean_item or "HYBRID" in clean_item or "ENERGY" in clean_item:
                            res.append("HYBRID_ENERGY")
                        elif "867F684F" in clean_item or "EV" in clean_item or "MOBILITY" in clean_item:
                            res.append("EV_MOBILITY")
                        elif "E6DB7FBE" in clean_item or "4F12BFE9" in clean_item or "BIOCHAR" in clean_item:
                            res.append("BIOCHAR")
                        elif "DFF43D66" in clean_item or "6F12BFE9" in clean_item or "COOK" in clean_item:
                            res.append("COOKSTOVES")
                        else:
                            res.append(item)
                    return res
        except Exception:
            pass

        if self.meta_data and isinstance(self.meta_data, dict):
            return self.meta_data.get("licensed_sectors", [])
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





class Role(Base):

    """

    Metadata-driven role definition table.

    Scopes: PLATFORM, ORGANIZATION, PROJECT.

    """



    __tablename__ = "roles"



    id: Mapped[uuid.UUID] = mapped_column(

        UUID(as_uuid=True),

        primary_key=True,

        default=uuid.uuid4,

        server_default=text("gen_random_uuid()"),

    )

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(100), nullable=False)

    description: Mapped[str] = mapped_column(String(500), nullable=True)

    scope: Mapped[str] = mapped_column(String(30), nullable=False, default="ORGANIZATION")  # PLATFORM, ORGANIZATION, PROJECT

    is_system: Mapped[bool] = mapped_column(default=True, server_default=text("true"))

    created_at: Mapped[datetime] = mapped_column(

        DateTime(timezone=True),

        default=lambda: datetime.now(timezone.utc),

        server_default=text("now()"),

    )





class Permission(Base):

    """

    Atomic system permission definitions.

    """



    __tablename__ = "permissions"



    id: Mapped[uuid.UUID] = mapped_column(

        UUID(as_uuid=True),

        primary_key=True,

        default=uuid.uuid4,

        server_default=text("gen_random_uuid()"),

    )

    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(150), nullable=False)

    description: Mapped[str] = mapped_column(String(500), nullable=True)

    category: Mapped[str] = mapped_column(String(50), nullable=False, default="general")

    scope: Mapped[str] = mapped_column(String(30), nullable=False, default="ORGANIZATION")

    created_at: Mapped[datetime] = mapped_column(

        DateTime(timezone=True),

        default=lambda: datetime.now(timezone.utc),

        server_default=text("now()"),

    )





class RolePermission(Base):

    """

    Mapping between Roles and Permissions.

    """



    __tablename__ = "role_permissions"



    id: Mapped[uuid.UUID] = mapped_column(

        UUID(as_uuid=True),

        primary_key=True,

        default=uuid.uuid4,

        server_default=text("gen_random_uuid()"),

    )

    role_code: Mapped[str] = mapped_column(String(50), ForeignKey("roles.code", ondelete="CASCADE"), nullable=False, index=True)

    permission_code: Mapped[str] = mapped_column(String(100), ForeignKey("permissions.code", ondelete="CASCADE"), nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(

        DateTime(timezone=True),

        default=lambda: datetime.now(timezone.utc),

        server_default=text("now()"),

    )





class ProjectMembership(Base):

    """

    Authoritative assignment connecting users to projects with project-specific roles.

    Allows a user to hold distinct roles (e.g. FIELD_AGENT on Project A, AUDITOR on Project B).

    """



    __tablename__ = "project_memberships"



    id: Mapped[uuid.UUID] = mapped_column(

        UUID(as_uuid=True),

        primary_key=True,

        default=uuid.uuid4,

        server_default=text("gen_random_uuid()"),

    )

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)

    role_code: Mapped[str] = mapped_column(String(50), nullable=False, default="FIELD_AGENT")

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    assigned_at: Mapped[datetime] = mapped_column(

        DateTime(timezone=True),

        default=lambda: datetime.now(timezone.utc),

        server_default=text("now()"),

    )

    assigned_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)





class SecurityAuditLog(Base):

    """

    Immutable audit logging table for privileged security governance events.

    """



    __tablename__ = "security_audit_logs"



    id: Mapped[uuid.UUID] = mapped_column(

        UUID(as_uuid=True),

        primary_key=True,

        default=uuid.uuid4,

        server_default=text("gen_random_uuid()"),

    )

    actor_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)

    target_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)

    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    result: Mapped[str] = mapped_column(String(20), nullable=False, default="SUCCESS")  # SUCCESS, FORBIDDEN, FAILED

    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=True, default=dict)

    created_at: Mapped[datetime] = mapped_column(

        DateTime(timezone=True),

        default=lambda: datetime.now(timezone.utc),

        server_default=text("now()"),

        index=True,

    )
