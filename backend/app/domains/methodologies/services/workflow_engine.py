import uuid
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.domains.activities.models import Activity
from app.domains.methodologies.models.workflow import (Workflow, WorkflowStage,
                                                       WorkflowTask)


class WorkflowEngine:
    """
    Universal Workflow Engine.
    Evaluates State machines, ABAC, RBAC, and approval gates for activities based on methodology workflow definitions.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def initialize_workflow(self, activity_id: uuid.UUID, version_id: uuid.UUID):
        """
        Triggers a new workflow instance for an activity based on the methodology version.
        """
        workflow_res = await self.db.execute(
            select(Workflow).filter_by(
                version_id=version_id, trigger_event="activity_created"
            )
        )
        workflow = workflow_res.scalar_one_or_none()
        if not workflow:
            return None

        # Here we would initialize the state machine state for the specific activity.
        # For CIOS, we can store current_stage_id in Activity or a separate WorkflowInstance table.
        # Since Phase 1 decoupled everything, we assume the Activity status tracks the high-level state,
        # but detailed workflow state can be logged in TrustLog or a new table.
        return workflow

    async def evaluate_abac_rules(
        self,
        stage: WorkflowStage,
        user_context: Dict[str, Any],
        activity_data: Dict[str, Any],
    ) -> bool:
        """
        Evaluates Attribute-Based Access Control logic for a specific stage.
        """
        if not stage.abac_rules:
            return True

        # Example rule format: {"require_region": "same_as_project", "require_certification": "ISO14064"}
        for key, expected_val in stage.abac_rules.items():
            if key == "require_certification":
                if expected_val not in user_context.get("certifications", []):
                    return False
        return True

    async def process_approval(
        self, task_id: uuid.UUID, activity_id: uuid.UUID, user_context: Dict[str, Any]
    ) -> bool:
        """
        Processes an approval gate.
        """
        task_res = await self.db.execute(select(WorkflowTask).filter_by(id=task_id))
        task = task_res.scalar_one_or_none()
        if not task or task.task_type != "approval":
            raise ValueError("Invalid approval task")

        stage_res = await self.db.execute(
            select(WorkflowStage).filter_by(id=task.stage_id)
        )
        stage = stage_res.scalar_one_or_none()

        # 1. RBAC Check
        if stage.required_role and user_context.get("role") != stage.required_role:
            raise PermissionError("User does not have the required role for this stage")

        # 2. ABAC Check
        activity_res = await self.db.execute(select(Activity).filter_by(id=activity_id))
        activity = activity_res.scalar_one_or_none()
        if not activity:
            raise ValueError("Activity not found")

        has_abac_access = await self.evaluate_abac_rules(
            stage, user_context, activity.activity_data
        )
        if not has_abac_access:
            raise PermissionError("User does not meet ABAC requirements for this stage")

        # 3. Process Approval
        # Transition to next stage or mark task as complete
        return True
