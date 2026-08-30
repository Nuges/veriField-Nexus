import uuid
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.digital_twins.models.twin import DigitalTwin, DigitalTwinState


@pytest.mark.asyncio
async def test_digital_twin_lifecycle(async_client: AsyncClient, admin_token_headers: dict, db_session: AsyncSession):
    twin_id = uuid.uuid4()
    asset_id = uuid.uuid4()

    twin = DigitalTwin(
        id=twin_id,
        asset_id=asset_id,
        twin_status="online",
        state_vector={"temperature": 180.0, "power_watts": 45.0, "runtime_hours": 12.5},
    )
    state1 = DigitalTwinState(
        id=uuid.uuid4(),
        digital_twin_id=twin_id,
        state_data={"temperature": 180.0, "power_watts": 45.0, "runtime_hours": 12.5},
        timestamp=datetime.now(timezone.utc),
    )
    db_session.add(twin)
    db_session.add(state1)
    await db_session.commit()

    # 1. Run Forward Simulation
    resp_sim = await async_client.post(
        f"/api/v1/digital-twins/{twin_id}/simulate?forward_steps=5&step_size_minutes=30",
        headers=admin_token_headers,
    )
    assert resp_sim.status_code == 200, f"Simulation failed: {resp_sim.text}"
    sim_data = resp_sim.json()
    assert "simulation" in sim_data

    # 2. Replay Historical Playback
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    resp_pb = await async_client.get(
        f"/api/v1/digital-twins/{twin_id}/playback?start_time=2026-01-01T00:00:00Z&end_time={now_iso}",
        headers=admin_token_headers,
    )
    assert resp_pb.status_code == 200, f"Playback failed: {resp_pb.text}"
    pb_data = resp_pb.json()
    assert "history" in pb_data

    # 3. Evaluate Failures Hook
    resp_eval = await async_client.post(
        f"/api/v1/digital-twins/{twin_id}/evaluate-failures",
        headers=admin_token_headers,
    )
    assert resp_eval.status_code == 200, f"Failure evaluation failed: {resp_eval.text}"

