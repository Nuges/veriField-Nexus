import uuid
from datetime import datetime, timezone

from sqlalchemy import (JSON, Boolean, Column, DateTime, ForeignKey, Integer,
                        String)

from app.db.base import Base


class DataAssetCatalogue(Base):
    """
    Enterprise Data Governance Catalogue.
    Tracks all logical data entities, their lineage, retention policies, and PII constraints.
    """

    __tablename__ = "data_asset_catalogue"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_name = Column(String, nullable=False, unique=True, index=True)
    domain_owner = Column(String, nullable=False)
    description = Column(String, nullable=True)

    # GDPR & PII
    contains_pii = Column(Boolean, default=False)
    pii_fields = Column(
        JSON, default=list
    )  # e.g. ["email", "phone", "gps_coordinates"]
    gdpr_consent_required = Column(Boolean, default=False)

    # Retention
    retention_period_days = Column(
        Integer, nullable=True
    )  # e.g. 2555 (7 years for carbon registries)
    archive_after_days = Column(Integer, nullable=True)

    # Lineage
    upstream_sources = Column(JSON, default=list)
    downstream_consumers = Column(JSON, default=list)

    # Schema Evolution
    current_schema_version = Column(Integer, default=1)
    schema_definition = Column(JSON, default=dict)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class SchemaEvolutionLog(Base):
    """
    Tracks schema migrations at a logical metadata level, independent of DB migrations.
    """

    __tablename__ = "schema_evolution_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_id = Column(String, ForeignKey("data_asset_catalogue.id"), nullable=False)
    version = Column(Integer, nullable=False)
    migration_payload = Column(JSON, nullable=False)
    applied_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
