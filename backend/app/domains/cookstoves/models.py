from sqlalchemy import Column, String, Float, DateTime, ForeignKey, JSON, Integer, Boolean, Text

from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.sql import func

import uuid



from app.db.base import Base



class HouseholdBeneficiary(Base):

    __tablename__ = "household_beneficiaries"



    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    household_code = Column(String(50), nullable=False, unique=True)

    head_of_household = Column(String(150), nullable=False)

    phone_number = Column(String(30), nullable=True)

    address = Column(String(255), nullable=False)

    community_name = Column(String(100), nullable=False)

    latitude = Column(Float, nullable=False)

    longitude = Column(Float, nullable=False)

    family_members_count = Column(Integer, nullable=False, default=5)

    baseline_fuel_type = Column(String(50), nullable=False, default="WOOD_FIRE") # WOOD_FIRE, CHARCOAL, KEROSENE

    baseline_fuel_kg_per_day = Column(Float, nullable=False, default=7.5)

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())



class CookstoveDevice(Base):

    __tablename__ = "cookstove_devices"



    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    household_id = Column(UUID(as_uuid=True), ForeignKey("household_beneficiaries.id", ondelete="CASCADE"), nullable=False)

    serial_number = Column(String(100), nullable=False, unique=True)

    stove_model = Column(String(100), nullable=False) # e.g. Baikuc TBIC-1, Institutional Biomass

    thermal_efficiency_pct = Column(Float, nullable=False, default=45.0)

    fuel_type_used = Column(String(50), nullable=False, default="PELLETS") # PELLETS, LPG, BIOMASS

    installation_date = Column(DateTime(timezone=True), nullable=False)

    installer_agent_id = Column(UUID(as_uuid=True), nullable=True)

    photo_evidence_url = Column(Text, nullable=True)

    photo_hash = Column(String(64), nullable=True)

    status = Column(String(30), nullable=False, default="DEPLOYED") # DEPLOYED, MONITORED, REPLACED, RETIRED

    created_at = Column(DateTime(timezone=True), server_default=func.now())



class UsageSurvey(Base):

    __tablename__ = "cookstove_usage_surveys"



    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    stove_id = Column(UUID(as_uuid=True), ForeignKey("cookstove_devices.id", ondelete="CASCADE"), nullable=False)

    surveyor_user_id = Column(UUID(as_uuid=True), nullable=False)

    survey_date = Column(DateTime(timezone=True), nullable=False)

    is_stove_in_use = Column(Boolean, nullable=False, default=True)

    reported_daily_usage_hours = Column(Float, nullable=False, default=3.5)

    fuel_consumed_kg_per_day = Column(Float, nullable=False, default=2.1)

    thermal_tampering_detected = Column(Boolean, default=False)

    is_primary_cooking_method = Column(Boolean, default=True)

    calculated_co2e_reduction_tonnes = Column(Float, nullable=False)

    has_fraud_flag = Column(Boolean, default=False)

    fraud_reason = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
