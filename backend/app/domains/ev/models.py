from sqlalchemy import Column, String, Float, DateTime, ForeignKey, JSON, Integer, Boolean, Text

from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.sql import func

import uuid



from app.db.base import Base



class EVChargingStation(Base):

    __tablename__ = "ev_charging_stations"



    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    station_code = Column(String(50), nullable=False, unique=True)

    operator_name = Column(String(100), nullable=False)

    location_name = Column(String(200), nullable=False)

    latitude = Column(Float, nullable=False)

    longitude = Column(Float, nullable=False)

    charger_type = Column(String(50), nullable=False, default="DC_FAST") # AC_LEVEL_2, DC_FAST, ULTRA_FAST

    max_output_kw = Column(Float, nullable=False, default=50.0)

    grid_emission_factor_kg_kwh = Column(Float, nullable=False, default=0.45) # Grid kg CO2/kWh

    renewable_source_pct = Column(Float, nullable=False, default=0.0) # Solar/Wind attached %

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())



class EVChargingSession(Base):

    __tablename__ = "ev_charging_sessions"



    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    station_id = Column(UUID(as_uuid=True), ForeignKey("ev_charging_stations.id", ondelete="CASCADE"), nullable=False)

    vehicle_vin = Column(String(100), nullable=False)

    fleet_operator_id = Column(String(100), nullable=True)



    start_time = Column(DateTime(timezone=True), nullable=False)

    end_time = Column(DateTime(timezone=True), nullable=False)



    energy_consumed_kwh = Column(Float, nullable=False)

    distance_displaced_km = Column(Float, nullable=False)

    baseline_vehicle_type = Column(String(50), nullable=False, default="ICE_DIESEL") # ICE_GASOLINE, ICE_DIESEL, ICE_BUS



    battery_state_of_health_pct = Column(Float, nullable=False, default=98.0)

    baseline_emission_factor_g_km = Column(Float, nullable=False, default=220.0) # g CO2/km for ICE



    net_co2e_avoided_kg = Column(Float, nullable=False)

    has_anomaly = Column(Boolean, default=False)

    anomaly_reason = Column(Text, nullable=True)



    metadata_json = Column(JSON, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
