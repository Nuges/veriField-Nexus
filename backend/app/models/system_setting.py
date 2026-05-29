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
    gps_max_distance_km = Column(Float, default=5.0)
    max_submissions_per_hour = Column(Integer, default=10)
    image_hash_threshold = Column(Integer, default=12)
    suspicious_hours_start = Column(Integer, default=2)
    suspicious_hours_end = Column(Integer, default=5)
