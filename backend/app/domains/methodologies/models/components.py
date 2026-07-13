import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MonitoringTemplate(Base):
    """
    Reusable monitoring parameter templates.
    e.g., 'Household Fuel Consumption (kg)', 'Daily Distance (km)'
    """

    __tablename__ = "methodology_monitoring_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)

    data_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # numeric, boolean, string, datetime
    unit: Mapped[str] = mapped_column(String(20), nullable=True)

    validation_schema: Mapped[dict] = mapped_column(
        JSONB, default=dict
    )  # min, max, regex

    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.utcnow(), server_default=text("now()")
    )


class EvidenceTemplate(Base):
    """
    Reusable evidence requirements.
    e.g., 'GPS Coordinates', 'Photo with Timestamp', 'Fuel Receipt'
    """

    __tablename__ = "methodology_evidence_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)

    evidence_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # gps, photo, document, sensor_data
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True)


class CalculationRule(Base):
    """
    Reusable calculation formulas.
    """

    __tablename__ = "methodology_calculation_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    formula: Mapped[str] = mapped_column(String, nullable=False)

    unit: Mapped[str] = mapped_column(String(50), nullable=True)  # e.g., 'tCO2e', 'kg'
    inputs_schema: Mapped[dict] = mapped_column(JSONB, default=dict)
    outputs_schema: Mapped[dict] = mapped_column(JSONB, default=dict)
    sensitivity_analysis_rules: Mapped[dict] = mapped_column(
        JSONB, default=dict
    )  # Metadata for variable stress-testing


class ValidationRule(Base):
    """
    Reusable QA/QC and data validation rules.
    """

    __tablename__ = "methodology_validation_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    rule_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # anomaly, completeness, boundary
    expression: Mapped[str] = mapped_column(
        String, nullable=False
    )  # e.g. "fuel_consumption < 500"
    error_message: Mapped[str] = mapped_column(String, nullable=False)


class ReportingTemplate(Base):
    """
    Reusable reporting templates.
    """

    __tablename__ = "methodology_reporting_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    report_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # MRV, Verification, ESG
    template_schema: Mapped[dict] = mapped_column(JSONB, default=dict)


# Junction tables linking Version -> Components


class VersionMonitoringTemplate(Base):
    __tablename__ = "version_monitoring_templates"

    version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("methodology_versions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("methodology_monitoring_templates.id", ondelete="CASCADE"),
        primary_key=True,
    )
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)


class VersionEvidenceTemplate(Base):
    __tablename__ = "version_evidence_templates"

    version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("methodology_versions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("methodology_evidence_templates.id", ondelete="CASCADE"),
        primary_key=True,
    )
    frequency: Mapped[str] = mapped_column(
        String(50), nullable=True
    )  # per_activity, monthly, annual


class VersionCalculationRule(Base):
    __tablename__ = "version_calculation_rules"

    version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("methodology_versions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("methodology_calculation_rules.id", ondelete="CASCADE"),
        primary_key=True,
    )
    execution_order: Mapped[int] = mapped_column(default=0)


class VersionValidationRule(Base):
    __tablename__ = "version_validation_rules"

    version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("methodology_versions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("methodology_validation_rules.id", ondelete="CASCADE"),
        primary_key=True,
    )


class VersionReportingTemplate(Base):
    __tablename__ = "version_reporting_templates"

    version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("methodology_versions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("methodology_reporting_templates.id", ondelete="CASCADE"),
        primary_key=True,
    )
