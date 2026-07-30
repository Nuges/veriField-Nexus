from sqlalchemy import Column, String, Float, DateTime, ForeignKey, JSON, Integer, Boolean, Text

from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.sql import func

import uuid



from app.db.base import Base



class SolarArrayAsset(Base):

    __tablename__ = "solar_array_assets"



    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    site_code = Column(String(50), nullable=False, unique=True)

    site_name = Column(String(100), nullable=False)

    latitude = Column(Float, nullable=False)

    longitude = Column(Float, nullable=False)



    capacity_kwp = Column(Float, nullable=False, default=100.0)

    battery_capacity_kwh = Column(Float, nullable=False, default=200.0)

    diesel_generator_kw = Column(Float, nullable=False, default=150.0)



    inverter_brand = Column(String(50), default="SMA")

    meter_serial_number = Column(String(100), nullable=True)



    baseline_diesel_ef_kg_kwh = Column(Float, nullable=False, default=0.744) # kg CO2e / kWh diesel generator

    annual_degradation_pct = Column(Float, nullable=False, default=0.5) # PV degradation



    status = Column(String(30), default="OPERATIONAL")

    created_at = Column(DateTime(timezone=True), server_default=func.now())



class EnergyTelemetryLog(Base):

    __tablename__ = "energy_telemetry_logs"



    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    solar_asset_id = Column(UUID(as_uuid=True), ForeignKey("solar_array_assets.id", ondelete="CASCADE"), nullable=False)

    timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now())



    solar_generation_kwh = Column(Float, nullable=False, default=0.0)

    battery_discharge_kwh = Column(Float, nullable=False, default=0.0)

    diesel_generation_kwh = Column(Float, nullable=False, default=0.0)

    diesel_fuel_consumed_liters = Column(Float, nullable=False, default=0.0)



    grid_displaced_kwh = Column(Float, nullable=False, default=0.0)

    net_co2e_avoided_tonnes = Column(Float, nullable=False, default=0.0)



    has_anomaly = Column(Boolean, default=False)

    anomaly_reason = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
