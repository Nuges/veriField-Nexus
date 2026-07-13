import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MethodologyRegistry(Base):
    """
    Registry entity (e.g., Verra, Gold Standard, CDM).
    """

    __tablename__ = "methodology_registries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)
    website: Mapped[str] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    methodologies = relationship("Methodology", back_populates="registry")


class MethodologyFamily(Base):
    """
    Family entity (e.g., Cookstoves, Biochar, EV Mobility).
    """

    __tablename__ = "methodology_families"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)

    methodologies = relationship("Methodology", back_populates="family")


class Methodology(Base):
    """
    Methodology entity (e.g., VM0050, TPDDTEC).
    """

    __tablename__ = "methodologies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)

    registry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("methodology_registries.id", ondelete="RESTRICT"),
        nullable=False,
    )
    family_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("methodology_families.id", ondelete="RESTRICT"),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    ui_config: Mapped[dict] = mapped_column(JSONB, default=dict)
    form_schema: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.utcnow(), server_default=text("now()")
    )

    # Relationships
    registry = relationship("MethodologyRegistry", back_populates="methodologies")
    family = relationship("MethodologyFamily", back_populates="methodologies")
    versions = relationship(
        "MethodologyVersion",
        back_populates="methodology",
        order_by="desc(MethodologyVersion.release_date)",
    )
    dependencies = relationship("MethodologyDependency", back_populates="methodology")


class MethodologyVersion(Base):
    """
    Version entity (e.g., v1.0, v2.0) for a Methodology.
    """

    __tablename__ = "methodology_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    methodology_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("methodologies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g. 1.0.0
    status: Mapped[str] = mapped_column(
        String(50), default="active"
    )  # draft, active, deprecated, retired

    release_date: Mapped[date] = mapped_column(Date, nullable=False)
    retirement_date: Mapped[date] = mapped_column(Date, nullable=True)
    migration_notes: Mapped[str] = mapped_column(String, nullable=True)

    methodology = relationship("Methodology", back_populates="versions")

    # Links to reusable components via junction tables or direct FKs if dedicated
    # (Since we are using reusable components, we will use junction tables in components.py)


class MethodologyDependency(Base):
    """
    Tracks what a Methodology depends on (e.g. specific evidence rules, QA rules).
    """

    __tablename__ = "methodology_dependencies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    methodology_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("methodologies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dependency_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'parameter', 'evidence', 'emission_factor', 'qa_rule'
    dependency_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    methodology = relationship("Methodology", back_populates="dependencies")
