import uuid
from datetime import datetime

from sqlalchemy import Float, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EmissionFactorRegistry(Base):
    """
    Independent Emission Factor Registry.
    Methodologies reference these factors, they do not own them.
    """

    __tablename__ = "emission_factor_registry"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    code: Mapped[str] = mapped_column(
        String(100), unique=True, index=True
    )  # e.g. EF-NGA-GRID-2024
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    country: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    fuel_type: Mapped[str] = mapped_column(String(100), nullable=True)
    grid_type: Mapped[str] = mapped_column(String(100), nullable=True)

    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)  # tCO2e/MWh, tCO2e/TJ

    vintage_year: Mapped[int] = mapped_column(nullable=True)
    source: Mapped[str] = mapped_column(
        String, nullable=True
    )  # e.g. IPCC 2006, EPA, Defra
    version: Mapped[str] = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.utcnow(), server_default=text("now()")
    )
