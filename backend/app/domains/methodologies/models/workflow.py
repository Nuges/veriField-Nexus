import uuid

from sqlalchemy import ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Workflow(Base):
    """
    A methodology workflow (e.g., 'Monitoring & Verification Workflow').
    """

    __tablename__ = "methodology_workflows"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("methodology_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)
    trigger_event: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g. "activity_created"

    stages = relationship(
        "WorkflowStage",
        back_populates="workflow",
        order_by="WorkflowStage.sequence_order",
    )


class WorkflowStage(Base):
    """
    A stage in the workflow (e.g., 'Data Collection', 'Internal QA', 'VVB Audit').
    """

    __tablename__ = "methodology_workflow_stages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("methodology_workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    required_role: Mapped[str] = mapped_column(
        String(100), nullable=True
    )  # e.g., 'field_agent', 'verifier'

    # Advanced Workflow Control
    abac_rules: Mapped[dict] = mapped_column(
        JSONB, default=dict
    )  # Attribute-Based Access Control logic
    escalation_timer_hours: Mapped[int] = mapped_column(
        Integer, nullable=True
    )  # Time limit before escalation
    escalation_webhook: Mapped[str] = mapped_column(
        String, nullable=True
    )  # Where to send escalation alerts

    workflow = relationship("Workflow", back_populates="stages")
    tasks = relationship(
        "WorkflowTask", back_populates="stage", order_by="WorkflowTask.sequence_order"
    )


class WorkflowTask(Base):
    """
    A specific task within a stage (e.g., 'Upload GPS Coordinates', 'Approve Calculation').
    """

    __tablename__ = "methodology_workflow_tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    stage_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("methodology_workflow_stages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    task_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'data_entry', 'evidence_upload', 'approval', 'calculation'
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)

    # Metadata for UI rendering and rules
    schema_definition: Mapped[dict] = mapped_column(JSONB, default=dict)

    stage = relationship("WorkflowStage", back_populates="tasks")
