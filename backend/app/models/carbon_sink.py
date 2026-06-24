"""
=============================================================================
VeriField Nexus — Carbon C-Sink Module ORM Models
=============================================================================
Defines database models compliant with Carbon Standards International (CSI)
Global C-Sink specifications (Artisan and Biochar). Includes profiles,
traceability nodes, QR registry records, and sync logs.
=============================================================================
"""

import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Float, DateTime, ForeignKey, Text, Boolean, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ArtisanProfile(Base):
    """
    Profile for an Artisan Biochar Producer or C-Sink Cook.
    """
    __tablename__ = "artisan_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    kiln_type: Mapped[str] = mapped_column(String(100), nullable=False)
    proficiency_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    volume_measuring_device_m3: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Traceability fields required by CSI
    client_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, unique=True)
    gps: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True) # {"latitude": float, "longitude": float}
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )
    evidence_links: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True) # links to credentials/certificates

    # Relationships
    kilns = relationship("KilnProfile", back_populates="artisan", cascade="all, delete-orphan")


class KilnProfile(Base):
    """
    Profile for a specific pyrolysis kiln equipment.
    """
    __tablename__ = "kiln_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    artisan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("artisan_profiles.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    serial_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    surface_area_m2: Mapped[float] = mapped_column(Float, nullable=False)
    depth_m: Mapped[float] = mapped_column(Float, nullable=False)
    capacity_m3: Mapped[float] = mapped_column(Float, nullable=False)
    methane_emission_factor: Mapped[float] = mapped_column(Float, default=0.0) # kg CH4/t biochar
    
    # Traceability fields
    client_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    gps: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )
    evidence_links: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True) # photo of kiln

    # Relationships
    artisan = relationship("ArtisanProfile", back_populates="kilns")
    batches = relationship("BiocharBatch", back_populates="kiln", cascade="all, delete-orphan")


class BiomassProfile(Base):
    """
    Profile detailing the biomass feedstock parameters.
    """
    __tablename__ = "biomass_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    mixing_ratio: Mapped[str] = mapped_column(String(100), nullable=False) # e.g. "100% crop_residue"
    carbon_content_pct: Mapped[float] = mapped_column(Float, nullable=False) # e.g. 71.3
    bulk_density_g_cm3: Mapped[float] = mapped_column(Float, nullable=False)
    methane_compensation_scheme: Mapped[str] = mapped_column(String(100), nullable=False) # avoidance/compensation
    
    # Traceability fields
    client_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    gps: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )
    evidence_links: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True) # link to lab PDF report

    # Relationships
    batches = relationship("BiocharBatch", back_populates="biomass")


class BiocharBatch(Base):
    """
    Represents a specific biochar production run (pyrolysis batch).
    """
    __tablename__ = "biochar_batches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    kiln_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("kiln_profiles.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    biomass_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("biomass_profiles.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    batch_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    quantity_kg: Mapped[float] = mapped_column(Float, nullable=False)
    produced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    lab_report_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Traceability fields
    client_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    gps: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )
    evidence_links: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Relationships
    kiln = relationship("KilnProfile", back_populates="batches")
    biomass = relationship("BiomassProfile", back_populates="batches")
    qr_records = relationship("QrRecord", back_populates="batch", cascade="all, delete-orphan")


class QrRecord(Base):
    """
    Tracks EBC/WBC QR Code values mapped to production batches for full lineage tracing.
    """
    __tablename__ = "qr_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    qr_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("biochar_batches.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    verification_status: Mapped[str] = mapped_column(String(20), default="verified") # verified, pending, rejected
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )

    # Relationships
    batch = relationship("BiocharBatch", back_populates="qr_records")


class CSinkUnit(Base):
    """
    Represents a bundled C-Sink Unit (aggregate volume >= 1 tCO2e) exported to registries.
    """
    __tablename__ = "c_sink_units"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    total_co2e_t: Mapped[float] = mapped_column(Float, nullable=False)
    carbon_content_pct: Mapped[float] = mapped_column(Float, nullable=False)
    biomass_type: Mapped[str] = mapped_column(String(255), nullable=False)
    pyrolysis_technology: Mapped[str] = mapped_column(String(255), nullable=False)
    matrix_category: Mapped[str] = mapped_column(String(255), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    
    # Traceability fields
    client_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    gps: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )
    evidence_links: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True) # monitoring reports / validation documents

    # Relationships
    transactions = relationship("CSinkTransaction", back_populates="c_sink_unit", cascade="all, delete-orphan")


class CSinkTransaction(Base):
    """
    Registry audit trail logging for STOCK/SINK API transactions submitted to CSI.
    """
    __tablename__ = "c_sink_transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    c_sink_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("c_sink_units.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False) # STOCK or SINK
    registry_tx_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="PENDING") # PENDING, SUCCESS, FAILED
    response_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )

    # Relationships
    c_sink_unit = relationship("CSinkUnit", back_populates="transactions")
