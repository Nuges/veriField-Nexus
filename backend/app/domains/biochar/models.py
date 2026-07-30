from sqlalchemy import Column, String, Float, DateTime, ForeignKey, JSON, Integer, Boolean, Text

from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.sql import func

import uuid



from app.db.base import Base



class BiocharBatch(Base):

    __tablename__ = "biochar_batches"



    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    batch_number = Column(String(50), nullable=False, unique=True)

    facility_name = Column(String(100), nullable=False)

    kiln_id = Column(String(50), nullable=False)



    # Feedstock tracking

    feedstock_type = Column(String(100), nullable=False) # e.g. agricultural_waste, rice_husk, wood_chips

    feedstock_weight_tonnes = Column(Float, nullable=False)

    moisture_content_pct = Column(Float, nullable=False)

    origin_location = Column(String(255), nullable=True)



    # Kiln Operations

    pyrolysis_temp_celsius = Column(Float, nullable=False)

    residence_time_minutes = Column(Float, nullable=False)

    kiln_operator_id = Column(UUID(as_uuid=True), nullable=True)



    # Yield & Production

    biochar_yield_tonnes = Column(Float, nullable=False)

    fixed_carbon_pct = Column(Float, nullable=False, default=75.0)

    ash_content_pct = Column(Float, nullable=False, default=5.0)

    molar_h_c_ratio = Column(Float, nullable=False, default=0.4) # < 0.7 for permanence



    # Permanence & Carbon Removal

    carbon_permanence_factor = Column(Float, nullable=False, default=0.85)

    net_co2e_removed_tonnes = Column(Float, nullable=False)



    # Quality & Lab Report

    lab_report_number = Column(String(100), nullable=True)

    lab_sample_id = Column(String(100), nullable=True)

    quality_grade = Column(String(20), nullable=False, default="GRADE_A") # GRADE_A, GRADE_B, REJECTED

    lab_document_url = Column(Text, nullable=True)



    # Status & Anomaly Flags

    status = Column(String(30), nullable=False, default="PRODUCED") # PRODUCED, LAB_TESTED, VERIFIED, CERTIFIED

    has_anomaly = Column(Boolean, default=False)

    anomaly_reason = Column(Text, nullable=True)



    metadata_json = Column(JSON, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())



class BiocharInventory(Base):

    __tablename__ = "biochar_inventories"



    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    batch_id = Column(UUID(as_uuid=True), ForeignKey("biochar_batches.id", ondelete="CASCADE"), nullable=False)

    storage_location = Column(String(200), nullable=False)

    current_stock_tonnes = Column(Float, nullable=False)

    application_soil_type = Column(String(100), nullable=True) # agricultural, agroforestry, remediation

    application_date = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
