import uuid
from datetime import datetime, timezone
from sqlalchemy import Float, Boolean, DateTime, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey

from app.db.base import Base


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id"), index=True, nullable=False
    )
    device_id: Mapped[str] = mapped_column(nullable=False)
    temperature: Mapped[float] = mapped_column(Float, nullable=True)
    usage_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Advanced MRV (Gold Standard MECD / Verra VMR0050)
    fuel_weight_kg: Mapped[float] = mapped_column(Float, nullable=True)
    battery_voltage: Mapped[float] = mapped_column(Float, nullable=True) # Durability tracking
    
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        nullable=False,
    )

    property = relationship("Property", backref="sensor_readings")
