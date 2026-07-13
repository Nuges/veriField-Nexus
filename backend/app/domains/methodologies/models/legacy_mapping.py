import uuid

from sqlalchemy import ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LegacyMethodologyMapping(Base):
    """
    Compatibility layer mapping legacy hardcoded methodology IDs
    (e.g., 'GS_TPDDTEC', 'VMR0050') to the new MethodologyVersion UUIDs.
    """

    __tablename__ = "methodology_legacy_mappings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    legacy_code: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    methodology_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("methodology_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )

    version = relationship("MethodologyVersion")
