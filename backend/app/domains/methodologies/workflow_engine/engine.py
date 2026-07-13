import uuid
from enum import Enum
from typing import Dict, List, Optional


class WorkflowStatus(Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"


class WorkflowEngine:
    """
    Universal Workflow Engine that transitions entities through metadata-defined stages.
    """

    def __init__(self, db_session=None):
        self.db = db_session

    async def get_next_stage(
        self, current_stage_sequence: int, workflow_stages: List[Dict]
    ) -> Optional[Dict]:
        """
        Determines the next stage in the sequence.
        """
        stages = sorted(workflow_stages, key=lambda s: s["sequence_order"])
        for stage in stages:
            if stage["sequence_order"] > current_stage_sequence:
                return stage
        return None

    async def can_transition(
        self, current_state: Dict, next_stage: Dict, provided_evidence: List[Dict]
    ) -> bool:
        """
        Evaluates if the entity can move to the next stage based on required tasks/evidence.
        """
        required_tasks = next_stage.get("tasks", [])

        # Check if all required evidence/data for the next stage's tasks is provided
        for task in required_tasks:
            if task["task_type"] == "evidence_upload":
                # Ensure evidence matching task criteria exists
                has_evidence = any(
                    e for e in provided_evidence if e.get("type") == task["name"]
                )
                if not has_evidence:
                    return False

            # Other task type checks (approvals, calculations, etc.)

        return True

    async def execute_transition(
        self,
        entity_id: uuid.UUID,
        workflow_id: uuid.UUID,
        current_stage_sequence: int,
        provided_evidence: List[Dict],
    ) -> Dict:
        """
        Attempts to transition an entity.
        Returns the new state and an audit log.
        """
        # In a real implementation, we would fetch the workflow definition from the DB
        # For now, we stub the metadata lookups
        workflow_metadata = {
            "stages": [
                {"sequence_order": 1, "name": "Data Collection", "tasks": []},
                {
                    "sequence_order": 2,
                    "name": "Verification",
                    "tasks": [{"task_type": "evidence_upload", "name": "GPS Log"}],
                },
            ]
        }

        next_stage = await self.get_next_stage(
            current_stage_sequence, workflow_metadata["stages"]
        )

        if not next_stage:
            return {
                "status": WorkflowStatus.COMPLETED.value,
                "stage": current_stage_sequence,
                "message": "Workflow already complete",
            }

        if await self.can_transition({}, next_stage, provided_evidence):
            return {
                "status": WorkflowStatus.IN_PROGRESS.value,
                "stage": next_stage["sequence_order"],
                "message": f"Transitioned to {next_stage['name']}",
            }
        else:
            return {
                "status": WorkflowStatus.PENDING.value,
                "stage": current_stage_sequence,
                "message": "Missing required criteria for transition",
            }
