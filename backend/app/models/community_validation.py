import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey

from app.db.base import Base


class CommunityValidation(Base):
    __tablename__ = "community_validations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id"), index=True, nullable=False
    )
    validator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False
    )
    response: Mapped[str] = mapped_column(String(10), nullable=False)  # 'yes', 'no', 'pending'
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        nullable=False,
    )

    upvotes: Mapped[int] = mapped_column(default=0, server_default=text("0"), nullable=False)

    property = relationship("Property", backref="community_validations")
    validator = relationship("User", backref="community_validations")


class CommunityComment(Base):
    __tablename__ = "community_comments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    validation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("community_validations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    comment: Mapped[str] = mapped_column(String(500), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        nullable=False,
    )

    validation = relationship("CommunityValidation", backref="comments")
    user = relationship("User", backref="community_comments")
