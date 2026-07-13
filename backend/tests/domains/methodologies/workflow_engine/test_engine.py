import uuid

import pytest

from app.domains.methodologies.workflow_engine.engine import (WorkflowEngine,
                                                              WorkflowStatus)


@pytest.mark.asyncio
async def test_workflow_transition_success():
    engine = WorkflowEngine()
    entity_id = uuid.uuid4()
    workflow_id = uuid.uuid4()

    # We are currently in stage 1.
    # Provided evidence includes "GPS Log", which is required for stage 2.
    provided_evidence = [{"type": "GPS Log", "url": "http://example.com/gps.csv"}]

    result = await engine.execute_transition(
        entity_id,
        workflow_id,
        current_stage_sequence=1,
        provided_evidence=provided_evidence,
    )

    assert result["status"] == WorkflowStatus.IN_PROGRESS.value
    assert result["stage"] == 2
    assert "Transitioned to Verification" in result["message"]


@pytest.mark.asyncio
async def test_workflow_transition_missing_evidence():
    engine = WorkflowEngine()
    entity_id = uuid.uuid4()
    workflow_id = uuid.uuid4()

    # Missing required evidence
    provided_evidence = [{"type": "Photo", "url": "http://example.com/photo.jpg"}]

    result = await engine.execute_transition(
        entity_id,
        workflow_id,
        current_stage_sequence=1,
        provided_evidence=provided_evidence,
    )

    assert result["status"] == WorkflowStatus.PENDING.value
    assert result["stage"] == 1
    assert "Missing required criteria" in result["message"]


@pytest.mark.asyncio
async def test_workflow_completed():
    engine = WorkflowEngine()
    entity_id = uuid.uuid4()
    workflow_id = uuid.uuid4()

    # Currently at stage 2, there is no stage 3 in the stub metadata
    result = await engine.execute_transition(
        entity_id, workflow_id, current_stage_sequence=2, provided_evidence=[]
    )

    assert result["status"] == WorkflowStatus.COMPLETED.value
    assert result["stage"] == 2
