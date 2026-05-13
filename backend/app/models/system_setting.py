from sqlalchemy import Column, Integer, Float
from app.db.base import Base

class SystemSetting(Base):
    """
    Stores global platform settings (singleton row).
    """
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    gps_weight = Column(Float, default=30.0)
    image_weight = Column(Float, default=40.0)
    frequency_weight = Column(Float, default=30.0)
